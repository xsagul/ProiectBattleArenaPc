import sys,pathlib,json
sys.path.insert(0,'tools');import match_func as M
header=pathlib.Path('client-src/obj/agent_meta_small_ui_ref.h')
lines=['#pragma once','#include "../src/types.h"','struct AgentUiResource {']+[f' virtual void Unused{i}() = 0;' for i in range(27)]
lines += [' virtual void Release() = 0;','};','struct AgentUiResourceControl { AgentUiResource* resource; int references; unsigned long long key; };','struct AgentUiResourceRegistry { bool Remove(const unsigned long long*); };','extern AgentUiResourceRegistry g_37252f0;','struct AgentUiResourceReference { virtual ~AgentUiResourceReference(); AgentUiResourceControl* control; int active; };','static_assert(sizeof(AgentUiResourceReference)==12,"resource reference ABI");','struct AgentUiLink { u32 hash; u32 unknown04; u32 unknown08; AgentUiResourceReference reference; };','static_assert(sizeof(AgentUiLink)==24,"UI hash link ABI");']
for n in range(2,6):lines += [f'struct AgentUiLinks{n} {{ '+ ' '.join(f'AgentUiLink link{i};' for i in range(n))+' };']
header.write_text('\n'.join(lines),encoding='utf-8')
native=pathlib.Path('client-src/obj/agent_meta_small_ui_ref_native.cpp');native.write_text('''#include "agent_meta_small_ui_ref.h"
AgentUiResourceReference::~AgentUiResourceReference() { if (control) { if (active) { control->resource->Release(); active=0; } --control->references; if(control->references==0 && !control->resource) g_37252f0.Remove(&control->key); control=nullptr; } }
''',encoding='utf-8')
callback=pathlib.Path('client-src/obj/agent_meta_small_ui_ref_callbacks.cpp');callback.write_text('#include "agent_meta_small_ui_ref.h"\n'+'\n'.join(f'void AgentUiDestruct{n}(void* p) {{ static_cast<AgentUiLinks{n}*>(p)->~AgentUiLinks{n}(); }}' for n in range(2,6)),encoding='utf-8')
results=[]
for flags in (M.FLAGS,M.FLAGS+['-Ob1']):
 o=M.compile_obj(str(native),flags)
 for symbol,rva in [('??1AgentUiResourceReference@@',0xae14d0),('??_GAgentUiResourceReference@@',0x31e950)]:
  c=M.compare(str(native),symbol,rva,flags,o);results.append(dict(file=str(native),flags=flags,symbol=symbol,rva=hex(rva),comparison=c));print(flags,symbol,c[:4],c[4],flush=True)
  if c[3] is None:M.rebuilt_symbols().setdefault(rva,[]).append(symbol)
o=M.compile_obj(str(callback),M.FLAGS)
for n,r in zip(range(2,6),(0x576830,0x576390,0x5766e0,0x576510)):
 c=M.compare(str(callback),f'?AgentUiDestruct{n}@@',r,M.FLAGS,o);results.append(dict(file=str(callback),symbol=f'?AgentUiDestruct{n}@@',rva=hex(r),comparison=c));print(n,c[:4],c[4],flush=True)
json.dump(results,open('client-src/obj/agent_meta_small_ui_ref_split_audit.json','w'),indent=2)
