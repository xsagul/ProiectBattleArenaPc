import sys,pathlib,json
sys.path.insert(0,'tools');import match_func as M
lines=['#include "../src/types.h"','#include <new>','struct AgentUiResource {']
lines += [f' virtual void Unused{i}() = 0;' for i in range(27)]
lines += [' virtual void Release() = 0;','};','struct AgentUiResourceControl { AgentUiResource* resource; int references; unsigned long long key; };','struct AgentUiResourceRegistry { bool Remove(const unsigned long long*); };','extern AgentUiResourceRegistry g_37252f0;','struct AgentUiResourceReference { virtual ~AgentUiResourceReference(); AgentUiResourceControl* control; int active; };','static_assert(sizeof(AgentUiResourceReference)==12,"resource reference ABI");','AgentUiResourceReference::~AgentUiResourceReference() { if (control) { if (active) { control->resource->Release(); active=0; } --control->references; if(control->references==0 && !control->resource) g_37252f0.Remove(&control->key); control=nullptr; } }']
for n in range(2,6):
 lines += [f'struct AgentUiLinks{n} {{ unsigned char prefix[12]; '+ ' '.join(f'AgentUiResourceReference reference{i};' for i in range(n))+' };',f'void AgentUiDestruct{n}(void* p) {{ static_cast<AgentUiLinks{n}*>(p)->~AgentUiLinks{n}(); }}']
p=pathlib.Path('client-src/obj/agent_meta_small_ui_ref_probe.cpp');p.write_text('\n'.join(lines),encoding='utf-8');o=M.compile_obj(str(p),M.FLAGS)
results=[]
for symbol,rva in [('??1AgentUiResourceReference@@',0xae14d0),('??_GAgentUiResourceReference@@',0x31e950)]+[(f'?AgentUiDestruct{n}@@',r) for n,r in zip(range(2,6),(0x576830,0x576390,0x5766e0,0x576510))]:
 c=M.compare(str(p),symbol,rva,M.FLAGS,o);print(symbol,c[:4],c[4],flush=True);results.append(dict(symbol=symbol,rva=hex(rva),comparison=c))
json.dump(results,open('client-src/obj/agent_meta_small_ui_ref_audit.json','w'),indent=2)
