import subprocess
import os

def check():
    lines = subprocess.check_output(['git', 'status', '--porcelain', '-uall'], text=True).splitlines()
    total = 0
    over_10mb = []
    count = 0
    for line in lines:
        if not line.strip():
            continue
        p = line[3:].strip('"')
        if os.path.isfile(p):
            sz = os.path.getsize(p)
            total += sz
            count += 1
            if sz > 10 * 1024 * 1024:
                over_10mb.append((p, sz))
    print(f"Total files: {count}")
    print(f"Total size: {total / 1024 / 1024:.2f} MB")
    by_dir = {}
    for line in lines:
        if not line.strip(): continue
        p = line[3:].strip('"')
        top = p.split('/')[0] if '/' in p else '.'
        if os.path.isfile(p):
            sz = os.path.getsize(p)
            by_dir[top] = by_dir.get(top, [0, 0])
            by_dir[top][0] += 1
            by_dir[top][1] += sz
    print("Breakdown by folder:")
    for d, (cnt, sz) in sorted(by_dir.items(), key=lambda x: x[1][1], reverse=True):
        print(f"  {d:20}: {cnt:6d} files, {sz / 1024 / 1024:7.2f} MB")
    data_sub = {}
    for line in lines:
        if not line.strip(): continue
        p = line[3:].strip('"')
        if p.startswith('data/'):
            parts = p.split('/')
            sub = parts[1] if len(parts) > 1 else 'root'
            if os.path.isfile(p):
                data_sub[sub] = data_sub.get(sub, [0, 0])
                data_sub[sub][0] += 1
                data_sub[sub][1] += os.path.getsize(p)
    print("\nBreakdown of data/:")
    for s, (cnt, sz) in sorted(data_sub.items(), key=lambda x: x[1][1], reverse=True):
        print(f"  data/{s:15}: {cnt:6d} files, {sz / 1024 / 1024:7.2f} MB")
    print(f"\nFiles > 10MB: {len(over_10mb)}")

    for p, sz in sorted(over_10mb, key=lambda x: x[1], reverse=True):
        print(f"  {p}: {sz / 1024 / 1024:.2f} MB")


if __name__ == '__main__':
    check()
