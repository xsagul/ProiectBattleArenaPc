"""Meaningful rejection checks for the isolated candidate's evidence gates."""
import copy
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_vfx_owned as V
import gen_sources as G
import gen_meta as A

im = G.Image()
a = A.analysis(im)
facts = A.class_facts(im, a)
g = next(g for g in facts if a.cls[g] == 'VfxFlexShapeDefinitionData')
f = facts[g]
assert V.candidate(im, a, f, g) is not None
wrong_size = dict(f, size=f['size'] + 4)
assert V.candidate(im, a, wrong_size, g) is None
wrong_parent = dict(f, parent=123)
assert V.candidate(im, a, wrong_parent, g) is None

original = V.MANIFEST.read_bytes()
manifest = json.loads(original)
try:
    # A plausible scalar pointer type with a different pointee lifetime must fail.
    bad = copy.deepcopy(manifest)
    row = next(x for x in bad['classes'] if x['name'] == a.cls[g])
    row['members'][-1]['serialized_type'] = 'MetaPointer<FlexTypeFloat>'
    V.MANIFEST.write_text(json.dumps(bad), encoding='utf-8')
    try:
        V.layout_of(im, a, f, g)
        raise AssertionError('Changed pointee accepted')
    except ValueError:
        pass
    # Changing a stored native body invalidates the proposed layout.
    bad = copy.deepcopy(manifest)
    bad['helpers'][0]['body'] += '\nret'
    V.MANIFEST.write_text(json.dumps(bad), encoding='utf-8')
    try:
        V.layout_of(im, a, f, g)
        raise AssertionError('Changed native body accepted')
    except ValueError:
        pass
finally:
    V.MANIFEST.write_bytes(original)

# Relocation identity is enforced independently of matching bytes.
path = V.BUNDLE / 'VfxProbabilityOwners.cpp'
obj = V.M.compile_obj(str(path), V.FLAGS)
bad_targets = dict(V.OPERATORS)
bad_targets['??3@YAXPAX@Z'] += 16
try:
    V.check(path, V.HELPERS[0]['symbol'], V.HELPERS[0]['rva'], obj, bad_targets)
    raise AssertionError('Wrong relocation mapping accepted')
except ValueError:
    pass

assert V.layout_of(im, a, f, g)
print('VFX guards: wrong size, parent, pointee, native body, and target rejected; evidence restored.')
