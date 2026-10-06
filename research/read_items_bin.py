import sys
sys.path.append('tools')
import wadx, struct

w = wadx.Wad(r'C:\Users\Sorin\Desktop\lol14.1\DATA\FINAL\Global.wad.client')
h = 0x1d720f4f42640c18
raw = w.read(h)
print(f"Items bin size: {len(raw)} bytes, starts with {raw[:4]}")
