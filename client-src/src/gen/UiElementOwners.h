// UI native owners; serialized pointer/link tags are described separately.
#pragma once
#include "MetaClasses.h"
#include <cfloat>
extern const Vector4 g_UiDefaultRect;
extern const float g_UiAnchorX, g_UiAnchorY;
template<class T> struct UiDataOwner {
    T* value;
    UiDataOwner(T* p = nullptr) : value(p) {}
    ~UiDataOwner() { delete value; }
};
struct UiSceneLink {
    u32 value = 0;
    ~UiSceneLink() { value = 0; }
};
struct UiAllocation12 { u32 words[3]; };
struct UiAllocationOwner12 {
    UiAllocation12* value = nullptr;
    ~UiAllocationOwner12() { ::operator delete(value, sizeof(UiAllocation12)); }
};
// External ABI, inspected at aaa4c0; its complete body remains unreconstructed.
struct UiAssetReference { u32 Release(); };
struct UiNullableAssetReference {
    UiAssetReference* value = nullptr;
    ~UiNullableAssetReference() { if(value) value->Release(); }
};
extern const Vector4 g_UiAssetDefaultVector;
extern const float g_UiAssetDefaultLow, g_UiAssetDefaultHigh;
static_assert(sizeof(UiAllocation12)==12);
static_assert(sizeof(UiAllocationOwner12)==4);
static_assert(sizeof(UiNullableAssetReference)==4);
