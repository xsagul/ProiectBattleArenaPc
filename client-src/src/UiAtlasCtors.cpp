// flags: -O2 -std:c++17 -GR-
#include "UiAtlas.h"

namespace ui_native {

// The metadata callbacks of the sliced providers jump to these constructors
// instead of inlining them, so they are defined away from their users.

// match: aded90 ??0AtlasData3SliceH@ui_native@@QAE@XZ
AtlasData3SliceH::AtlasData3SliceH() = default;

// match: adee10 ??0AtlasData3SliceV@ui_native@@QAE@XZ
AtlasData3SliceV::AtlasData3SliceV() = default;

// match: adee90 ??0AtlasData9Slice@ui_native@@QAE@XZ
AtlasData9Slice::AtlasData9Slice() = default;

// Their vtables, and with them the inline mode getters, are emitted here.
// same: ebc40 ?GetMode@AtlasData3SliceH@ui_native@@UBEEXZ
// same: 1abe50 ?GetMode@AtlasData3SliceV@ui_native@@UBEEXZ
// same: 1abe40 ?GetMode@AtlasData9Slice@ui_native@@UBEEXZ

} // namespace ui_native
