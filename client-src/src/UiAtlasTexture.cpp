// flags: -O2 -std:c++17 -GR-
#include "UiAtlas.h"
#include <utility>

namespace ui_native {

// match: ae6850 ?GetTexture@AtlasData@ui_native@@
void AtlasData::GetTexture(const u32& flags, u32 width, u32 height,
    float unknown4, float unknown5, float unknown6,
    TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) {
    Vector4& uv = coordinates.first;
    texture = reference;
    if (mTextureSourceResolutionWidth > 0 && mTextureSourceResolutionHeight > 0) {
        uv = mTextureUV;
        if (flags & 0x200000)
            CropAtlasUV(mTextureUV, width, height, uv);
        uv.x /= mTextureSourceResolutionWidth;
        uv.y /= mTextureSourceResolutionHeight;
        uv.z /= mTextureSourceResolutionWidth;
        uv.w /= mTextureSourceResolutionHeight;
        if (flags & 0x200) std::swap(uv.x, uv.z);
        if (flags & 0x400) std::swap(uv.y, uv.w);
    } else {
        uv = mTextureUV;
    }
}

// match: ae6700 ?GetTexture@AtlasData3SliceH@ui_native@@
void AtlasData3SliceH::GetTexture(const u32& flags, u32 width, u32 height,
    float unknown4, float unknown5, float unknown6,
    TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) {
    texture = reference;
    CalculateThreeSliceH(flags, unknown4, unknown5,
        TextureUs, TextureVs, mTextureSourceResolutionWidth, mTextureSourceResolutionHeight,
        LeftRightWidths, coordinates, borders);
}

// match: ae6770 ?GetTexture@AtlasData3SliceV@ui_native@@
void AtlasData3SliceV::GetTexture(const u32& flags, u32 width, u32 height,
    float unknown4, float unknown5, float unknown6,
    TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) {
    texture = reference;
    CalculateThreeSliceV(flags, unknown6,
        TextureUs, TextureVs, mTextureSourceResolutionWidth, mTextureSourceResolutionHeight,
        TopBottomHeights, coordinates, borders);
}

// match: ae67d0 ?GetTexture@AtlasData9Slice@ui_native@@
void AtlasData9Slice::GetTexture(const u32& flags, u32 width, u32 height,
    float unknown4, float unknown5, float unknown6,
    TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) {
    texture = reference;
    CalculateNineSlice(flags, unknown4, unknown5, unknown6,
        TextureUs, TextureVs, mTextureSourceResolutionWidth, mTextureSourceResolutionHeight,
        LeftRightWidths, TopBottomHeights, coordinates, borders);
}

} // namespace ui_native
