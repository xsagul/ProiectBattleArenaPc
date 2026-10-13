import json
p='tools/ui_ref_layouts.json';d=json.load(open(p));r=next(r for r in d if r['name']=='HudItemShopItemDetailsDefinition');r['key_members']=[dict(name='ClickData',owner_class=r['name'],type='UiHashKey',size=12,offset='0x78',native_ctor_rva=0x7130f0)];json.dump(d,open(p,'w'),indent=2)
