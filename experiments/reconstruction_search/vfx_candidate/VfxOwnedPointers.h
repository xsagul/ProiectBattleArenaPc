// Candidate runtime ownership; serialized tags stay in metadata.
#pragma once
#include "C:/Users/Sorin/Desktop/ProiectBattleArenaPc/client-src/src/Meta.h"
#include "C:/Users/Sorin/Desktop/ProiectBattleArenaPc/client-src/src/gen/ReflectedBuffers.h"
struct FlexValueVector3;
struct VfxProbabilityTableData;
template<class T> struct VfxOwnedPointer {
    T* value = nullptr;
    ~VfxOwnedPointer() { delete value; }
};
template<> struct VfxOwnedPointer<FlexValueVector3> {
    FlexValueVector3* value = nullptr;
    ~VfxOwnedPointer(); // body compiled separately, native helper 0xa64b00
};
struct VfxProbabilityOwners {
    VfxOwnedPointer<VfxProbabilityTableData> probabilityTables[3];
    ~VfxProbabilityOwners(); // defaulted separately, native helper 0xa64c90
};
struct VfxRawAllocation {
    void* data = nullptr;
    ~VfxRawAllocation() { ::operator delete(data); }
};
static_assert(sizeof(VfxOwnedPointer<FlexValueVector3>) == 4, "native pointer storage");
static_assert(sizeof(VfxProbabilityOwners) == 12, "three native owned pointers");
