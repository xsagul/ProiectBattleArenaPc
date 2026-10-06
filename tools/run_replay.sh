#!/bin/bash
# run_replay.sh [start|seek <seconds>|capture <frames> <tag>|stop]: drives the 13.3 client playing the 13.3 replay with the
# GPU sponge (d3d11.dll next to the game).
#   start            launch the replay (DX11) and wait until the game loop runs
#   seek <s>         jump the replay to game second s (Replay API, port 2999) and wait until it has caught up
#   capture <n> <t>  record the next n frames; they land in data/sponge/<t>/ with objects.bin and the shaders so far
#   cam <x> <z> [true] point the top camera at map position (x, z) (eye 1911.85 above, pitch 56: 1289.5 behind); true keeps the HUD
#   pause | play [speed]
#   only <name,...>  hide every particle system except the named ones (substring match); 'only' alone shows all again
#   stop             close the client
G=/c/Users/Sorin/Desktop/ProiectBattleArenaPc/game
GW='C:\Users\Sorin\Desktop\ProiectBattleArenaPc\game'
ROFL='C:\Users\Sorin\Desktop\ProiectBattleArenaPc\research\rofl\KR-6363178603_13.3.rofl'
OUT=/c/Users/Sorin/Desktop/ProiectBattleArenaPc/data/sponge
api() { curl -sk --max-time 5 "https://127.0.0.1:2999$1" "${@:2}"; }
running() { tasklist //FI "IMAGENAME eq League of Legends.exe" //FI "MEMUSAGE gt 5000" | grep -qi "league of legends"; }

case "$1" in
  start)
    running && { echo "already running"; exit 0; }
    rm -rf "$G/sponge" "$G/sponge_d3d11.log" "$G/sponge_capture.txt"
    powershell -NoProfile -Command "Start-Process -FilePath '$GW\League of Legends.exe' -WorkingDirectory '$GW' -ArgumentList '\"$ROFL\"','\"-GameBaseDir=$GW\"','-SkipRads','-SkipBuild','-EnableLNP','-UseDX11=1:1','-Locale=en_US'" >/dev/null
    sleep 3
    f=""
    until [ -n "$f" ] && grep -q "GAMESTATE_GAMELOOP" "$f"; do
      running || { echo "client exited"; exit 1; }
      sleep 2
      f=$(ls -t $G/Logs/GameLogs/*/*r3dlog.txt 2>/dev/null | head -1)
    done
    until api /replay/playback | grep -q '"time"'; do sleep 1; done
    echo "game loop; $(api /replay/playback | tr -d '\n\t ')"
    cat "$G/sponge_d3d11.log"
    ;;
  seek)
    api /replay/playback -X POST -H "Content-Type: application/json" -d "{\"time\":$2,\"paused\":false,\"speed\":1.0}" >/dev/null
    sleep 2
    until api /replay/playback | grep -q '"seeking": false'; do running || exit 1; sleep 2; done
    echo "at $(api /replay/playback | tr -d '\n\t ')"
    ;;
  capture)
    n=${2:-1}; tag=${3:-cap}
    before=$(ls $G/sponge/frame_*.bin 2>/dev/null | wc -l)
    echo "$n" > "$G/sponge_capture.txt"
    until [ $(ls $G/sponge/frame_*.bin 2>/dev/null | wc -l) -ge $((before + n)) ] && ! grep -q "x" /dev/null; do running || exit 1; sleep 1; done
    sleep 2
    mkdir -p "$OUT/$tag/shaders"
    for f in $(ls $G/sponge/frame_*.bin | tail -n "$n"); do mv "$f" "$OUT/$tag/"; b="${f%.bin}.bmp"; [ -f "$b" ] && mv "$b" "$OUT/$tag/"; done
    cp "$G/sponge/objects.bin" "$OUT/$tag/objects.bin"
    cp -n $G/sponge/shaders/*.dxbc "$OUT/$tag/shaders/" 2>/dev/null
    api /replay/playback | tr -d '\n\t ' > "$OUT/$tag/playback.json"
    api /replay/render > "$OUT/$tag/render.json"
    echo "captured $n frames into $OUT/$tag: $(ls -la $OUT/$tag/*.bin | awk '{s+=$5} END {print s}') bytes"
    ;;
  cam)
    z=$(python -c "print($3 - 1289.5)")
    api /replay/render -X POST -H "Content-Type: application/json" -d "{\"cameraMode\":\"fps\",\"cameraRotation\":{\"x\":0,\"y\":56,\"z\":0},\"fogOfWar\":false,\"cameraPosition\":{\"x\":$2,\"y\":1911.85,\"z\":$z},\"interfaceAll\":${4:-false} }" | python -c "import json,sys; d=json.load(sys.stdin); print(d['cameraPosition'], d['interfaceAll'])"
    ;;
  pause) api /replay/playback -X POST -H "Content-Type: application/json" -d '{"paused":true}' | tr -d '[:space:]'; echo ;;
  play) api /replay/playback -X POST -H "Content-Type: application/json" -d "{\"paused\":false,\"speed\":${2:-1.0}}" | tr -d '[:space:]'; echo ;;
  only)
    api /replay/particles | python -c "
import json,sys
d=json.load(sys.stdin)
want=[w.lower() for w in '$2'.split(',') if w]
out={k:(not want or any(w in k.lower() for w in want)) for k in d}
print(sum(out.values()),'of',len(out),'visible',file=sys.stderr)
json.dump(out,sys.stdout)" > /tmp/sponge_particles.json
    api /replay/particles -X POST -H "Content-Type: application/json" -d @/tmp/sponge_particles.json > /dev/null
    ;;
  dump)
    # the game's code as loaded in memory -> data/exe133/<name>.bin + <name>_pages.txt (regions and their protection)
    rm -f "$G/sponge/exe_image.bin" "$G/sponge/exe_pages.txt"
    echo 1 > "$G/sponge_dump.txt"
    until [ -f "$G/sponge/exe_pages.txt" ] && [ ! -f "$G/sponge_dump.txt" ]; do running || exit 1; sleep 1; done
    sleep 1
    cp "$G/sponge/exe_image.bin" "$OUT/../exe133/${2:-exe_image_new}.bin"
    cp "$G/sponge/exe_pages.txt" "$OUT/../exe133/${2:-exe_image_new}_pages.txt"
    tail -1 "$G/sponge_d3d11.log"
    ;;
  touch)
    # touch <mode> [first count]: mode 0 counts the locked code pages; 1 / 2 read one byte from each locked page in
    # [first, first + count) (1: from the sponge, 2: through the game's own code); see d3d11_proxy.c
    echo "${2:-0} ${3:-0} ${4:-0}" > "$G/sponge_touch.txt"
    until [ ! -f "$G/sponge_touch.txt" ]; do running || { echo "client exited"; tail -5 "$G/sponge_d3d11.log"; exit 1; }; sleep 1; done
    sleep 1
    grep "touch:" "$G/sponge_d3d11.log" | tail -22
    ;;
  imports)
    # the Windows functions behind the game's import slots -> data/exe133/imports.txt
    rm -f "$G/sponge/imports.txt"
    echo 1 > "$G/sponge_imports.txt"
    until [ ! -f "$G/sponge_imports.txt" ] && [ -f "$G/sponge/imports.txt" ]; do running || { echo "client exited"; exit 1; }; sleep 1; done
    sleep 1
    cp "$G/sponge/imports.txt" "$OUT/../exe133/imports.txt"
    tail -1 "$G/sponge_d3d11.log"
    ;;
  stop)
    taskkill //F //IM "League of Legends.exe" >/dev/null 2>&1
    ;;
esac
