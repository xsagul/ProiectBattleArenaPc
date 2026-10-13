import sys,re,os,struct,json
sys.path.insert(0,'tools')
import gen_sources as G,gen_fields as F,gen_field_classes as C,gen_packet_scalars as S
im=G.Image();specs=S.scalar_specs(im);rows=[]
for ctor,name in re.findall(r'^// ctor: ([0-9a-f]+) (\w+)',open('client-src/src/gen/FieldClasses.h').read(),re.M):
 ctor=int(ctor,16);schema=C.constructor_schema(im,ctor)
 if not schema or not schema[2] or len(schema[0])!=3 or schema[0][2][3] is None:continue
 text=im.text(ctor);root=re.search(r'^mov (edi|esi|ebx), ecx$',text,re.M)[1];table=F.number(re.findall(r'mov dword ptr \['+root+r'\], (0x[0-9a-f]+)',text)[-1]);rva=struct.unpack_from('<I',im.img,table-F.BASE+4)[0]-F.BASE
 if rva in im.done or rva in specs:continue
 rows.append(dict(name=name,rva=hex(rva),schema=schema,bytes=im.size(rva),text=im.text(rva)))
json.dump(rows,open('client-src/obj/agent_packet_unclassified_scalars.json','w'),indent=2)
print('classified',len(specs),'unclassified',len(rows));print([(r['name'],r['rva'],r['bytes']) for r in rows])
for r in rows[:10]:print(r['name'],r['rva'],r['text'])
