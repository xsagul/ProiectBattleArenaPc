#!/bin/bash
# The Ghidra workspace of the 13.3 client (client-src/ghidra/BA13.gpr), headless.
#   ghidra.sh import            import game/League of Legends.unpacked.exe, apply our names, analyze (long: hours)
#   ghidra.sh decomp [filter]   decompile every function (or those whose name contains filter) -> client-src/decomp/
#   ghidra.sh names             re-apply client-src/names.tsv (after tools/ghidra_names.py) without re-analyzing
# Open it with the GUI too: toolchain/ghidra_12.1.4_PUBLIC/ghidraRun.bat, File > Open Project > client-src/ghidra/BA13.gpr
cd "$(dirname "$0")/.."
ROOT="$(cygpath -w "$(pwd)")"
export JAVA_HOME="$ROOT\toolchain\jdk-21.0.12.1+1"
export PATH="$(cygpath -u "$JAVA_HOME")/bin:$PATH"
G="$ROOT\toolchain\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat"
P="$ROOT\client-src\ghidra"
mkdir -p client-src/ghidra
case "$1" in
  import)
    cmd //c "$G" "$P" BA13 -import "$ROOT\game\League of Legends.unpacked.exe" -overwrite \
      -scriptPath "$ROOT\tools\ghidra" -preScript ApplyNames.java "$ROOT\client-src\names.tsv" \
      -max-cpu 8 -analysisTimeoutPerFile 36000 ;;
  decomp)
    cmd //c "$G" "$P" BA13 -process "League of Legends.unpacked.exe" -noanalysis -readOnly \
      -scriptPath "$ROOT\tools\ghidra" -postScript ExportDecomp.java "$ROOT\client-src\decomp" $2 ;;
  names)
    cmd //c "$G" "$P" BA13 -process "League of Legends.unpacked.exe" -noanalysis \
      -scriptPath "$ROOT\tools\ghidra" -postScript ApplyNames.java "$ROOT\client-src\names.tsv" ;;
  *) sed -n 2,6p "$0" ;;
esac
