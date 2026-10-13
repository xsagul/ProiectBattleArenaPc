# Isolated VFX ownership candidate

Run from the workspace root:

```powershell
python experiments/reconstruction_search/vfx_candidate/gen_vfx_owned.py --probe-only
python experiments/reconstruction_search/vfx_candidate/verify_guards.py
```

The first command validates five metadata descriptions, one trivial scalar dependency, two native helper bodies and ten independently compiled Destroy/Destruct callbacks. The measured result is 12/12 exact functions covering 808 bytes, including every relocation target. This is candidate coverage, not a claimed improvement to the production score.

All emitted files stay in this directory. Compiler objects stay under `client-src/obj`, as required by the existing compiler helper. No source enters `M.sources`, no production file is edited, and temporary helper bindings are restored in `finally`. The audit records unchanged source discovery, hashes of watched production files, and the completed binding restoration check.

`metadata` resolves every member and preserves its wrapper body and descriptor. `candidate` adds creation fingerprints, destruction bodies, helper bodies and the selected runtime fields. `fields` renders the proposed native storage. `layout_of` revalidates the saved manifest before returning any fields. `verify` compiles each actual body, checks all bytes and explicit targets, and introduces temporary helper names only after the corresponding body passes. Rejected proposals raise structured mismatch details for a future search coordinator to cache.

The serializable list tag at `VfxAnimatedVector3fVariableData::probabilityTables` describes three native owned pointers. The defaulted destructor of `VfxProbabilityOwners` proves the reverse destruction loop at RVA `a64c90` (79 bytes). The separately compiled `VfxOwnedPointer<FlexValueVector3>` destructor proves RVA `a64b00` (92 bytes), including the nested dynamic object, raw allocation, signed-capacity buffers and the call to that array destructor. Keeping these two bodies in separate translation units preserves the client's actual call boundary without inlining attributes.

Runtime member storage is tied to both metadata and complete destruction:

| Class | Native size | Members with lifetimes |
|---|---:|---|
| VfxProbabilityTableData | 32 | float buffers at 0 and 12 |
| VfxAnimatedVector3fVariableData | 64 | three owned pointers at 0, float buffer at 12, Vector3 buffer at 24, raw allocation at 60 |
| ValueVector3 | 16 | owned dynamics pointer at 12 |
| FlexValueVector3 | 20 | embedded ValueVector3 at 4 |
| VfxFlexShapeDefinitionData | 36 | owned FlexTypeFloat pointer at 28, owned FlexValueVector3 pointer at 32 |

The candidate does not publish or claim constructors. Their image bodies are saved as fingerprints; emitted default initializers must still pass full constructor comparisons before production use.

For later integration, include `VfxOwnedPointers.h` before class definitions, emit `ValueVector3` before its embedded use in `FlexValueVector3`, and use implicit destruction for these five classes. The helper header uses forward declarations, so pointer dependencies do not impose definition ordering. Production publication and lifecycle marker ownership remain the coordinator's separate work after the baseline audit.

The rejection checks cover incompatible size, a newly introduced base class, a changed pointer's pointee, a changed helper body and a deliberately wrong operator-delete target. They restore the manifest even when a guard fails.
