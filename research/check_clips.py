for champ in ['garen', 'lux', 'ashe', 'tryndamere', 'zed']:
    f = f'research/{champ}_bin.txt'
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        txt = fp.read()
    clips = set()
    for l in txt.splitlines():
        if 'mAnimationName:' in l or 'mClipName:' in l:
            c = l.split(':', 1)[1].strip().strip('"')
            if c:
                clips.add(c)
    print(f'{champ:12}: {sorted(list(clips))}')
