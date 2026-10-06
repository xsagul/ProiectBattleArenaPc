with open('research/tryndamere_bin.txt', encoding='utf-8') as f:
    text = f.read()

for name in ['TryndamereQ', 'TryndamereW', 'TryndamereE', 'UndyingRage', 'Blood_Lust']:
    i = text.find(f'mScriptName: "{name}"')
    if i != -1:
        print("="*40)
        print("SPELL:", name)
        print(text[i:i+2000])
