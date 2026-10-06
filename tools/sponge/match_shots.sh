#!/bin/bash
# Screenshots of a running match (run next to run_match.sh): after each given second, asks the GPU sponge
# (d3d11.dll proxy in lol13.3) for one frame and saves it as research/exe133/match_<name>/frames/s<second>.png.
#
#   match_shots.sh <name> <second> [second ...]
G="/c/Users/Sorin/Desktop/lol13.3"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cygpath -m "$HERE/../../research/exe133")/match_$1/frames"
shift
mkdir -p "$OUT"
t0=$(date +%s)
for s in "$@"; do
  while [ $(( $(date +%s) - t0 )) -lt "$s" ]; do sleep 0.5; done
  before=$(ls "$G"/sponge/frame_*.bmp 2>/dev/null | wc -l)
  echo 1 > "$G/sponge_capture.txt"
  for i in $(seq 1 20); do
    [ $(ls "$G"/sponge/frame_*.bmp 2>/dev/null | wc -l) -gt "$before" ] && break
    sleep 0.5
  done
  f=$(ls -t "$G"/sponge/frame_*.bmp 2>/dev/null | head -1)
  [ -n "$f" ] && python -c "from PIL import Image; import sys; Image.open(sys.argv[1]).save(sys.argv[2])" "$(cygpath -m "$f")" "$OUT/s$s.png" && echo "shot s$s"
  rm -f "$G"/sponge/frame_*.bin "$f"
done
