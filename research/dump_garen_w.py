with open('research/garen_bin.txt', encoding='utf-8') as f:
    text = f.read()

idx = text.find('ObjectName: "GarenW"')
if idx != -1:
    print(text[idx:idx+2500])
