import pathlib,sys
sys.path.insert(0,'tools');import match_func as M
s=pathlib.Path('client-src/src/gen/UiResourceRefs.h').read_text().replace('#include "../types.h"','#include "../src/Meta.h"').replace('u32 hash;','HashValue hash;');p=pathlib.Path('client-src/obj/agent_ui_hash_typed.h');p.write_text(s)
s=pathlib.Path('client-src/src/gen/UiResourceRefs.cpp').read_text().replace('#include "UiResourceRefs.h"','#include "agent_ui_hash_typed.h"').replace('hash(0)','hash{0}');c=pathlib.Path('client-src/obj/agent_ui_hash_typed.cpp');c.write_text(s);o=M.compile_obj(str(c),M.file_flags(str(c)));print(M.compare(str(c),'??0UiHashKey@@',0x9ba240,M.file_flags(str(c)),o));print(M.compare(str(c),'??1UiResourceReference@@',0xae14d0,M.file_flags(str(c)),o)[:4])
