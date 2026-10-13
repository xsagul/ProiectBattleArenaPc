import sys,pathlib,re,json
sys.path.insert(0,'tools');import gen_ui_refs as U,gen_sources as G,gen_meta as A
im=G.Image();head=pathlib.Path('client-src/src/gen/BinClasses.h').read_text();meta=pathlib.Path('client-src/src/gen/MetaClasses.cpp').read_text();rows=[]
for name,row in U.load_layouts().items():
 body=re.search(r'^struct (?:alignas\([^\n]+?\) )?'+name+r'(?: : \w+)?\n\{\n(.*?)^\};',head,re.M|re.S)[1]
 ctor=re.search(r'^    '+name+r'\(\);\s*// rva (0x[0-9a-f]+)',body,re.M)
 marker=re.search(r'// match: ([0-9a-f]+) \?\?__E'+name+r'_Meta@@',meta)
 args=A.ctor_args(im,int(marker[1],16)); ctor_rva=int(ctor[1],16) if ctor else None
 rows.append(dict(**row,ctor_rva=ctor_rva,ctor_text=im.text(ctor_rva) if ctor_rva else None,create_rva=args[1]-G.P.BASE,construct_rva=args[3]-G.P.BASE,class_body=body,construct_text=im.text(args[3]-G.P.BASE)))
json.dump(rows,open('client-src/obj/agent_ui_ctor_inventory.json','w'),indent=2)
print('Explicit ctor',sum(r['ctor_rva'] is not None for r in rows),'/',len(rows));print([(r['name'],hex(r['ctor_rva']) if r['ctor_rva'] else None,r['unresolved_tail_size']) for r in rows])
for r in rows[:7]:print(r['name'],r['ctor_text'])
