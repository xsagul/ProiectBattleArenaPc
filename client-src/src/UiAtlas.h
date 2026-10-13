// Native UI texture ABI recovered from the 13.3 client.
// Keep this complete native view separate from the generator's incomplete
// BinObject/AtlasDataBase view until that hierarchy is migrated together.
#pragma once
#include "Meta.h"
#include <intrin.h>
#include <cstddef>

namespace ui_native {

// External implementation at aaa4c0; only the reference-count field is known.
struct AssetReference {
    u8 unknown00[32];
    volatile long refs;
    u32 Release();
};

struct TextureReference {
    AssetReference* value = nullptr;
    ~TextureReference() { if (value) value->Release(); }
    TextureReference& operator=(const TextureReference& other) {
        if (other.value) _InterlockedIncrement(&other.value->refs);
        if (value) value->Release();
        value = other.value;
        return *this;
    }
};

struct TextureManager {
    TextureReference FindTexture(const MetaString& name);
    TextureReference FindTexture(const char* name);
    // External implementation at ab2b90, not claimed as reconstructed.
    TextureReference FindTexture(u32 flags, const char* name);
};
extern TextureManager* g_TextureManager; // RVA 2527228

struct TextureCoordinates { Vector4 first, second; };
// The nine-slice calculator fills both; each three-slice calculator fills only the first.
struct TextureBorders { Vector2 first, second; };

// Native root table fb3474 contains only these two slots.
struct Object {
    virtual ~Object() {}
    virtual const MetaClass* GetClass() const = 0;
};

struct IUiTextureDataProvider : Object {
    virtual void PostLoad() = 0;
    // Nine stack words are demonstrated by ret 0x24. AtlasData9Slice proves
    // the float arguments, second coordinate vector and final border output.
    // Canonical names/cv qualifications remain unknown.
    virtual void GetTexture(const u32& flags, u32 width, u32 height,
        float unknown4, float unknown5, float unknown6,
        TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) = 0;
    virtual u8 GetMode() const = 0; // Observed AL values: AtlasData 0, 3SliceH 1, 3SliceV 2, 9Slice 3.
};

struct AtlasDataBase : IUiTextureDataProvider {
    const MetaClass* GetClass() const override;
    MetaString mTextureName;
    u32 mTextureSourceResolutionWidth = 0;
    u32 mTextureSourceResolutionHeight = 0;
    TextureReference reference;
    void PostLoad() override {
        reference = g_TextureManager->FindTexture(mTextureName);
    }
};

// Static destruction in metadata and its owner's destructor demonstrates the
// final source form, despite the generic metadata classifier calling it nonpoly.
struct AtlasData final : AtlasDataBase {
    const MetaClass* GetClass() const override;
    Vector4 mTextureUV{0, 0, 1, 1};
    void GetTexture(const u32& flags, u32 width, u32 height,
        float unknown4, float unknown5, float unknown6,
        TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) override;
    u8 GetMode() const override { return 0; }
};

struct AtlasData3SliceH final : AtlasDataBase {
    AtlasData3SliceH();
    const MetaClass* GetClass() const override;
    Vector4 TextureUs{0, 0.25f, 0.75f, 1};
    Vector2 TextureVs{0, 1};
    Vector2 LeftRightWidths{0.25f, 0.25f};
    void GetTexture(const u32& flags, u32 width, u32 height,
        float unknown4, float unknown5, float unknown6,
        TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) override;
    u8 GetMode() const override { return 1; }
};

struct AtlasData3SliceV final : AtlasDataBase {
    AtlasData3SliceV();
    const MetaClass* GetClass() const override;
    Vector2 TextureUs{0, 1};
    Vector4 TextureVs{0, 0.25f, 0.75f, 1};
    Vector2 TopBottomHeights{0.25f, 0.25f};
    void GetTexture(const u32& flags, u32 width, u32 height,
        float unknown4, float unknown5, float unknown6,
        TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) override;
    u8 GetMode() const override { return 2; }
};

struct AtlasData9Slice final : AtlasDataBase {
    AtlasData9Slice();
    const MetaClass* GetClass() const override;
    Vector4 TextureUs{0, 0.25f, 0.75f, 1};
    Vector4 TextureVs{0, 0.25f, 0.75f, 1};
    Vector2 TopBottomHeights{0.25f, 0.25f};
    Vector2 LeftRightWidths{0.25f, 0.25f};
    void GetTexture(const u32& flags, u32 width, u32 height,
        float unknown4, float unknown5, float unknown6,
        TextureReference& texture, TextureCoordinates& coordinates, TextureBorders& borders) override;
    u8 GetMode() const override { return 3; }
};

void CropAtlasUV(const Vector4& source, u32 width, u32 height, Vector4& uv);
void CalculateThreeSliceH(const u32& flags, float unknown4, float unknown5,
    const Vector4& us, const Vector2& vs, u32 sourceWidth, u32 sourceHeight,
    const Vector2& leftRight, TextureCoordinates& coordinates, TextureBorders& borders);
void CalculateThreeSliceV(const u32& flags, float unknown6,
    const Vector2& us, const Vector4& vs, u32 sourceWidth, u32 sourceHeight,
    const Vector2& topBottom, TextureCoordinates& coordinates, TextureBorders& borders);
void CalculateNineSlice(const u32& flags, float unknown4, float unknown5, float unknown6,
    const Vector4& us, const Vector4& vs, u32 sourceWidth, u32 sourceHeight,
    const Vector2& leftRight, const Vector2& topBottom,
    TextureCoordinates& coordinates, TextureBorders& borders);

static_assert(sizeof(TextureReference) == 4);
static_assert(sizeof(Object) == 4);
static_assert(sizeof(IUiTextureDataProvider) == 4);
static_assert(sizeof(AtlasDataBase) == 28);
static_assert(sizeof(AtlasData) == 44);
static_assert(sizeof(AtlasData3SliceH) == 60);
static_assert(sizeof(AtlasData3SliceV) == 60);
static_assert(sizeof(AtlasData9Slice) == 76);
static_assert(offsetof(AssetReference, refs) == 32);
static_assert(offsetof(AtlasDataBase, reference) == 24);
static_assert(offsetof(AtlasData, mTextureUV) == 28);

} // namespace ui_native
