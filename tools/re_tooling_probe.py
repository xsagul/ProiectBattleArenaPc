"""Read-only PyGhidra/type-recovery and Z3 smoke test on the actual client.

Run after `python tools/ghidra_cli.py stop`, using the isolated interpreter:
  toolchain/reconstruction-env/Scripts/python.exe tools/re_tooling_probe.py
No analysis annotations, bytes or source claims are saved to the client project.
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    # The sibling tools/ghidra directory otherwise shadows JPype's Java package.
    tool_dir = pathlib.Path(__file__).resolve().parent
    sys.path[:] = [p for p in sys.path if pathlib.Path(p).resolve() != tool_dir]
    import pyghidra
    import z3
    os.environ['JAVA_HOME'] = str(ROOT / 'toolchain/jdk-21.0.12.1+1')
    pyghidra.start(install_dir=ROOT / 'toolchain/ghidra_12.1.4_PUBLIC')
    from ghidra.app.decompiler import DecompInterface
    from ghidra.program.model.data import StructureDataType, PointerDataType, CharDataType, UnsignedIntegerDataType, VoidDataType
    from ghidra.program.model.listing import ParameterImpl, Function
    from ghidra.program.model.symbol import SourceType
    from ghidra.program.flatapi import FlatProgramAPI
    from jpype.types import JByte

    project = pyghidra.open_project(str(ROOT / 'client-src/ghidra'), 'BA13')
    report = {}
    try:
        with pyghidra.program_context(project, '/League of Legends.unpacked.exe') as program:
            base = int(program.getImageBase().getOffset())
            if base != 0x580000:
                raise ValueError(f'Unexpected client image base: {base:#x}')
            space = program.getAddressFactory().getDefaultAddressSpace()
            address = lambda rva: space.getAddress(base + rva)
            replay = program.getFunctionManager().getFunctionAt(address(0x2e4990))
            data = __import__('jpype').JArray(JByte)(36)
            program.getMemory().getBytes(replay.getEntryPoint(), data)
            actual = bytes(int(b) & 255 for b in data)
            with open(ROOT / 'client-src/exe_image_unpacked.bin', 'rb') as image:
                image.seek(0x2e4990)
                expected = image.read(36)
            if actual != expected:
                raise ValueError('Ghidra replay bytes differ from the authoritative unpacked image')
            calls = []
            for instruction in program.getListing().getInstructions(replay.getBody(), True):
                for ref in instruction.getReferencesFrom():
                    if ref.getReferenceType().isCall():
                        calls.append(int(ref.getToAddress().getOffset()) - base)
            if calls != [0x996470]:
                raise ValueError(f'Unexpected Replay outgoing calls: {calls}')
            report['replay'] = dict(rva='0x2e4990', identical_bytes=len(actual), outgoing_rvas=[hex(x) for x in calls])

            tx = program.startTransaction('Temporary proved placement ABI and field hints')
            decoder = DecompInterface()
            original_function = program.getFunctionManager().getFunctionAt(address(0x188980))
            original_type = program.getDataTypeManager().getDataType('/ProvedStringValue16')
            try:
                func = program.getFunctionManager().getFunctionAt(address(0x188980))
                if func is None:
                    api = FlatProgramAPI(program, pyghidra.task_monitor())
                    api.disassemble(address(0x188980))
                    func = api.createFunction(address(0x188980), 'ProbePlacement188980')
                if func is None:
                    raise ValueError('Cannot create temporary placement function at RVA 0x188980')
                if not decoder.openProgram(program):
                    raise RuntimeError('Cannot start Ghidra decompiler: ' + str(decoder.getLastMessage()))

                def decompile():
                    result = decoder.decompileFunction(func, 60, pyghidra.task_monitor())
                    if not result.decompileCompleted():
                        raise ValueError(str(result.getErrorMessage()))
                    return str(result.getDecompiledFunction().getC())

                before = decompile()
                record = StructureDataType('ProvedStringValue16', 0)
                record.add(PointerDataType(CharDataType.dataType), 'data', None)
                for name in ('size', 'capacity', 'value'):
                    record.add(UnsignedIntegerDataType.dataType, name, None)
                record = program.getDataTypeManager().addDataType(record, None)
                func.setCallingConvention('__cdecl')
                func.setReturnType(VoidDataType.dataType, SourceType.USER_DEFINED)
                param = ParameterImpl('p', PointerDataType(record), program)
                func.replaceParameters(Function.FunctionUpdateType.DYNAMIC_STORAGE_ALL_PARAMS, True,
                                       SourceType.USER_DEFINED, param)
                decoder.flushCache()
                after = decompile()
                if 'void ' not in after or not all('->' + name in after for name in ('data', 'size', 'capacity', 'value')):
                    raise ValueError('Type hints did not produce the expected structured placement body')
                report['placement'] = dict(rva='0x188980', before=before, after=after, saved=False)
            finally:
                program.endTransaction(tx, False)
                decoder.dispose()
            if program.getFunctionManager().getFunctionAt(address(0x188980)) != original_function:
                raise ValueError('Temporary function was not rolled back')
            if program.getDataTypeManager().getDataType('/ProvedStringValue16') != original_type:
                raise ValueError('Temporary structure was not rolled back')
            report['placement']['rollback_verified'] = True
    finally:
        project.close()

    x, y = z3.BitVecs('x y', 32)
    solver = z3.Solver()
    solver.add(x * y != y * x)
    positive = solver.check()
    if positive != z3.unsat:
        raise ValueError('Unexpected unsigned modular multiplication result')
    solver = z3.Solver()
    solver.add(x / 2 != (x >> 1))
    negative = solver.check()
    if negative != z3.sat:
        raise ValueError('Expected signed-division/shift counterexample')
    report['z3'] = dict(version=z3.get_version_string(), unsigned_mul_commutes=str(positive),
                        signed_div_vs_shift=str(negative), counterexample=str(solver.model()),
                        scope='semantic bit-vector proof only; not an instruction-byte or C++ lifetime proof')
    path = ROOT / 'client-src/obj/tooling-research/pyghidra-z3-probe.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Verified: client bytes, outgoing call, structured void placement ABI (rolled back), Z3 positive/negative cases.')
    print(path)


if __name__ == '__main__':
    main()
