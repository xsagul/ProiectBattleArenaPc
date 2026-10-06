"""Our stand-in for Riot's online services, as the real Riot Client 63.0.9 / League Client 13.3 ask for them.

Method (the user's): start the real client pointed at us, log every request it makes, answer each step with what it
needs, repeat until login -> lobby -> game. Every request lands in the log (method, host, path, headers, body), the
answers that exist so far are in ROUTES; anything else gets 404 and shows up in the log as the next thing to answer.

Also a proxy: the client is started with HTTP(S)_PROXY pointing here, so a request to a host we have not redirected
shows up as CONNECT <host> and is refused: nothing leaves the machine.

  riot_services.py [port] [log file]
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5200
LOG = open(sys.argv[2] if len(sys.argv) > 2 else 'riot_services.log', 'a', encoding='utf-8')
LOCK = threading.Lock()
T0 = time.time()

ROUTES = {}   # (method, path without query) -> function(handler, body) -> (status, headers, body bytes)


def log(text):
    with LOCK:
        line = f'{time.time() - T0:8.3f} {text}'
        print(line, flush=True)
        LOG.write(line + '\n')
        LOG.flush()


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _body(self):
        n = int(self.headers.get('Content-Length') or 0)
        return self.rfile.read(n) if n else b''

    def _handle(self):
        body = self._body()
        path = self.path.split('?')[0]
        hdr = {k: v for k, v in self.headers.items()}
        fn = ROUTES.get((self.command, path))
        status, headers, out = fn(self, body) if fn else (404, {'Content-Type': 'application/json'},
                                                           json.dumps({'errorCode': 'NOT_EMULATED', 'path': path}).encode())
        log(f'{self.command} {self.headers.get("Host")} {self.path} -> {status}{"" if fn else " (not answered yet)"}\n'
            f'          headers {json.dumps(hdr)}\n'
            + (f'          body {body[:2000].decode("utf-8", "replace")}\n' if body else '')
            + (f'          answer {out[:300].decode("utf-8", "replace")}' if fn else ''))
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _handle

    def do_CONNECT(self):
        log(f'CONNECT {self.path} -> refused (a host we do not redirect yet)')
        self.send_response(403)
        self.send_header('Content-Length', '0')
        self.end_headers()


if __name__ == '__main__':
    log(f'--- riot_services on 127.0.0.1:{PORT}')
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
