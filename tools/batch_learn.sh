#!/bin/bash
# Learns packet ids one after the other (pkt_schema.py learn on the longest replay sample, then check and many) and
# appends one summary line per id to data/exe133/codec/batch_learn.txt.
#   batch_learn.sh <id> [<id> ...]
cd "$(dirname "$0")/.."
for p in "$@"; do
  [ -s data/exe133/codec/$p.tree.json ] && continue
  PKT_LONGEST=1 timeout 3600 python server/pkt_schema.py learn $p > data/exe133/codec/learn$p.log 2>&1
  c=$(python server/pkt_schema.py check $p 40 2>&1 | tail -n 1)
  m=$(timeout 1800 python server/pkt_schema.py many $p 3000 2>&1 | tail -n 1)
  echo "$p | $c | $m" >> data/exe133/codec/batch_learn.txt
done
