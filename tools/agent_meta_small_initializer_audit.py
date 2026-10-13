import sys,json,pathlib,re
sys.path.insert(0,'tools');import match_func as M
original=pathlib.Path('client-src/src/gen/MetaClasses.cpp'); source=original.read_text(encoding='utf-8')
def absolute_include(m):
 return '#include "'+str((original.parent/m[1]).resolve()).replace('\\','/')+'"'
source=re.sub(r'^#include "([^"]+)"',absolute_include,source,flags=re.M)
p='client-src/obj/agent_meta_small_initializer_context.cpp';pathlib.Path(p).write_text(source,encoding='utf-8')
obj=M.compile_obj(p,M.FLAGS);report=json.load(open('client-src/progress-2026-10-08-parallel-audit.json'));results=[]
for old in report['failures']:
 if old['source'].endswith('MetaClasses.cpp') and old['detail'].startswith('same bytes'):
  c=M.compare(p,old['symbol'],int(old['rva'],16),M.FLAGS,obj);results.append(dict(rva=old['rva'],symbol=old['symbol'],passed=c[3] is None,detail=c[4]))
json.dump(results,open('client-src/obj/agent_meta_small_initializers_audit.json','w'),indent=2)
print('Recovered old MetaClasses failures',sum(x['passed'] for x in results),'/',len(results))
