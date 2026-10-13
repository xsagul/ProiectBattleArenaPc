import sys,os,json,re,itertools
sys.path.insert(0,'tools');import match_func as M
srcs={0x88f070:max(json.load(open('client-src/obj/agent_packet_enum732_audit.json')),key=lambda v:v['comparison'][2])['source'],0x8e1220:json.load(open('client-src/obj/scalar-presence-helper-audit.json'))['0x8e1220']['source']}
pre=['#include "../src/FieldCodec.h"','#include "../src/gen/FieldClasses.h"','#include "../src/gen/FieldFormatAliases.h"','extern const u8 g_1b3d360[256];'];variants=[]
for r,s in srcs.items():
 setter=re.search(r'__forceinline void Set_NAME[^\n]+',s)[0]
 for style,mode in itertools.product(range(8),range(4)):
  t=s
  if style==0:
   t=t.replace(setter,'template<int Format> '+setter);i=[0]
   def temp(m):
    k=i[0];i[0]+=1;return f'Set_NAME<{k if mode<2 else k+1}>'
   start=t.index('char NAME::Read');t=t[:start]+re.sub('Set_NAME(?=\\()',temp,t[start:])
  else:
   calls=list(re.finditer(r'Set_NAME\((field\w+\.value), (u\d+\([^)]*\))\)',t));newsetters=[]
   for k,m in reversed(list(enumerate(calls))):
    if mode<2 and k!=mode:continue
    helper=setter.replace('Set_NAME',f'Set_{k}_NAME')
    typ='u32' if r==0x88f070 else 'u8'
    if style==1:helper=helper.replace(f'const {typ}& value',f'{typ} value')
    if style==2:helper=helper.replace(f'const {typ}& value',f'const {typ} value')
    if style==3:helper=helper.replace(f', const {typ}& value','').replace('field = value;',f'field = {m[2]};')
    if style==4:helper=helper.replace('__forceinline void','__forceinline bool').replace('} }','} return true; }')
    if style==5:helper=helper.replace('__forceinline void','inline void')
    if style==6:helper=helper.replace('field = value;','field = value; u8* finish = (u8*)&field + sizeof(field);').replace('b != (u8*)&field + sizeof(field)','b != finish')
    if style==7:helper=helper.replace('field = value;','{ field = value; }')
    newsetters.append(helper)
    call=f'Set_{k}_NAME({m[1]})' if style==3 else m[0].replace('Set_NAME',f'Set_{k}_NAME')
    t=t[:m.start()]+call+t[m.end():]
   t=t.replace(setter,setter+'\n'+'\n'.join(newsetters))
  variants.append(((r,style,mode),t))
p='client-src/obj/agent_packet_setter_parts_probe.cpp';open(p,'w').write('\n'.join(pre+[t.replace('NAME',f'AgentSetter_{k}') for k,(_,t) in enumerate(variants)]))
obj=M.compile_obj(p,M.FLAGS);results=[];found=[]
for k,(label,t) in enumerate(variants):
 c=M.compare(p,f'?Read@AgentSetter_{k}@@',label[0],M.FLAGS,obj);results.append(dict(label=label,comparison=c[:4]))
 if c[3] is None:print('FOUND',label,flush=True);found.append(dict(label=label,comparison=c,source=t))
json.dump(results,open('client-src/obj/agent_packet_setter_parts_audit.json','w'),indent=2);json.dump(found,open('client-src/obj/agent_packet_setter_parts_found.json','w'),indent=2)
for r in srcs:print('BEST',hex(r),sorted([v for v in results if v['label'][0]==r],key=lambda v:-v['comparison'][2])[:3])
