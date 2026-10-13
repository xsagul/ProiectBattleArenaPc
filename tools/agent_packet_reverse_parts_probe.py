import sys,os,json,itertools,re
sys.path.insert(0,'tools');import match_func as M
source=json.load(open('client-src/obj/scalar-presence-helper-audit.json'))['0x8e1220']['source']
pre=['#include "../src/FieldCodec.h"','#include "../src/gen/FieldClasses.h"','extern const u8 g_1b3d360[256];']
A=['b * 0x0802LU','(b * 0x401LU) << 1','(b << 1) * 0x401LU','(b * 2LU) * 0x401LU','(b * 0x8020LU) >> 4','(b << 11) + (b << 1)']
B=['b * 0x8020LU','(b * 0x401LU) << 5','(b << 5) * 0x401LU','(b * 0x0802LU) << 4','(b << 4) * 0x0802LU','(b << 15) + (b << 5)']
variants=[]
for a,b,order,param,which in itertools.product(A,B,range(2),('u8','u32'),(0,1,2)):
 terms=[f'(({a}) & 0x22110LU)',f'(({b}) & 0x88440LU)'];terms=terms[::1 if order==0 else -1]
 helper=f'inline u8 Reverse_NAME({param} b) {{ return (u8)(({terms[0]} | {terms[1]}) * 0x10101LU >> 16); }}\n'
 t=source
 def change(m):
  text=m[0];count=[0]
  def repl(m):
   k=count[0];count[0]+=1;return 'Reverse_NAME((u8)x)' if which==2 or k==which else m[0]
  return re.sub('Rev\\(x\\)',repl,text)
 t=re.sub('__forceinline void (?:Set|Range)_NAME[^\n]+',change,t)
 variants.append(((a,b,order,param,which),helper+t))
p='client-src/obj/agent_packet_reverse_parts_probe.cpp';open(p,'w').write('\n'.join(pre+[t.replace('NAME',f'AgentParts_{k}') for k,(_,t) in enumerate(variants)]))
obj=M.compile_obj(p,M.FLAGS);found=[];results=[]
for k,(label,t) in enumerate(variants):
 c=M.compare(p,f'?Read@AgentParts_{k}@@',0x8e1220,M.FLAGS,obj);results.append(dict(label=label,comparison=c[:4]))
 if c[3] is None:print('FOUND',label,flush=True);found.append(dict(label=label,source=t,comparison=c))
json.dump(results,open('client-src/obj/agent_packet_reverse_parts_audit.json','w'),indent=2);json.dump(found,open('client-src/obj/agent_packet_reverse_parts_found.json','w'),indent=2)
print('BEST',sorted(results,key=lambda v:-v['comparison'][2])[:6])
