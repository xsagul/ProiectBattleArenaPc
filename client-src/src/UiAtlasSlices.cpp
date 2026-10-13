// flags: -O2 -std:c++17 -GR-
#include "UiAtlas.h"
#include <utility>

namespace ui_native {

// The client scales vectors component by component; these plain loops are
// the source form that reproduces its instruction order.
static __forceinline void Normalize(Vector4& v, u32 resolution) {
    if (float(resolution) != 0.f) {
        const float scale = 1.f / float(resolution);
        float* components = &v.x;
        for (int i = 0; i < 4; ++i) components[i] *= scale;
    }
}

static __forceinline void Scale(Vector2& v, float scale) {
    float* components = &v.x;
    for (int i = 0; i < 2; ++i) components[i] *= scale;
}

// match: ae63e0 ?CalculateThreeSliceH@ui_native@@
void CalculateThreeSliceH(const u32& flags, float unknown4, float unknown5,
    const Vector4& us, const Vector2& vs, u32 sourceWidth, u32 sourceHeight,
    const Vector2& leftRight, TextureCoordinates& coordinates, TextureBorders& borders) {
    coordinates.first = us;
    coordinates.second = {vs.x, vs.y, 0, 0};
    Normalize(coordinates.first, sourceWidth);
    Normalize(coordinates.second, sourceHeight);
    if (flags & 0x200) {
        std::swap(coordinates.first.x, coordinates.first.w);
        std::swap(coordinates.first.y, coordinates.first.z);
    }
    if (flags & 0x400)
        std::swap(coordinates.second.x, coordinates.second.y);
    const float inverseX = 1.f / unknown5;
    borders.first = leftRight;
    Scale(borders.first, inverseX);
    Scale(borders.first, unknown4);
}

// match: ae6510 ?CalculateThreeSliceV@ui_native@@
void CalculateThreeSliceV(const u32& flags, float unknown6,
    const Vector2& us, const Vector4& vs, u32 sourceWidth, u32 sourceHeight,
    const Vector2& topBottom, TextureCoordinates& coordinates, TextureBorders& borders) {
    coordinates.first = {us.x, us.y, 0, 0};
    coordinates.second = vs;
    Normalize(coordinates.first, sourceWidth);
    Normalize(coordinates.second, sourceHeight);
    if (flags & 0x200)
        std::swap(coordinates.first.x, coordinates.first.y);
    if (flags & 0x400) {
        std::swap(coordinates.second.x, coordinates.second.w);
        std::swap(coordinates.second.y, coordinates.second.z);
    }
    const float inverseY = 1.f / unknown6;
    borders.first = topBottom;
    Scale(borders.first, inverseY);
}

// match: ae4e40 ?CalculateNineSlice@ui_native@@
void CalculateNineSlice(const u32& flags, float unknown4, float unknown5, float unknown6,
    const Vector4& us, const Vector4& vs, u32 sourceWidth, u32 sourceHeight,
    const Vector2& leftRight, const Vector2& topBottom,
    TextureCoordinates& coordinates, TextureBorders& borders) {
    coordinates.first = us;
    coordinates.second = vs;
    Normalize(coordinates.first, sourceWidth);
    Normalize(coordinates.second, sourceHeight);
    if (flags & 0x200) {
        std::swap(coordinates.first.x, coordinates.first.w);
        std::swap(coordinates.first.y, coordinates.first.z);
    }
    if (flags & 0x400) {
        std::swap(coordinates.second.x, coordinates.second.w);
        std::swap(coordinates.second.y, coordinates.second.z);
    }
    const float inverseY = 1.f / unknown6;
    const float inverseX = 1.f / unknown5;
    borders.first = topBottom;
    Scale(borders.first, inverseY);
    borders.second = leftRight;
    Scale(borders.second, inverseX);
    Scale(borders.second, unknown4);
}

} // namespace ui_native
