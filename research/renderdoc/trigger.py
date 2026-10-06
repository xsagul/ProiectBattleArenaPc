# Run inside qrenderdoc (qrenderdoc.exe --python trigger.py): connects to the injected League client and captures
# frames on request. Requests come from a file next to this script, one line each: "<frames> <tag>"; each capture's
# path is appended to captures.txt as "<tag> <path>".
import os
import time

import renderdoc as rd

here = 'C:/Users/Sorin/Desktop/ProiectBattleArenaPc/research/renderdoc'
requests = os.path.join(here, 'requests.txt')
done = os.path.join(here, 'captures.txt')
log = open(os.path.join(here, 'trigger.log'), 'a')


def say(*a):
    log.write(' '.join(str(x) for x in a) + '\n')
    log.flush()


ident = 0
for _ in range(120):
    ident = rd.EnumerateRemoteTargets('', 0)
    if ident:
        break
    time.sleep(1)
say('target ident', ident)
tc = rd.CreateTargetControl('', ident, 'ba-trigger', True)
say('connected', tc.Connected() if tc else None, tc.GetTarget() if tc else '')

seen = 0
pending = []
quit_after = time.time() + 6 * 3600
while tc and tc.Connected() and time.time() < quit_after:
    if os.path.exists(requests):
        lines = open(requests).read().splitlines()
        for line in lines[seen:]:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == 'quit':
                quit_after = 0
                break
            frames = int(parts[0])
            tag = parts[1] if len(parts) > 1 else 'cap'
            tc.TriggerCapture(frames)
            pending.append(tag)
            say('trigger', frames, tag)
        seen = len(lines)
    msg = tc.ReceiveMessage(None)
    if msg.type == rd.TargetControlMessageType.NewCapture:
        tag = pending.pop(0) if pending else 'cap'
        with open(done, 'a') as f:
            f.write('%s %s\n' % (tag, msg.newCapture.path))
        say('captured', tag, msg.newCapture.path)
    elif msg.type == rd.TargetControlMessageType.Disconnected:
        break
    time.sleep(0.05)
if tc:
    tc.Shutdown()
say('done')
os._exit(0)
