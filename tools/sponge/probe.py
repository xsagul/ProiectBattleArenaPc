"""Write the probe list that ba_host.dll reads at start (lol13.3/ba_probes.txt).

  probe.py <rva>[:hits][=name] ...     one probe per function start; hits = how many calls get logged (default 40)
  probe.py                             no probes

For each address the number of bytes to move is found here: whole instructions covering at least 5 bytes, none of
them position-dependent (relative jump / call). Results go to ba_net.log in the client's folder.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exe_dis as E

OUT = r'C:\Users\Sorin\Desktop\lol13.3\ba_probes.txt'
lines = []
for a in sys.argv[1:]:
    name = ''
    if '=' in a: a, name = a.split('=', 1)
    hits = 40
    if ':' in a: a, hits = a.split(':'); hits = int(hits)
    r = int(a, 16)
    n = 0
    for ins in E.md.disasm(E.data[r:r + 32], E.BASE + r):
        if ins.mnemonic.startswith('j') or ins.mnemonic in ('call', 'loop', 'ret', 'int3'):
            sys.exit(f'{r:#x}: cannot move "{ins.mnemonic} {ins.op_str}" (after {n} bytes)')
        n += ins.size
        if n >= 5: break
    lines.append(f'{r:x} {n} {hits} {name or "fn_%x" % r}')
open(OUT, 'w').write('\n'.join(lines) + ('\n' if lines else ''))
print('\n'.join(lines) or 'no probes')
