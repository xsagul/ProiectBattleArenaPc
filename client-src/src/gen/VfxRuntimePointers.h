// Native VFX ownership, separately proved from serialized list tags.
#pragma once
#include "ReflectedBuffers.h"
#include "ReflectedElementDefaults.h"
struct FlexValueVector3;
struct VfxProbabilityTableData;
struct VfxAnimatedVector3fVariableData;
template<class T> struct VfxOwnedPointer {
    T* value = nullptr;
    ~VfxOwnedPointer() { delete value; }
};
template<> struct VfxOwnedPointer<FlexValueVector3> {
    FlexValueVector3* value = nullptr;
    ~VfxOwnedPointer();
};
struct VfxProbabilityOwners {
    VfxOwnedPointer<VfxProbabilityTableData> probabilityTables[3];
    ~VfxProbabilityOwners();
};
struct VfxRawAllocation {
    void* data = nullptr;
    ~VfxRawAllocation() { ::operator delete(data); }
};
struct VfxConstantVector3 : Vector3 {
    VfxConstantVector3() { x=0; y=0; z=0; }
    VfxConstantVector3(const Vector3& value) : Vector3(value) {}
};
static_assert(sizeof(VfxConstantVector3)==12,"native scalar vector");
VfxAnimatedVector3fVariableData* __fastcall VfxDynamicAllocate(void* context);
