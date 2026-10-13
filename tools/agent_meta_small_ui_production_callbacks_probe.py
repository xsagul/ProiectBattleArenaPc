import sys,pathlib,json
sys.path.insert(0,'tools');import match_func as M,gen_ui_refs as U
rows=U.load_layouts();header=pathlib.Path('client-src/obj/agent_meta_small_ui_production_types.h');lines=['#pragma once','#include "../src/gen/UiResourceRefs.h"','template<class T> void MetaDestruct(void*);'];done=set()
def emit(name):
 if name in done:return
 row=rows[name];parent=row['parent']
 if parent:emit(parent)
 fields=[f"UiHashLink {m['name']};" for m in row['members'] if m['owner_class']==name]
 if row['unresolved_tail_size']:fields.append(f"u8 unknownTail[{row['unresolved_tail_size']}];")
 lines.append(f"struct {name}"+(f' : {parent}' if parent else '')+' { '+' '.join(fields)+' };');lines.append(f"static_assert(sizeof({name})=={row['size']},\"metadata size\");");done.add(name)
for name in sorted(rows):emit(name)
header.write_text('\n'.join(lines));callback=pathlib.Path('client-src/obj/agent_meta_small_ui_production_callbacks.cpp');callback.write_text('#include "agent_meta_small_ui_production_types.h"\n'+'\n'.join(f'template<>void MetaDestruct<{name}>(void*p){{static_cast<{name}*>(p)->~{name}();}}' for name in rows));o=M.compile_obj(str(callback),M.FLAGS);verified=[]
for name,row in rows.items():
 symbol=f'??$MetaDestruct@U{name}@@@@YAXPAX@Z';rva=int(row['destruct_rva'],16);c=M.compare(str(callback),symbol,rva,M.FLAGS,o)
 if c[3] is not None:print('FAIL',name,c)
 verified.append(dict(name=name,rva=hex(rva),symbol=symbol,comparison=c))
json.dump(verified,open('client-src/obj/agent_meta_small_ui_production_callbacks_audit.json','w'),indent=2);print('Typed callbacks with real production UiRef declarations and inheritance:',sum(v['comparison'][3] is None for v in verified),'/',len(verified))
