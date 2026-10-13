import sys,os,re,json
sys.path.insert(0,'tools');import match_func as M
results=[]
for file in ('PacketScalars.cpp','FieldFormatAliases.cpp'):
 p=os.path.join(M.ROOT,'client-src','src','gen',file);obj=M.compile_obj(p,M.FLAGS)
 for m in re.finditer(r'^// (match|same): ([0-9a-f]+) (\S+)',open(p).read(),re.M):
  c=M.compare(p,m[3],int(m[2],16),M.FLAGS,obj);results.append(dict(file=file,rva=m[2],symbol=m[3],kind=m[1],comparison=c))
  if c[3] is not None:print('FAILED',file,m[2],c,flush=True)
json.dump(results,open('client-src/obj/agent_packet_final_audit.json','w'),indent=2)
print('VERIFIED',sum(v['comparison'][3] is None for v in results),'/',len(results))
