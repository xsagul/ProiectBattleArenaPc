// flags: -O2 -std:c++17 -GR-
#include "UiAtlas.h"

namespace ui_native {

// match: aecd80 ?CropAtlasUV@ui_native@@
void CropAtlasUV(const Vector4& source, u32 width, u32 height, Vector4& uv) {
    const float targetAspect = float(width) / float(height);
    const float sourceWidth = source.z - source.x;
    const float sourceHeight = source.w - source.y;
    const float sourceAspect = sourceWidth / sourceHeight;
    if (targetAspect > sourceAspect) {
        const float inset = (sourceHeight - sourceWidth / targetAspect) * 0.5f;
        uv.y = inset + uv.y;
        uv.w -= inset;
    } else if (sourceAspect > targetAspect) {
        const float inset = (sourceWidth - sourceHeight * targetAspect) * 0.5f;
        uv.x = inset + uv.x;
        uv.z -= inset;
    }
}

} // namespace ui_native
