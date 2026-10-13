import sys,pathlib,json
sys.path.insert(0,'tools');import match_func as M
header=pathlib.Path('client-src/obj/agent_meta_small_ui_ref.h');s=header.read_text();s=s.replace('AgentUiResourceControl* control; int active;', 'AgentUiResourceControl* control = nullptr; int active = 0;');s=s.replace('struct AgentUiLink { u32 hash; u32 unknown04; u32 unknown08; AgentUiResourceReference reference; };','struct AgentUiHashKey { AgentUiHashKey(); u32 hash; u32 unknown04; u32 unknown08; };\nstruct AgentUiLink { AgentUiHashKey key; AgentUiResourceReference reference; };');s=s.replace('struct AgentUiResourceReference { virtual ~AgentUiResourceReference(); AgentUiResourceControl* control = nullptr; int active = 0; };','struct AgentUiResourceReferenceState { AgentUiResourceControl* control = nullptr; int active = 0; };\nstruct AgentUiResourceReference : AgentUiResourceReferenceState { virtual ~AgentUiResourceReference(); };');header.write_text(s)
key=pathlib.Path('client-src/obj/agent_meta_small_ui_key_native.cpp');key.write_text('#include "agent_meta_small_ui_ref.h"\nAgentUiHashKey::AgentUiHashKey() : hash(0), unknown04(0), unknown08(0x7fffffff) {}\n')
ctor=pathlib.Path('client-src/obj/agent_meta_small_ui_link_ctor.cpp');ctor.write_text('''#include "agent_meta_small_ui_ref.h"
struct AgentAbilityPrompt { AgentUiLink AnimLink; AgentUiLink TextLink; bool unknown30=false; u8 padding31[3]; u32 unknown34=0; u32 unknown38=0; AgentAbilityPrompt(); };
struct AgentCooldownEffectUiData { AgentUiLink CooldownText; AgentUiLink RadialEffect; AgentUiLink CompleteEffect; AgentUiLink JumpEffect; AgentCooldownEffectUiData(); };
AgentAbilityPrompt::AgentAbilityPrompt() {}
AgentCooldownEffectUiData::AgentCooldownEffectUiData() {}
''')
results=[]
for path,sym,rva in [(key,'??0AgentUiHashKey@@',0x9ba240),(ctor,'??0AgentAbilityPrompt@@',0x710d60),(ctor,'??0AgentCooldownEffectUiData@@',0x586c00)]:
 o=M.compile_obj(str(path),M.FLAGS);c=M.compare(str(path),sym,rva,M.FLAGS,o);print(sym,c[:4],c[4],flush=True);results.append(dict(symbol=sym,rva=hex(rva),comparison=c))
 if c[3] is None:M.rebuilt_symbols().setdefault(rva,[]).append(sym)
json.dump(results,open('client-src/obj/agent_meta_small_ui_link_ctor_audit.json','w'),indent=2)

