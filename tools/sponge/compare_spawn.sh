#!/bin/bash
# The first lane wave seen by the client, Riot's server (the replay streamed) against ours (--start-only + world.py),
# with the same input: camera locked on the hero (y), the hero sent by a right click on the minimap next to the blue
# mid inhibitor; frames taken by the server at given GAME seconds -> research/exe133/match_<name>_<mode>/frames.
#   compare_spawn.sh <name> <game seconds, comma separated>
cd "$(dirname "$0")/../.."
NAME=$1; SHOTS=$2
G=/c/Users/Sorin/Desktop/lol13.3
for MODE in replay ours; do
  EXTRA=""
  [ "$MODE" = ours ] && EXTRA="--start-only"
  rm -f $G/sponge/frame_*.bmp $G/sponge/frame_*.bin
  # the input waits for the game window itself; the match runs in the foreground (run_match kills the game at its end)
  (sleep 2; powershell -ExecutionPolicy Bypass -File tools/sponge/game_input.ps1 "14:key:y;15:rclick:1695,1030;30:rclick:1695,1030" research/exe133/${NAME}_${MODE}_input.log > /dev/null 2>&1 &)
  bash tools/sponge/run_match.sh 95 ${NAME}_$MODE python tools/sponge/lnp_server.py --replay-574 --own-574 --set574 "1.champion=Jinx;1.champion_id=222;1.skin=0" --slot 1 --hero 4000001e --own-79 --set79 "1.champion=Jinx;1.skin=0" $EXTRA --shots-game "$SHOTS" --stream research/rofl/KR-6363178603_13.3.rofl > /dev/null 2>&1
  while tasklist | grep -q "League of Legends"; do sleep 1; done
  sleep 3
  OUT=research/exe133/match_${NAME}_$MODE/frames; mkdir -p $OUT
  i=0
  for f in $(ls $G/sponge/frame_*.bmp 2>/dev/null | sort); do
    python -c "from PIL import Image; import sys; Image.open(sys.argv[1]).save(sys.argv[2])" "$(cygpath -m $f)" "$OUT/f$i.png"; i=$((i+1))
  done
  rm -f $G/sponge/frame_*.bmp $G/sponge/frame_*.bin
  grep "capture asked" research/exe133/match_${NAME}_$MODE/server.txt | head -20
done
