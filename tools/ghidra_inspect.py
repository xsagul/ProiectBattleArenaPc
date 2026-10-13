"""Export decompilation, calls, instructions and optional P-code for client RVAs.

Use toolchain/reconstruction-env/Scripts/python.exe; stop the CLI bridge first.
Missing functions are created temporarily and all project edits are rolled back.
"""
import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rva', nargs='+', type=lambda value: int(value, 16))
    parser.add_argument('--pcode', action='store_true')
    parser.add_argument('--verified-abis', action='store_true',
                        help='Temporarily apply measured native ABIs and clear incorrect noreturn annotations')
    parser.add_argument('-o', '--output', type=pathlib.Path)
    args = parser.parse_args()
    tool_dir = pathlib.Path(__file__).resolve().parent
    sys.path[:] = [p for p in sys.path if pathlib.Path(p).resolve() != tool_dir]
    import pyghidra
    from jpype.types import JByte

    os.environ['JAVA_HOME'] = str(ROOT / 'toolchain/jdk-21.0.12.1+1')
    pyghidra.start(install_dir=ROOT / 'toolchain/ghidra_12.1.4_PUBLIC')
    from ghidra.app.decompiler import DecompInterface
    from ghidra.program.flatapi import FlatProgramAPI
    import jpype

    project = pyghidra.open_project(str(ROOT / 'client-src/ghidra'), 'BA13')
    report = {'base': '0x580000', 'saved': False, 'functions': []}
    try:
        with pyghidra.program_context(project, '/League of Legends.unpacked.exe') as program:
            base = int(program.getImageBase().getOffset())
            if base != 0x580000:
                raise ValueError(f'Unexpected client base: {base:#x}')
            space = program.getAddressFactory().getDefaultAddressSpace()
            api = FlatProgramAPI(program, pyghidra.task_monitor())
            decoder = DecompInterface()
            tx = program.startTransaction('Temporary function discovery for read-only export')
            try:
                if args.verified_abis:
                    from ghidra.program.model.data import VoidDataType, PointerDataType, UnsignedIntegerDataType
                    from ghidra.program.model.listing import Function, ParameterImpl
                    from ghidra.program.model.symbol import SourceType
                    pointer = PointerDataType(VoidDataType.dataType)
                    integer = UnsignedIntegerDataType.dataType
                    known = [(0xae14d0, '__thiscall', VoidDataType.dataType, []),
                             (0x9bab90, '__thiscall', VoidDataType.dataType, []),
                             (0x5894b0, '__thiscall', pointer, []),
                             (0x9ba240, '__thiscall', pointer, []),
                             (0x9bb8d0, '__cdecl', pointer, [integer]),
                             (0x9bb930, '__cdecl', VoidDataType.dataType, [pointer]),
                             (0x9bb940, '__cdecl', VoidDataType.dataType, [pointer, integer])]
                    applied = []
                    for rva, convention, returns, types in known:
                        entry = space.getAddress(base + rva)
                        native = program.getFunctionManager().getFunctionAt(entry)
                        if native is None:
                            api.disassemble(entry)
                            native = api.createFunction(entry, f'NativeProbe_{rva:x}')
                        if native is None:
                            raise ValueError(f'Cannot annotate native ABI at RVA {rva:#x}')
                        native.setNoReturn(False)
                        native.setCallingConvention(convention)
                        native.setReturnType(returns, SourceType.USER_DEFINED)
                        params = [ParameterImpl(f'a{i}', typ, program) for i, typ in enumerate(types)]
                        native.replaceParameters(Function.FunctionUpdateType.DYNAMIC_STORAGE_ALL_PARAMS,
                                                 True, SourceType.USER_DEFINED, *params)
                        applied.append(dict(rva=hex(rva), signature=str(native.getSignature())))
                    report['temporary_verified_abis'] = applied
                if not decoder.openProgram(program):
                    raise RuntimeError(str(decoder.getLastMessage()))
                with open(ROOT / 'client-src/exe_image_unpacked.bin', 'rb') as image:
                    for rva in args.rva:
                        if rva < 0:
                            raise ValueError('RVA must be nonnegative')
                        entry = space.getAddress(base + rva)
                        func = program.getFunctionManager().getFunctionAt(entry)
                        temporary = func is None
                        if temporary:
                            api.disassemble(entry)
                            func = api.createFunction(entry, f'Probe_{rva:x}')
                        if func is None:
                            raise ValueError(f'Cannot define function at RVA {rva:#x}')
                        if args.verified_abis:
                            from ghidra.program.model.listing import FlowOverride
                            from ghidra.app.cmd.function import CreateFunctionCmd
                            changed = []
                            native_entries = {item[0] for item in known}
                            for instruction in program.getListing().getInstructions(func.getBody(), True):
                                targets = [int(ref.getToAddress().getOffset()) - base
                                           for ref in instruction.getReferencesFrom()
                                           if ref.getReferenceType().isCall()]
                                # CALL_RETURN on a JMP represents a valid tail call.
                                # Only an actual CALL may have a stale noreturn override.
                                if str(instruction.getMnemonicString()).upper() == 'CALL' and any(target in native_entries for target in targets) and instruction.getFlowOverride() != FlowOverride.NONE:
                                    changed.append(instruction.getAddress())
                            for site in changed:
                                instruction = program.getListing().getInstructionAt(site)
                                instruction.setFlowOverride(FlowOverride.NONE)
                                api.disassemble(site.add(instruction.getLength()))
                            if changed:
                                func.setBody(CreateFunctionCmd.getFunctionBody(program, entry, pyghidra.task_monitor()))
                            report.setdefault('cleared_call_flow_overrides', []).extend(str(site) for site in changed)
                        decoder.flushCache()
                        result = decoder.decompileFunction(func, 60, pyghidra.task_monitor())
                        if not result.decompileCompleted():
                            raise RuntimeError(str(result.getErrorMessage()))
                        instructions, calls = [], []
                        for ins in program.getListing().getInstructions(func.getBody(), True):
                            offset = int(ins.getAddress().getOffset()) - base
                            raw = jpype.JArray(JByte)(int(ins.getLength()))
                            program.getMemory().getBytes(ins.getAddress(), raw)
                            raw = bytes(int(value) & 255 for value in raw)
                            image.seek(offset)
                            if raw != image.read(len(raw)):
                                raise ValueError(f'Client/Ghidra byte mismatch at RVA {offset:#x}')
                            record = dict(rva=hex(offset), bytes=raw.hex(), asm=str(ins))
                            if args.pcode:
                                record['pcode'] = [str(op) for op in ins.getPcode()]
                            instructions.append(record)
                            for ref in ins.getReferencesFrom():
                                if ref.getReferenceType().isCall():
                                    calls.append(dict(site_rva=hex(offset), target_va=str(ref.getToAddress()),
                                                      target_rva=hex(int(ref.getToAddress().getOffset()) - base)))
                        report['functions'].append(dict(rva=hex(rva), va=hex(base + rva),
                            temporary_function=temporary, signature=str(func.getSignature()),
                            decompiled=str(result.getDecompiledFunction().getC()),
                            instructions=instructions, outgoing_calls=calls))
            finally:
                decoder.dispose()
                program.endTransaction(tx, False)
    finally:
        project.close()
    content = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding='utf-8')
        print(args.output)
    else:
        print(content)


if __name__ == '__main__':
    main()
