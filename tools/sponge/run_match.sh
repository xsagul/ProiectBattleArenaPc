#!/bin/bash
# Start the unpacked 13.3 client in match mode against a local "server" script, for a few seconds, and collect what
# both sides saw.
#
#   run_match.sh <seconds> <name> [server command ...]
#
# The server command gets the port as its last argument and is killed at the end; default: tools/sponge/udp_listen.py
# (answers nothing). Keep <seconds> under 20: at 30 s without a server the client shows "Failed to Connect".
# Output in research/exe133/match_<name>/: server.txt (the server script's output), ba_net.log (ba_host.dll's sponge),
# r3dlog.txt and network log (the client's own logs).
G="/c/Users/Sorin/Desktop/lol13.3"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SECS="$1"; NAME="$2"; shift 2
PORT=5119
KEY="17BLOhi6KZsTtldTsizvHg=="
OUT="$ROOT/research/exe133/match_$NAME"
mkdir -p "$OUT"
if [ $# -eq 0 ]; then
  python "$HERE/udp_listen.py" $PORT $((SECS + 2)) "$OUT/server.txt" &
else
  "$@" $PORT > "$OUT/server.txt" 2>&1 &
fi
SRV=$!
sleep 1
cd "$G"
"./League of Legends.unpacked.exe" "127.0.0.1 $PORT $KEY 1" -Product=LoL -PlayerID=1 -GameID=1 "-GameBaseDir=C:\\Users\\Sorin\\Desktop\\lol13.3" -Region=EUW -PlatformID=EUW1 -Locale=en_US -SkipBuild -UseDX11=1:1 &
sleep "$SECS"
taskkill //F //IM "League of Legends.unpacked.exe" > /dev/null 2>&1
sleep 1
kill $SRV 2> /dev/null
cp "$G/ba_net.log" "$OUT/ba_net.log" 2> /dev/null
D="$G/Logs/GameLogs/$(ls -t "$G/Logs/GameLogs" | head -1)"
for f in "$D"/*; do cp "$f" "$OUT/$(basename "$f" | sed 's/^[0-9T:-]*_//')"; done
ls -la "$OUT"
