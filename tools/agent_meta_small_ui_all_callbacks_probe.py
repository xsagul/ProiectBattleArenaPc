import sys,pathlib,json,re
sys.path.insert(0,'tools');import match_func as M
old=json.load(open('client-src/obj/agent_meta_small_missing.json'))
counts={0x576830:2,0x576390:3,0x5766e0:4,0x576510:5}
meta=pathlib.Path('client-src/src/gen/MetaClasses.cpp').read_text();binhead=pathlib.Path('client-src/src/gen/BinClasses.h').read_text();rows=[]
parents={m[1]:m[2] for m in re.finditer(r'^struct (?:alignas\([^\n]+?\) )?(\w+)(?: : (\w+))?\n\{',binhead,re.M)}
def fields_of(name):
 body=re.search(r'inline '+name+r'_MetaClass::'+name+r'_MetaClass\(\)\n.*?\n\}\n',meta,re.S)[0]
 fields=fields_of(parents[name]) if parents.get(name) else {}
 fields.update({int(m[2],16):(m[1],name) for m in re.finditer(r'AddMember<HashValue>\(HASH\("([^"]+)"\), (0x[0-9a-f]+)',body)})
 return fields
for fn,name,rva in old:
 if fn!='MetaDestruct' or rva not in counts:continue
 n=counts[rva];size=int(re.search(r'static_assert\(sizeof\('+name+r'\) == (0x[0-9a-f]+)',binhead)[1],16)
 body=re.search(r'inline '+name+r'_MetaClass::'+name+r'_MetaClass\(\)\n.*?\n\}\n',meta,re.S)[0]
 fields=fields_of(name)
 members=[]
 for off in range(0,n*24,24):
  member_name,owner=fields.get(off,(f'unknownLink{off:x}',name))
  members.append(dict(name=member_name,owner_class=owner,reflected=off in fields,offset=hex(off),type='UiHashLink',size=24,reference_offset=hex(off+12)))
 rows.append(dict(name=name,parent=parents.get(name),size=size,destruct_rva=hex(rva),members=members,unresolved_tail_offset=hex(n*24),unresolved_tail_size=size-n*24))
json.dump(rows,open('client-src/obj/agent_meta_small_ui_layouts.json','w'),indent=2)
header=pathlib.Path('client-src/obj/agent_meta_small_ui_classes.h')
lines=['#pragma once','#include "agent_meta_small_ui_ref.h"','template<class T> void MetaDestruct(void*);']
for row in rows:
 fields=' '.join('AgentUiLink '+m['name']+';' for m in row['members'])
 if row['unresolved_tail_size']:fields+=f" u8 unknownTail[{row['unresolved_tail_size']}];"
 lines.append(f"struct {row['name']} {{ {fields} }};")
 lines.append(f"static_assert(sizeof({row['name']})=={row['size']},\"metadata size\");")
header.write_text('\n'.join(lines))
callback=pathlib.Path('client-src/obj/agent_meta_small_ui_all_callbacks.cpp');callback.write_text('#include "agent_meta_small_ui_classes.h"\n'+'\n'.join(f"template<> void MetaDestruct<{row['name']}>(void*p) {{ static_cast<{row['name']}*>(p)->~{row['name']}(); }}" for row in rows))
o=M.compile_obj(str(callback),M.FLAGS);native=pathlib.Path('client-src/obj/agent_meta_small_ui_ref_native.cpp');no=M.compile_obj(str(native),M.FLAGS+['-Ob1']);c=M.compare(str(native),'??1AgentUiResourceReference@@',0xae14d0,M.FLAGS+['-Ob1'],no);assert c[3]is None,c;M.rebuilt_symbols().setdefault(0xae14d0,[]).append('??1AgentUiResourceReference@@')
verified=[]
for row in rows:
 symbol=f"??$MetaDestruct@U{row['name']}@@@@YAXPAX@Z";rva=int(row['destruct_rva'],16);c=M.compare(str(callback),symbol,rva,M.FLAGS,o)
 if c[3] is not None:print('FAIL',row['name'],c)
 verified.append(dict(name=row['name'],symbol=symbol,rva=hex(rva),comparison=c))
json.dump(verified,open('client-src/obj/agent_meta_small_ui_all_callbacks_audit.json','w'),indent=2)
print('Verified typed callbacks',sum(v['comparison'][3] is None for v in verified),'/',len(verified),'sizes',{r:n for r,n in counts.items()},flush=True)
