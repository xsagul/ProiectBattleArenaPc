#include "C:/Users/Sorin/Desktop/ProiectBattleArenaPc/client-src/src/gen/ReflectedBuffers.h"
struct ProbabilityTableSeed {
    ReflectedBuffer<float> keyTimes;
    ReflectedBuffer<float> keyValues;
    float singleValue;
    u16 flags;
    u8 padding[2];
};
static_assert(sizeof(ProbabilityTableSeed)==32,"reflected pointed object size");
template<class T> struct OwnedPointerSeed {
    T* value;
    ~OwnedPointerSeed() { delete value; }
};
struct ProbabilityOwnersSeed {
    OwnedPointerSeed<ProbabilityTableSeed> tables[1];
    ~ProbabilityOwnersSeed();
};
ProbabilityOwnersSeed::~ProbabilityOwnersSeed() = default;
