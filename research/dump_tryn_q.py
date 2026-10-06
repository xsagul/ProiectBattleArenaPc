with open('research/tryndamere_bin.txt', encoding='utf-8') as f:
    text = f.read()

i = text.find('mScriptName: "TryndamereQ"')
if i != -1:
    print("="*40)
    print("SPELL: TryndamereQ")
    print(text[i:i+3000])
