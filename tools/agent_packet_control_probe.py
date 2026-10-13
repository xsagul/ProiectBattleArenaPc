import sys,os,json,itertools
sys.path.insert(0,'tools')
import match_func as M
s=json.load(open('client-src/obj/scalar-presence-helper-audit.json'))['0x868c40']['source']
pre=['#include "../src/FieldCodec.h"','#include "../src/gen/FieldClasses.h"','extern const u8 g_1b3d360[256];']
s=s.replace('u32 x = *b;','u8 x = *b;').replace('g_1b3d360[(u8)x]','g_1b3d360[x]')
variants=[]
for helper,post,control in itertools.product((True,False),(True,False),range(7)):
 t=s
 if not helper:t=t.replace('Bits_NAME(p, 0, 1)','(*p & 1)')
 if post:t=t.replace('const u8* p = *cursor; if ((u32)(end - p) < 1) return false; *cursor = p + 1;','if ((u32)(end - *cursor) < 1) return false; const u8* p = (*cursor)++;')
 if control==1:t=t.replace('); } else {','); return true; } else {').replace('return false; } return true; }','return false; return true; } }')
 if control==2:t=t.replace('); } else {','); return true; } else {').replace('if (!ReadValidated8_79c870(&fielda.value, cursor, end)) return false; } return true; }','return ReadValidated8_79c870(&fielda.value, cursor, end); } }')
 if control==3:t=t.replace('); } else {','); return true; } ').replace('if (!ReadValidated8_79c870(&fielda.value, cursor, end)) return false; } return true; }','return ReadValidated8_79c870(&fielda.value, cursor, end); }')
 if control==4:t=t.replace('if (format == 1) { Set_NAME(fielda.value, g_36f73cc); } else { if (!ReadValidated8_79c870(&fielda.value, cursor, end)) return false; } return true; }','if (format != 1) return ReadValidated8_79c870(&fielda.value, cursor, end); Set_NAME(fielda.value, g_36f73cc); return true; }')
 if control==5:t=t.replace('if (format == 1) { Set_NAME(fielda.value, g_36f73cc); } else { if (!ReadValidated8_79c870(&fielda.value, cursor, end)) return false; } return true; }','if (format == 1) { Set_NAME(fielda.value, g_36f73cc); return true; } return ReadValidated8_79c870(&fielda.value, cursor, end) != 0; }')
 if control==6:t=t.replace('if (format == 1) { Set_NAME(fielda.value, g_36f73cc); } else { if (!ReadValidated8_79c870(&fielda.value, cursor, end)) return false; } return true; }','if (format == 1) { Set_NAME(fielda.value, g_36f73cc); return true; } if (ReadValidated8_79c870(&fielda.value, cursor, end)) return true; return false; }')
 variants.append((helper,post,control,t))
p='client-src/obj/agent_packet_control_probe.cpp';open(p,'w').write('\n'.join(pre+[t.replace('NAME',f'AgentControl_{k}') for k,(_,_,_,t) in enumerate(variants)]))
obj=M.compile_obj(p,M.FLAGS);found=[];results=[]
for k,(*label,t) in enumerate(variants):
 c=M.compare(p,f'?Read@AgentControl_{k}@@',0x868c40,M.FLAGS,obj);results.append(dict(label=label,comparison=c))
 if c[3] is None:print('FOUND',label,flush=True);found.append(dict(label=label,source=t,comparison=c))
json.dump(results,open('client-src/obj/agent_packet_control_audit.json','w'),indent=2);json.dump(found,open('client-src/obj/agent_packet_control_found.json','w'),indent=2)
print('BEST',[(v['label'],v['comparison'][:4]) for v in sorted(results,key=lambda v:-v['comparison'][2])[:5]])
