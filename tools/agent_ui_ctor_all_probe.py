import sys,json,re,pathlib
sys.path.insert(0,'tools');import match_func as M
rows=json.load(open('client-src/obj/agent_ui_ctor_inventory.json'));lines=['#include "../src/gen/BinClasses.h"','#include <cstring>'];defs=[]
for row in rows:
 if row['ctor_rva'] is None:continue
 n=row['unresolved_tail_size'];start=int(row['unresolved_tail_offset'],16);stores=[];body=[]
 for m in re.finditer(r'mov (byte|word|dword) ptr \[edi(?: \+ (0x[0-9a-f]+|\d+))?\], (0x[0-9a-f]+|\d+)',row['ctor_text']):
  off=int(m[2] or '0',0);width={'byte':1,'word':2,'dword':4}[m[1]];value=int(m[3],0)
  if off<start:continue
  assert off+width<=row['size'],row
  assert not any(off<oldoff+w and off+width>oldoff for oldoff,w,v in stores)
  stores.append((off,width,value));delta=off-start
  if width==1:body.append(f' unknown{start:02x}[{delta}]={value};')
  else:
   typ='u16' if width==2 else 'u32';body.append(f' const {typ} value{off:x}={value:#x}; std::memcpy(unknown{start:02x}+{delta}, &value{off:x}, {width});')
 source=row['name']+'::'+row['name']+'() { '+' '.join(body)+' }';lines.append(source);defs.append(dict(row,stores=stores,source=source))
p=pathlib.Path('client-src/obj/agent_ui_ctor_all_probe.cpp');p.write_text('\n'.join(lines));o=M.compile_obj(str(p),M.FLAGS);results=[]
for row in defs:
 c=M.compare(str(p),'??0'+row['name']+'@@',row['ctor_rva'],M.FLAGS,o);results.append(dict(name=row['name'],rva=hex(row['ctor_rva']),source=row['source'],stores=row['stores'],comparison=c))
 if c[3] is not None:print('FAIL',row['name'],c[:4],c[4])
json.dump(results,open('client-src/obj/agent_ui_ctor_all_audit.json','w'),indent=2)
print('Matched UI native ctors',sum(v['comparison'][3] is None for v in results),'/',len(results),'uniqueRVA',len({v['rva'] for v in results if v['comparison'][3] is None}))
