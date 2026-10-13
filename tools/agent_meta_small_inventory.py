import json,re,collections
r=json.load(open('client-src/progress-2026-10-08-parallel-audit.json'));missing=[]
for x in r['failures']:
 if not x['source'].endswith('MetaClasses.cpp') or not x['detail'].startswith('same bytes'):continue
 for m in re.finditer(r'ours names (\?\?\$(\w+)@U(\w+)@@@@\S+), the client has the rebuilt \?k([0-9a-f]+)@@ there',x['detail']):missing.append((m[2],m[3],int(m[4],16)))
missing=sorted(set(missing));meta=open('client-src/src/gen/MetaFunctions.cpp').read();owned=[]
for fn,k,r in missing:
 if re.search(r'^template (?:void\*|void) '+fn+'<'+re.escape(k)+r'>\(',meta,re.M):owned.append((fn,k,r))
print('missing',len(missing),'byfn',collections.Counter(x[0] for x in missing),'ODR owned',len(owned));print('First',missing[:30]);json.dump(missing,open('client-src/obj/agent_meta_small_missing.json','w'),indent=2)
