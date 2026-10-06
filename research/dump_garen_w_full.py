with open('research/garen_bin.txt', encoding='utf-8') as f:
    text = f.read()

idx = text.find('ObjectName: "GarenW"')
if idx != -1:
    end_idx = text.find('ObjectName:', idx + 10)
    print(text[idx:end_idx])
