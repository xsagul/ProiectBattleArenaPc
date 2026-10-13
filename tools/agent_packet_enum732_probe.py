import sys,os,json,itertools,re
sys.path.insert(0,'tools');import match_func as M,gen_fields as F,gen_packet_scalars as S,gen_sources as G
im=G.Image();specs=S.scalar_specs(im);spec=specs[0x88f070];variants=[]
for steps in F.equivalent_bit_chains(spec['steps']):
 for codec,wide,bounds,presence,fmt in itertools.product(F.reverse_source_forms(steps),(False,True),('field','range','nonzero'),('copy','postincrement'),('direct','helper')):
  t=S.reader_source(dict(spec,steps=steps),bounds,codec=codec,wide_byte=wide,presence_style=presence,format_style=fmt)
  variants.append(((steps,codec,wide,bounds,presence,fmt),t))
pre=['#include "../src/FieldCodec.h"','#include "../src/gen/FieldClasses.h"','#include "../src/gen/FieldFormatAliases.h"','extern const u8 g_1b3d360[256];']
p='client-src/obj/agent_packet_enum732_probe.cpp';open(p,'w').write('\n'.join(pre+[t.replace('NAME',f'AgentEnum732_{k}') for k,(_,t) in enumerate(variants)]))
obj=M.compile_obj(p,M.FLAGS);results=[]
for k,(label,t) in enumerate(variants):
 c=M.compare(p,f'?Read@AgentEnum732_{k}@@',0x88f070,M.FLAGS,obj);results.append(dict(label=label,comparison=c,source=t))
json.dump(results,open('client-src/obj/agent_packet_enum732_audit.json','w'),indent=2)
print('BEST',[(r['label'],r['comparison'][:4]) for r in sorted(results,key=lambda v:-v['comparison'][2])[:3]])
