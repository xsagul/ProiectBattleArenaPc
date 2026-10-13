// Keeps one REA MCP server (and so one analysed Ghidra session) alive and feeds it requests.
//
//   node tools/rea_session.mjs <outdir> [requests.json]
//
// requests.json = [{ "name": "open", "tool": "open_binary", "arguments": {...} }, ...]
// Every answer goes to <outdir>/<name>.json. After the list is done the session stays up and
// takes more request files dropped into <outdir>/inbox/*.json (same format, one list per file);
// creating <outdir>/stop ends it. <outdir>/tools.json = the server's own tool list.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REA = path.join(ROOT, 'toolchain', 'rea', 'node_modules', 'rea-agents', 'scripts', 'rea.mjs');
const JDK = path.join(ROOT, 'toolchain', 'jdk-21.0.12.1+1');

const outdir = path.resolve(process.argv[2] || 'rea_out');
const inbox = path.join(outdir, 'inbox');
fs.mkdirSync(inbox, { recursive: true });
const log = (...a) => {
  const line = `[${new Date().toISOString().slice(11, 19)}] ${a.join(' ')}\n`;
  fs.appendFileSync(path.join(outdir, 'session.log'), line);
  process.stdout.write(line);
};

const env = {
  ...process.env,
  GHIDRA_INSTALL_DIR: path.join(ROOT, 'toolchain', 'ghidra_12.1.4_PUBLIC'),
  JAVA_HOME: JDK,
  PATH: path.join(JDK, 'bin') + path.delimiter + process.env.PATH,
  REA_GHIDRA_STARTUP_TIMEOUT_MS: process.env.REA_GHIDRA_STARTUP_TIMEOUT_MS || String(3 * 3600 * 1000),
  GHIDRA_HEADLESS_MAXMEM: process.env.GHIDRA_HEADLESS_MAXMEM || '6G',
};
const server = spawn(process.execPath, [REA, '--mcp'], { env, stdio: ['pipe', 'pipe', 'pipe'] });
server.stderr.on('data', d => fs.appendFileSync(path.join(outdir, 'server.err'), d));
server.on('exit', code => { log('server exited', code); process.exit(code || 0); });

let nextId = 1;
const waiting = new Map();
let buffer = '';
server.stdout.on('data', d => {
  buffer += d;
  for (;;) {
    const end = buffer.indexOf('\n');
    if (end < 0) break;
    const line = buffer.slice(0, end).trim();
    buffer = buffer.slice(end + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); } catch { log('not json:', line.slice(0, 200)); continue; }
    if (msg.id !== undefined && waiting.has(msg.id)) {
      waiting.get(msg.id)(msg);
      waiting.delete(msg.id);
    } else if (msg.method === 'notifications/progress') {
      log('progress', JSON.stringify(msg.params).slice(0, 300));
    } else if (msg.id !== undefined && msg.method) {
      // a request from the server (roots, sampling ...): we offer none
      send({ jsonrpc: '2.0', id: msg.id, error: { code: -32601, message: 'not supported' } });
    }
  }
});
const send = msg => server.stdin.write(JSON.stringify(msg) + '\n');
const request = (method, params) => new Promise(resolve => {
  const id = nextId++;
  waiting.set(id, resolve);
  send({ jsonrpc: '2.0', id, method, params });
});

async function run(list) {
  for (const item of list) {
    const started = Date.now();
    const answer = await request('tools/call', {
      name: item.tool,
      arguments: item.arguments || {},
      _meta: { progressToken: item.name },
    });
    const file = path.join(outdir, item.name + '.json');
    fs.writeFileSync(file, JSON.stringify(answer.result ?? answer.error, null, 1));
    const failed = answer.error || answer.result?.isError;
    log(item.name, item.tool, failed ? 'FAILED' : 'ok', ((Date.now() - started) / 1000).toFixed(1) + ' s',
      fs.statSync(file).size + ' B');
  }
}

const hello = await request('initialize', {
  protocolVersion: '2025-06-18',
  capabilities: {},
  clientInfo: { name: 'rea_session', version: '1' },
});
log('server', JSON.stringify(hello.result?.serverInfo), 'protocol', hello.result?.protocolVersion);
send({ jsonrpc: '2.0', method: 'notifications/initialized' });
const tools = await request('tools/list', {});
fs.writeFileSync(path.join(outdir, 'tools.json'), JSON.stringify(tools.result, null, 1));
log('tools', tools.result?.tools?.length);

if (process.argv[3]) await run(JSON.parse(fs.readFileSync(process.argv[3], 'utf8')));
log('waiting for', inbox);
for (;;) {
  if (fs.existsSync(path.join(outdir, 'stop'))) break;
  for (const name of fs.readdirSync(inbox).filter(n => n.endsWith('.json')).sort()) {
    const file = path.join(inbox, name);
    let list;
    try { list = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { log('bad request file', name, e.message); }
    fs.renameSync(file, file + '.taken');
    if (list) await run(list);
    log('done', name);
  }
  await new Promise(r => setTimeout(r, 500));
}
await run([{ name: 'close', tool: 'close_binary', arguments: {} }]);
server.stdin.end();
