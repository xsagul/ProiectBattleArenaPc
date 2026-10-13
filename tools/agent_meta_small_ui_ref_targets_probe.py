import sys,pathlib,struct,json,os
sys.path.insert(0,'tools');import match_func as M
import packet_emu as P
path='client-src/obj/agent_meta_small_ui_ref_native.cpp';flags=M.FLAGS+['-Ob1','-GR-'];obj=M.compile_obj(path,flags);results=[]
expected={
 '??1AgentUiResourceReference@@': {'??_7AgentUiResourceReference@@6B@':0x1afb9bc-P.BASE,'?g_37252f0@@3UAgentUiResourceRegistry@@A':0x37252f0-P.BASE,'?Remove@AgentUiResourceRegistry@@QAE_NPB_K@Z':0xafd340},
 '??_GAgentUiResourceReference@@': {'??1AgentUiResourceReference@@UAE@XZ':0xae14d0,'??3@YAXPAXI@Z':0x9bb940}}
for sym,rva in [('??1AgentUiResourceReference@@',0xae14d0),('??_GAgentUiResourceReference@@',0x31e950)]:
 c=M.compare(path,sym,rva,flags,obj);assert c[3] is None,c;_,code,_=M.function_of(obj,sym);targets=dict(M.symbol_addresses(rva,code));assert targets==expected[sym],(sym,targets,expected[sym]);M.rebuilt_symbols().setdefault(rva,[]).append(sym);results.append(dict(symbol=sym,rva=hex(rva),bytes=c[1],targets=targets))
stat=os.stat(obj);data,symptr,name,_,_,_,_=M._coff_object(os.path.abspath(obj),stat.st_mtime_ns,stat.st_size);nsym=struct.unpack_from('<I',data,12)[0];k=0;vt=None
while k<nsym:
 s=data[symptr+18*k:symptr+18*k+18];n=name(s);value,sec,typ,cls,aux=struct.unpack_from('<IhHBB',s,8)
 if n=='??_7AgentUiResourceReference@@6B@':vt=(value,sec)
 k+=1+aux
assert vt is not None
value,sec=vt;header=20+struct.unpack_from('<H',data,16)[0]+40*(sec-1);size,raw,relptr=struct.unpack_from('<III',data,header+16);nrel=struct.unpack_from('<H',data,header+32)[0]
assert size-value==4,(size,value)
vtrefs=[]
for i in range(nrel):
 off,idx,typ=struct.unpack_from('<IIH',data,relptr+10*i)
 if off>=value:vtrefs.append((off-value,name(data[symptr+18*idx:symptr+18*idx+18])))
assert vtrefs==[(0,'??_GAgentUiResourceReference@@UAEPAXI@Z')],vtrefs
assert struct.unpack_from('<I',P.IMG,0x1afb9bc-P.BASE)[0]-P.BASE==0x31e950
results.append(dict(vtable_va='0x1afb9bc',bytes=4,slots=vtrefs))
json.dump(results,open('client-src/obj/agent_meta_small_ui_ref_targets_audit.json','w'),indent=2)
print('Native destructor79/79 +deleting32/32 +single-slot vtable4bytes +all targets VERIFIED')
