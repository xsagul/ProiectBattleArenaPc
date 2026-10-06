// The League Client 13.3 shadow-DOM elements (<lol-uikit-*> in rcp-fe-lol-uikit, <lol-regalia-*> and others in
// rcp-fe-lol-shared-components): each element's template and style sheet ship inside the plugin's script as small
// webpack modules. This lists them as data (lobby/www13/uikit/elements*.json: tag -> {template, css, attrs}) so the
// page can attach the same shadow content with its own element classes.
// Only the string modules are evaluated (a template module is e.exports='...'; a style module pushes a CSS string
// built from literals and asset modules, e.exports=publicPath+'file.png' or a data: URL), with a stub require; the
// element classes and everything else in the bundle are never called (besides css-loader's url-quoting helper).
//   node tools/uikit_extract.js [plugin=rcp-fe-lol-uikit]     e.g. rcp-fe-lol-shared-components (the lol-regalia-* elements)
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const PLUGIN = process.argv[2] || 'rcp-fe-lol-uikit';
const SRC = path.join(ROOT, `lcu-data/13.3/plugins/${PLUGIN}/global/default/${PLUGIN}.js`);
const OUT = path.join(ROOT, 'lobby/www13/uikit', PLUGIN === 'rcp-fe-lol-uikit' ? 'elements.json' : `elements-${PLUGIN.replace('rcp-fe-lol-', '')}.json`);
const s = fs.readFileSync(SRC, 'utf8');
// "(function(e){...bootstrap...;t.p='/fe/<name>/',...})([modules])": keep the array, read the public path
const end = s.indexOf('})([');
const publicPath = (/\.p='([^']*)'/.exec(s.slice(0, end)) || [])[1] || '';
const modules = new Function('return (function(e){return e})(' + s.slice(end + 3))();
const src = modules.map((f) => (typeof f === 'function' ? f.toString() : ''));

const isCssRuntime = (c) => c.includes('sourceMappingURL=data:application/json');
const isUrlEscape = (c) => c.startsWith("function(e){e.exports=function(e){return'string'==typeof e?");
const isStringModule = (c) => /^function\s*\(\w+(,\w+){0,2}\)\{(\w+=)?\w+\.exports=(\w+\.p\+)?(['"])/.test(c) ||
  /\.push\(\[\w+\.i,/.test(c);
const cache = {};
function value(i) {
  if (i in cache) return cache[i];
  const c = src[i];
  if (!c || !isStringModule(c)) return (cache[i] = null);
  const module = { exports: {}, i };
  const req = (j) => {
    if (isCssRuntime(src[j] || '')) return () => { const a = []; a.i = () => {}; return a; };
    if (isUrlEscape(src[j] || '')) {   // css-loader's url() quoting helper: a pure function, taken as is
      const m = { exports: {} };
      modules[j].call(m.exports, m, m.exports, req);
      return m.exports;
    }
    return value(j);
  };
  req.p = publicPath;
  modules[i].call(module.exports, module, module.exports, req);
  let v = module.exports;
  if (Array.isArray(v)) v = v.map((x) => x[1]).join('\n');
  return (cache[i] = typeof v === 'string' ? v : null);
}

const out = {};
src.forEach((c, i) => {
  for (const m of c.matchAll(/(\w)\.tagName='((?:lol-)?[a-z]+-[\w-]+)'/g)) {
    const tag = m[2];
    const t = /templateMarkup\(\)\{return \w\((\d+)\)\}/.exec(c);
    const st = /stylesheetMarkup\(\)\{return \w\((\d+)\)\}/.exec(c);
    const at = /observedAttributes\(\)\{return(\[[^\]]*\])/.exec(c);
    out[tag] = {
      module: i,
      template: t ? value(+t[1]) : null,
      css: st ? value(+st[1]) : null,
      attrs: at ? at[1] : null,
    };
  }
});
fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log(Object.keys(out).length, 'elements ->', OUT, 'public path', publicPath);
for (const [k, v] of Object.entries(out)) console.log(k, !!v.template, v.css ? v.css.length : 0);
