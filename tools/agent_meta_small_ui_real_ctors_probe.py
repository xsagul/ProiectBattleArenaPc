import sys,pathlib,json
sys.path.insert(0,'tools');import match_func as M
p=pathlib.Path('client-src/obj/agent_meta_small_ui_real_ctors.cpp');p.write_text('''#include "../src/gen/BinClasses.h"
#include <cstring>
AbilityPrompt::AbilityPrompt() {
    unknown30[0] = 0;
    const u32 zero = 0;
    std::memcpy(unknown30 + 4, &zero, 4);
    std::memcpy(unknown30 + 8, &zero, 4);
}
CooldownEffectUiData::CooldownEffectUiData() {}
''',encoding='utf-8')
o=M.compile_obj(str(p),M.FLAGS);results=[]
for name,rva in [('AbilityPrompt',0x710d60),('CooldownEffectUiData',0x586c00)]:
 c=M.compare(str(p),f'??0{name}@@',rva,M.FLAGS,o);print(name,c[:4],c[4]);results.append(dict(name=name,rva=hex(rva),comparison=c))
json.dump(results,open('client-src/obj/agent_meta_small_ui_real_ctors_audit.json','w'),indent=2)
