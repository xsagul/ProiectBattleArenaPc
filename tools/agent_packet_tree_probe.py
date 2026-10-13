import sys,os,json,itertools
sys.path.insert(0,'tools')
import gen_packet_scalars as S,gen_sources as G,match_func as M
im=G.Image();audit=json.load(open('client-src/obj/scalar-presence-helper-audit.json'))
pre=['#include "../src/FieldCodec.h"','#include "../src/gen/FieldClasses.h"','#include "../src/gen/FieldFormatAliases.h"','extern const u8 g_1b3d360[256];']
candidates=[]
# Vary surrounding control-flow of the one-byte validated scalar.
s=audit['0x868c40']['source']; specs=S.scalar_specs(im)
for wide in (False,True):
 for presence in ('copy','postincrement'):
  for fmt in ('direct','helper'):
   for bounds in ('field','range','nonzero'):
    src=S.reader_source(specs[0x868c40],bounds,wide_byte=wide,presence_style=presence,format_style=fmt)
    for tail in range(4):
     t=src
     if tail==1:t=t.replace('); } else {','); return true; } else {').replace('return false; } return true; }','return false; return true; } }')
     if tail==2:t=t.replace('); } else {','); return true; } if (true) {')
     if tail==3:t=t.replace('); } else {','); return true; } {').replace('return false; } return true; }','return false; } return true; }')
     candidates.append((0x868c40,f'control-{wide}-{presence}-{fmt}-{bounds}-{tail}',t))
# Algebraically equivalent expression trees for reverse.
A=['b * 0x0802U','(b * 0x401U) << 1','(b << 1) * 0x401U','(b * 2U) * 0x401U','(b * 0x8020U) >> 4','b * (0x800U + 2U)','(b << 11) + (b << 1)']
B=['b * 0x8020U','(b * 0x401U) << 5','(b << 5) * 0x401U','(b * 0x0802U) << 4','(b << 4) * 0x0802U','b * (0x8000U + 0x20U)','(b << 15) + (b << 5)']
for a,b,order,local in itertools.product(A,B,range(2),range(3)):
 terms=[f'(({a}) & 0x22110U)',f'(({b}) & 0x88440U)'];terms=terms[::1 if order==0 else -1]
 body=f'return (u8)(({terms[0]} | {terms[1]}) * 0x10101U >> 16);'
 if local==1:body=f'u32 a = {terms[0]}; u32 c = {terms[1]}; return (u8)((a | c) * 0x10101U >> 16);'
 if local==2:body=f'u32 a = {terms[0]}; a |= {terms[1]}; a *= 0x10101U; return a >> 16;'
 helper='__forceinline u8 Reverse_NAME(u32 b) { '+body+' }\n'
 src=helper+audit['0x8e1220']['source'].replace('Rev(x)','Reverse_NAME((u8)x)')
 candidates.append((0x8e1220,f'reverse-{a}-{b}-{order}-{local}',src))
path=os.path.join(M.OUT,'agent_packet_tree_probe.cpp')
open(path,'w').write('\n'.join(pre+[t.replace('NAME',f'AgentPacket_{r:x}_{k}') for k,(r,_,t) in enumerate(candidates)]))
obj=M.compile_obj(path,M.FLAGS);results=[];found=[]
for k,(r,label,t) in enumerate(candidates):
 c=M.compare(path,f'?Read@AgentPacket_{r:x}_{k}@@',r,M.FLAGS,obj)
 results.append(dict(rva=hex(r),label=label,size=c[1],same=c[2],first=c[3]))
 if c[3] is None:found.append(dict(rva=hex(r),label=label,source=t,comparison=c));print('FOUND',hex(r),label,flush=True)
json.dump(results,open('client-src/obj/agent_packet_tree_audit.json','w'),indent=2)
json.dump(found,open('client-src/obj/agent_packet_tree_found.json','w'),indent=2)
for r in (0x868c40,0x8e1220):print('BEST',hex(r),sorted([v for v in results if v['rva']==hex(r)],key=lambda v:(-v['same'],v['size']))[:5])

