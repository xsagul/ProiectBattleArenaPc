"""Reconstruct real default-constructor ABIs from already verified Small bodies.

Only declared constructors in BinClasses.h are considered. The matching Small
body must take no arguments and return this (or nothing). Its final synthetic
return is removed; C++ emits the constructor return and implicit base/vptr
initialization. A first call to the declared parent's constructor is removed
only when both its RVA and its receiver exactly identify that base constructor.
Every accepted alias is backed by the separately compiled real constructor.

Run: python tools/gen_meta_ctors.py
"""
import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import match_func as M

GEN = ROOT / 'client-src/src/gen'
OUT = GEN / 'MetaConstructors.cpp'
PROBE = ROOT / 'client-src/obj/agent_ctor_candidates.cpp'
AUDIT = ROOT / 'client-src/obj/agent_ctor_audit.json'


def classes(header):
    result = {}
    pattern = r'^struct (?:alignas\([^\n]+?\) )?(\w+)(?: : (\w+))?\n\{\n(.*?)^\};'
    for m in re.finditer(pattern, header, re.M | re.S):
        name, parent, body = m.groups()
        ctor = re.search(r'^    ' + re.escape(name) + r'\(\);\s*// rva 0x([0-9a-f]+)', body, re.M)
        strings = [int(x, 16) for x in re.findall(r'^    (?:::)?MetaString \w+;\s*// \+0x([0-9a-f]+)', body, re.M)]
        result[name] = dict(parent=parent, rva=int(ctor[1], 16) if ctor else None, strings=strings)
    return result


def member_initializers(body, name, info):
    """Drop exact default-string stores already emitted by real C++ members.

    This transforms a candidate only; complete byte/target comparison remains
    mandatory before publishing its constructor ABI.
    """
    offsets, seen = set(), set()
    while name in info and name not in seen:
        seen.add(name)
        offsets.update(info[name].get('strings', ()))
        name = info[name]['parent']
    lines = body.splitlines()

    def store(line):
        m = re.fullmatch(r'    \*\(int\*\)\(\(\(int\)this \+ (\d+)\)\) = '
                         r'(g_1b467f0|\*\(int\*\)\(\(int\)&g_1b467f0\)|0);', line)
        return (int(m[1]), '0' if m[2] == '0' else 'g_1b467f0') if m else None

    out, i = [], 0
    while i < len(lines):
        s = store(lines[i])
        if s and s[0] in offsets and s[1] == 'g_1b467f0' and i + 2 < len(lines) and \
                store(lines[i + 1]) == (s[0] + 4, '0') and store(lines[i + 2]) == (s[0] + 8, '0'):
            i += 3
        else:
            out.append(lines[i])
            i += 1
    return '\n'.join(out) + ('\n' if out else '')


def small_sources():
    from gen_meta_placements import TYPED_GLOBALS
    declarations, bodies = set(), {}
    for p in sorted(GEN.glob('Small_*.cpp')):
        source = p.read_text(encoding='utf-8')
        first_body = re.search(r'^[^\n]*\{  // @[0-9a-f]+\n', source, re.M)
        if first_body:
            for line in source[:first_body.start()].splitlines():
                if line.startswith(('extern ', 'struct ', '__declspec(', 'int ', 'void ', 'unsigned char ')):
                    scalar_global=re.fullmatch(r'extern int (g_[0-9a-f]+);',line)
                    if scalar_global and scalar_global[1] in TYPED_GLOBALS:
                        # BinClasses includes the native pointer declaration.
                        continue
                    declarations.add(line)
        for m in re.finditer(r'^(?:int|void) K([0-9a-f]+)::f\(\) \{  // @\1\n(.*?)^\}\n', source, re.M | re.S):
            body = m[2]
            if 'return ' in body:
                if not body.endswith('    return (int)this;\n') or body.count('return ') != 1:
                    continue
                body = body[:-len('    return (int)this;\n')]
            bodies[int(m[1], 16)] = dict(body=body, source=p.name)
    return sorted(declarations), bodies


def thin_base_inline_prefix(body,parent_name,info,bodies):
    """An intermediate base only changes the vptr after its parent's ctor.

    A derived constructor can inline the ancestor stores and overwrite that
    intermediate vptr. No intermediate member initialization may be discarded.
    Final byte/target verification remains mandatory for every candidate.
    """
    seen=set()
    while parent_name in info and parent_name not in seen:
        seen.add(parent_name)
        parent=info[parent_name];ancestor_name=parent['parent']
        ancestor=info.get(ancestor_name,{})
        ancestor_rva=ancestor.get('rva');parent_rva=parent.get('rva')
        if parent_rva not in bodies or ancestor_rva not in bodies:return None
        lines=bodies[parent_rva]['body'].splitlines()
        call=rf'    \(\([KT]{ancestor_rva:x}\*\)\(int\)this\)->f\(\);'
        vptr=r'    \*\(int\*\)\(\(int\)this\) = \(int\)&g_[0-9a-f]+;'
        prefix=bodies[ancestor_rva]['body']
        direct=len(lines)==2 and re.fullmatch(call,lines[0]) and re.fullmatch(vptr,lines[1])
        flattened=bool(prefix) and bodies[parent_rva]['body'].startswith(prefix) and \
            re.fullmatch(vptr,bodies[parent_rva]['body'][len(prefix):].rstrip('\n'))
        if not direct and not flattened:return None
        if prefix and body.startswith(prefix):return body[len(prefix):],ancestor_rva
        parent_name=ancestor_name
    return None


def exact_base_call(line,rva,parent_name):
    """Only the established zero-argument base ABI on this can be elided."""
    if re.fullmatch(rf'    \(\([KT]{rva:x}\*\)\(int\)this\)->f\(\);',line):
        return True
    from gen_small import NATIVE_CALLS
    native=NATIVE_CALLS.get(rva)
    return bool(native and native[:3]==(parent_name,parent_name,0) and
                line=='    (int)(new ((void*)(int)this) '+parent_name+');')


def render(declarations, items, claims=False, absolute=False, info=None):
    include = str(GEN / 'BinClasses.h').replace('\\', '/') if absolute else 'BinClasses.h'
    lines = ['// Real default constructors reconstructed from verified Small bodies.',
             '// Generated by tools/gen_meta_ctors.py; every alias has a compiled identical body.']
    if claims:
        lines.extend(f'// same: {item["rva"]:x} ??0{name}@@' for name, item in sorted(items.items()))
    lines.extend([f'#include "{include}"', '#include <stdlib.h>', '#include <new>', ''])
    lines.extend(declarations)
    lines.append('')
    def depth(name):
        parents, seen = 0, set()
        while info and name in info and info[name]['parent'] and name not in seen:
            seen.add(name)
            name = info[name]['parent']
            parents += 1
        return parents
    for name, item in sorted(items.items(), key=lambda x: (depth(x[0]), x[0])):
        lines.append(f'{name}::{name}() {{  // @{item["rva"]:x}')
        lines.extend(item['body'].splitlines())
        lines.extend(['}', ''])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--header',type=pathlib.Path,default=GEN/'BinClasses.h')
    parser.add_argument('--output-directory',type=pathlib.Path,default=GEN)
    parser.add_argument('--audit',type=pathlib.Path,default=AUDIT)
    args=parser.parse_args()
    header=args.header.resolve()
    destination=args.output_directory.resolve()
    destination.mkdir(parents=True,exist_ok=True)
    info = classes(header.read_text(encoding='utf-8'))
    declarations, bodies = small_sources()
    candidates, skipped = {}, []
    external=set()
    for source in M.sources():
        path=pathlib.Path(source)
        if path.name=='MetaConstructors.cpp' or path.name.startswith('MetaCtorCalls_'):continue
        external.update(re.findall(r'^\s*(?:__declspec\(noinline\) )?(\w+)::\1\(',path.read_text(encoding='utf-8'),re.M))
    for name, c in sorted(info.items()):
        if c['rva'] is None:
            continue
        if name in external:
            skipped.append(dict(name=name,rva=c['rva'],reason='real constructor definition owned by another source'))
            continue
        if c['rva'] not in bodies:
            skipped.append(dict(name=name, rva=c['rva'], reason='no verified zero-argument Small constructor body'))
            continue
        item = dict(bodies[c['rva']], rva=c['rva'], base_call_removed=False)
        parent_name = c['parent']
        while parent_name in info and info[parent_name]['rva'] is None:
            parent_name = info[parent_name]['parent']
        parent = info.get(parent_name, {})
        base_rva = parent.get('rva')
        if base_rva is not None:
            inherited_prefix=thin_base_inline_prefix(item['body'],parent_name,info,bodies)
            first, sep, rest = item['body'].partition('\n')
            if exact_base_call(first,base_rva,parent_name):
                item['body'] = rest
                item['base_call_removed'] = True
            elif base_rva in bodies and item['body'].startswith(bodies[base_rva]['body']):
                # The client inlined this exact base initialization. Let C++
                # generate it from the real base body in the same TU.
                item['body']=item['body'][len(bodies[base_rva]['body']):]
                item['base_inline_prefix_removed']=True
            elif base_rva in bodies and all(re.fullmatch(r'    \*\((?:int|signed char|short)\*\)\(.*\) = .*;',line)
                                          and '(int)this' in line.split(' = ',1)[0]
                                          for line in bodies[base_rva]['body'].splitlines()):
                # A store-only base may be inlined and overwritten by the
                # existing body's stores. No external effects are discarded;
                # the compiled body must prove the resulting order exactly.
                item['base_store_only']=True
            elif inherited_prefix is not None:
                item['body'],ancestor_rva=inherited_prefix
                item['base_inherited_inline_prefix_removed']=ancestor_rva
            else:
                skipped.append(dict(name=name, rva=c['rva'], reason='declared base constructor is not the first exact Small call'))
                continue
        item['body'] = member_initializers(item['body'], name, info)
        candidates[name] = item
    print('Declared constructors:', sum(c['rva'] is not None for c in info.values()),
          'candidates:', len(candidates), 'skipped:', len(skipped), flush=True)
    def text(items,claims=False):
        source=render(declarations,items,claims=claims,absolute=True,info=info)
        return source.replace(str(GEN/'BinClasses.h').replace('\\','/'),str(header).replace('\\','/'))
    PROBE.write_text(text(candidates),encoding='utf-8',newline='\n')
    obj=M.compile_obj(str(PROBE),M.FLAGS)
    saved=copy.deepcopy(M.rebuilt_symbols())
    M.rebuilt_symbols.v=copy.deepcopy(saved)
    keep,groups,rejected,solo={}, {}, {}, {}

    def result(name,path,objpath):
        item=candidates[name]
        x=M.compare(str(path),f'??0{name}@@',item['rva'],M.FLAGS,objpath)
        if x[3] is not None:
            rejected[name]=dict(name=name,rva=item['rva'],bytes=x[1],identical_bytes=x[2],first=x[3],detail=x[4])
        return x

    def accept(name,group,x):
        item=candidates[name]
        keep[name]=item
        groups[name]=group
        item['bytes']=x[1]
        rejected.pop(name,None)
        alias=f'??0{name}@@'
        # Only a real body that has just passed byte AND target comparison is
        # exposed to subsequent constructor checks. This local proof inventory
        # is restored afterwards; unverified aliases are never introduced.
        aliases=M.rebuilt_symbols().setdefault(item['rva'],[])
        if alias not in aliases: aliases.append(alias)

    try:
        for attempt in range(len(candidates)+1):
            accepted=[]
            for name in candidates:
                if name in keep: continue
                x=result(name,PROBE,obj)
                if x[3] is None:
                    accept(name,'shared',x)
                    accepted.append(name)
            print('Shared pass',attempt+1,'accepted',len(accepted),'total',len(keep),flush=True)
            if not accepted: break
        # A caller whose client code calls its base must sometimes live in a
        # TU that cannot inline that base body. Test this real source boundary,
        # rather than imposing a noinline attribute on every constructor.
        for name in candidates:
            if name in keep: continue
            tag=f'{candidates[name]["rva"]:x}_{hashlib.sha1(name.encode()).hexdigest()[:8]}'
            path=PROBE.with_name(f'agent_ctor_isolated_{tag}.cpp')
            path.write_text(text({name:candidates[name]}),encoding='utf-8',newline='\n')
            solo[name]=(path,M.compile_obj(str(path),M.FLAGS))
        for attempt in range(len(solo)+1):
            accepted=[]
            for name,(path,objpath) in solo.items():
                if name in keep: continue
                x=result(name,path,objpath)
                if x[3] is None:
                    accept(name,'isolated',x)
                    accepted.append(name)
            print('Isolated pass',attempt+1,'accepted',len(accepted),'total',len(keep),flush=True)
            if not accepted: break
        # Removing rejected definitions can alter inlining. Recompile the
        # actual retained shared source before publishing any new aliases.
        final_probe=PROBE.with_name('agent_ctor_final_shared.cpp')
        for attempt in range(len(keep)+1):
            shared={n:i for n,i in keep.items() if groups[n]=='shared'}
            final_probe.write_text(text(shared),encoding='utf-8',newline='\n')
            final_obj=M.compile_obj(str(final_probe),M.FLAGS)
            changed=[]
            for name in list(shared):
                x=result(name,final_probe,final_obj)
                if x[3] is None:
                    candidates[name]['bytes']=x[1]
                    continue
                changed.append(name)
                if name not in solo:
                    tag=f'{candidates[name]["rva"]:x}_{hashlib.sha1(name.encode()).hexdigest()[:8]}'
                    path=PROBE.with_name(f'agent_ctor_isolated_{tag}.cpp')
                    path.write_text(text({name:candidates[name]}),encoding='utf-8',newline='\n')
                    solo[name]=(path,M.compile_obj(str(path),M.FLAGS))
                x=result(name,*solo[name])
                if x[3] is None:
                    accept(name,'isolated',x)
                else:
                    del keep[name]
                    del groups[name]
                    alias=f'??0{name}@@'
                    if alias not in saved.get(candidates[name]['rva'],[]):
                        M.rebuilt_symbols()[candidates[name]['rva']].remove(alias)
            if not changed: break
        verified=[]
        for name,item in keep.items():
            verified.append(dict(name=name,rva=item['rva'],bytes=item['bytes'],
                                 base_call_removed=item['base_call_removed'],translation_unit=groups[name]))
        shared={n:i for n,i in keep.items() if groups[n]=='shared'}
        (destination/'MetaConstructors.cpp').write_text(text(shared,True),encoding='utf-8',newline='\n')
        output_names={'MetaConstructors.cpp'}
        for name,item in keep.items():
            if groups[name]!='isolated': continue
            tag=f'{item["rva"]:x}_{hashlib.sha1(name.encode()).hexdigest()[:8]}'
            filename=f'MetaCtorCalls_{tag}.cpp'
            (destination/filename).write_text(text({name:item},True),encoding='utf-8',newline='\n')
            output_names.add(filename)
        # These files are exclusively generated by this tool. Remove only
        # previously generated shards that are no longer in the proved set.
        for stale in destination.glob('MetaCtorCalls_*.cpp'):
            if stale.name not in output_names:
                marker='// Generated by tools/gen_meta_ctors.py;'
                if marker not in stale.read_text(encoding='utf-8')[:300]:
                    raise ValueError(f'Refusing to remove a constructor shard not owned by this generator: {stale}')
                stale.unlink()
        args.audit.write_text(json.dumps(dict(verified=verified,rejected=list(rejected.values()),skipped=skipped),indent=2),encoding='utf-8')
    finally:
        M.rebuilt_symbols.v=saved
    print('Verified real constructor ABIs:',len(verified),'unique RVAs:',len({x['rva'] for x in verified}),
          'bytes:',sum(x['bytes'] for x in verified),'rejected:',len(rejected),flush=True)


if __name__ == '__main__':
    main()
