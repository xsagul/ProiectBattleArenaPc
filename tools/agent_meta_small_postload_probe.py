import sys,pathlib,json
sys.path.insert(0,'tools');import match_func as M
p=pathlib.Path('client-src/obj/agent_meta_small_postload_probe.cpp')
s='''#include "../src/gen/BinClasses.h"
struct ViewLoadRegistry_ab1550 { void Load(const u8* fileLinkBytes); };
extern int g_36f6118;
void RegisterView_af37c0(ViewController*);
void ViewController::PostLoad() {
    ViewLoadRegistry_ab1550* registry = (ViewLoadRegistry_ab1550*)g_36f6118;
    if (registry) registry->Load(unknown04 + 0x2c);
    if (unknown04[0]) RegisterView_af37c0(this);
}
'''
p.write_text(s,encoding='utf-8');o=M.compile_obj(str(p),M.FLAGS);c=M.compare(str(p),'?PostLoad@ViewController@@',0xaefdb0,M.FLAGS,o);print(c[:4],c[4]);M.function_of(o,'?PostLoad@ViewController@@');print('TARGETS',M.symbol_addresses(0xaefdb0,M.function_of(o,'?PostLoad@ViewController@@')[1]));json.dump(dict(comparison=c,source=s),open('client-src/obj/agent_meta_small_postload_audit.json','w'),indent=2)
