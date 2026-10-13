"""Run the verified portable Ghidra CLI against the existing BA13 project.

Addresses are virtual addresses, not RVAs. Example:
  python tools/ghidra_cli.py decompile 0x864990 --with-vars --with-params
The native command's general help and type-management commands remain available.
Only invoke one Ghidra bridge or PyGhidra reader on BA13 at a time.
"""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    exe = ROOT / 'toolchain/ghidra-cli/ghidra.exe'
    ghidra = ROOT / 'toolchain/ghidra_12.1.4_PUBLIC'
    java = ROOT / 'toolchain/jdk-21.0.12.1+1'
    if not exe.exists() or not ghidra.exists() or not java.exists():
        raise SystemExit('Portable Ghidra CLI, Ghidra 12.1.4 and full JDK 21 are required in toolchain/.')
    args = sys.argv[1:] or ['--help']
    if args[:2] == ['function', 'calls']:
        raise SystemExit('Ghidra CLI v0.2.2 returns incoming references for function calls. '
                         'Use x-ref for callers; the PyGhidra probe explicitly verifies outgoing calls.')
    env = dict(os.environ, GHIDRA_INSTALL_DIR=str(ghidra),
               GHIDRA_CLI_CONFIG=str(exe.parent / 'config.yaml'))
    command = [str(exe), '--java-home', str(java), '--projects-dir', str(ROOT / 'client-src/ghidra'),
               '--project', 'BA13', '--program', 'League of Legends.unpacked.exe', '--json', *args]
    return subprocess.call(command, cwd=ROOT, env=env)


if __name__ == '__main__':
    sys.exit(main())
