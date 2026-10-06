# Builds the project with the portable toolchain in toolchain/ (CMake + llvm-mingw Clang), no installation needed.
#   powershell -ExecutionPolicy Bypass -File build.ps1 [-Config Release|Debug] [-Clean] [-Out build-clang]
#   (-Out: another build folder, e.g. to test while the game in build-clang is running)
param([string]$Config = "Release", [switch]$Clean, [string]$Out = "build-clang")

$root = $PSScriptRoot
$cmake = Join-Path $root "toolchain\cmake-4.4.3-windows-x86_64\bin\cmake.exe"
$llvm = Join-Path $root "toolchain\llvm-mingw-20260922-ucrt-x86_64\bin"
$build = Join-Path $root $Out
$env:PATH = "$llvm;$env:PATH"

if ($Clean -and (Test-Path $build)) { Remove-Item -Recurse -Force $build -Confirm:$false }

# A game that is running keeps its .exe files locked, and the linker cannot write over them. Windows lets a running
# program be renamed: the locked ones are moved aside (the running game goes on from the moved file) and a copy takes
# their name, which the build can then replace. Left-overs of earlier builds are removed once nothing runs from them.
$bin = Join-Path $build "bin"
if (Test-Path $bin) {
  Get-ChildItem $bin -Filter "*.old.exe" | ForEach-Object { try { Remove-Item $_.FullName -Force -ErrorAction Stop } catch {} }
  foreach ($exe in Get-ChildItem $bin -Filter "*.exe" | Where-Object { $_.Name -notlike "*.old.exe" }) {
    try {
      $s = [IO.File]::Open($exe.FullName, 'Open', 'ReadWrite', 'None')
      $s.Close()
    } catch {
      $aside = Join-Path $bin ($exe.BaseName + "." + [DateTime]::Now.Ticks + ".old.exe")
      Rename-Item $exe.FullName $aside
      Copy-Item $aside $exe.FullName
    }
  }
}
& $cmake -S $root -B $build -G "MinGW Makefiles" `
  -DCMAKE_BUILD_TYPE=$Config `
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ `
  -DCMAKE_MAKE_PROGRAM=mingw32-make
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $cmake --build $build -j 8
exit $LASTEXITCODE
