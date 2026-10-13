import sys,os,json,itertools,re
sys.path.insert(0,'tools');import match_func as M,gen_fields as F,gen_packet_scalars as S,gen_sources as G
spec=S.scalar_specs(G.Image())[0x8bf6c0]
pre=['#include "../src/FieldCodec.h"','#include "../src/gen/FieldClasses.h"','extern const u8 g_1b3d360[256];','char ReadField8_796de0(u8*,const u8**,const u8*);']
functions,decls=S.functions_in_wrappers(); pre += decls
for tag in (3,5,4,7):
 pre += [functions[0x796de0][2].replace('char ReadField8_796de0',f'__declspec(noinline) char AgentFormat_796de0_{tag}')]
variants=[]
for steps in F.equivalent_bit_chains([tuple(x) for x in spec['steps']]):
 for codec,wide,bounds,presence,fmt in itertools.product(F.reverse_source_forms(steps),(False,True),('field','range','nonzero'),('copy','postincrement'),('direct','helper')):
  t=S.reader_source(dict(spec,steps=steps),bounds,codec=codec,wide_byte=wide,presence_style=presence,format_style=fmt)
  t=t.replace('FieldFormat_796de0_', 'AgentFormat_796de0_')
  variants.append(((steps,codec,wide,bounds,presence,fmt),t))
p='client-src/obj/agent_packet_enum734_probe.cpp';open(p,'w').write('\n'.join(pre+[t.replace('NAME',f'AgentEnum_{k}') for k,(_,t) in enumerate(variants)]))
obj=M.compile_obj(p,M.FLAGS);found=[];results=[]
for tag in (3,5,4,7):
 c=M.compare(p,f'?AgentFormat_796de0_{tag}@',0x796de0,M.FLAGS,obj); assert c[3] is None,c
 M.rebuilt_symbols().setdefault(0x796de0,[]).append(f'?AgentFormat_796de0_{tag}@')
for k,(label,t) in enumerate(variants):
 c=M.compare(p,f'?Read@AgentEnum_{k}@@',0x8bf6c0,M.FLAGS,obj);results.append(dict(label=label,comparison=c[:4]))
 if c[3] is None:print('FOUND',label,flush=True);found.append(dict(label=label,source=t,comparison=c))
json.dump(results,open('client-src/obj/agent_packet_enum734_audit.json','w'),indent=2);json.dump(found,open('client-src/obj/agent_packet_enum734_found.json','w'),indent=2)
print('BEST',sorted(results,key=lambda v:-v['comparison'][2])[:6])



