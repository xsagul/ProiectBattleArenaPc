// Isolated candidate definitions, not included by the production pipeline.
#pragma once
#include "VfxOwnedPointers.h"
#include <cstddef>
struct FlexTypeFloat { u32 mFlexID = 0; float mValue = 0; };
static_assert(sizeof(FlexTypeFloat) == 8, "metadata");
struct VfxProbabilityTableData {
    ReflectedBuffer<float> keyTimes; // +0x0
    ReflectedBuffer<float> keyValues; // +0xc
    float singleValue = 1.0f; // +0x18
    u16 unknown1c = 1;
    u8 unknown1e[2];
};
static_assert(sizeof(VfxProbabilityTableData) == 32, "native size");
static_assert(offsetof(VfxProbabilityTableData, keyTimes) == 0, "metadata offset");
static_assert(offsetof(VfxProbabilityTableData, keyValues) == 12, "metadata offset");
static_assert(offsetof(VfxProbabilityTableData, singleValue) == 24, "metadata offset");
struct VfxAnimatedVector3fVariableData {
    VfxProbabilityOwners probabilityTables; // +0x0
    ReflectedBuffer<float> times; // +0xc
    ReflectedBuffer<Vector3> values; // +0x18
    u8 unknown24 = 0;
    u8 unknown25;
    u16 unknown26 = 0;
    u32 unknown28 = 0;
    u32 unknown2c = 0xffffffff;
    u8 unknown30[12];
    VfxRawAllocation unknown3c; // native cleanup frees this pointer
};
static_assert(sizeof(VfxAnimatedVector3fVariableData) == 64, "native size");
static_assert(offsetof(VfxAnimatedVector3fVariableData, probabilityTables) == 0, "metadata offset");
static_assert(offsetof(VfxAnimatedVector3fVariableData, times) == 12, "metadata offset");
static_assert(offsetof(VfxAnimatedVector3fVariableData, values) == 24, "metadata offset");
struct ValueVector3 {
    Vector3 constantValue = {}; // +0x0
    VfxOwnedPointer<VfxAnimatedVector3fVariableData> dynamics; // +0xc
};
static_assert(sizeof(ValueVector3) == 16, "native size");
static_assert(offsetof(ValueVector3, constantValue) == 0, "metadata offset");
static_assert(offsetof(ValueVector3, dynamics) == 12, "metadata offset");
struct FlexValueVector3 {
    u32 mFlexID = 0; // +0x0
    ::ValueVector3 mValue; // +0x4
};
static_assert(sizeof(FlexValueVector3) == 20, "native size");
static_assert(offsetof(FlexValueVector3, mFlexID) == 0, "metadata offset");
static_assert(offsetof(FlexValueVector3, mValue) == 4, "metadata offset");
struct VfxFlexShapeDefinitionData {
    float ScaleBirthTranslationByBoundObjectSize = 0.0f; // +0x0
    float scaleBirthScaleByBoundObjectSize = 0.0f; // +0x4
    float scaleBirthScaleByBoundObjectHeight = 0.0f; // +0x8
    float scaleBirthScaleByBoundObjectRadius = 0.0f; // +0xc
    float scaleEmitOffsetByBoundObjectSize = 0.0f; // +0x10
    float scaleEmitOffsetByBoundObjectHeight = 0.0f; // +0x14
    float scaleEmitOffsetByBoundObjectRadius = 0.0f; // +0x18
    VfxOwnedPointer<FlexTypeFloat> flexScaleEmitOffset; // +0x1c
    VfxOwnedPointer<FlexValueVector3> flexBirthTranslation; // +0x20
};
static_assert(sizeof(VfxFlexShapeDefinitionData) == 36, "native size");
static_assert(offsetof(VfxFlexShapeDefinitionData, ScaleBirthTranslationByBoundObjectSize) == 0, "metadata offset");
static_assert(offsetof(VfxFlexShapeDefinitionData, scaleBirthScaleByBoundObjectSize) == 4, "metadata offset");
static_assert(offsetof(VfxFlexShapeDefinitionData, scaleBirthScaleByBoundObjectHeight) == 8, "metadata offset");
static_assert(offsetof(VfxFlexShapeDefinitionData, scaleBirthScaleByBoundObjectRadius) == 12, "metadata offset");
static_assert(offsetof(VfxFlexShapeDefinitionData, scaleEmitOffsetByBoundObjectSize) == 16, "metadata offset");
static_assert(offsetof(VfxFlexShapeDefinitionData, scaleEmitOffsetByBoundObjectHeight) == 20, "metadata offset");
static_assert(offsetof(VfxFlexShapeDefinitionData, scaleEmitOffsetByBoundObjectRadius) == 24, "metadata offset");
static_assert(offsetof(VfxFlexShapeDefinitionData, flexScaleEmitOffset) == 28, "metadata offset");
static_assert(offsetof(VfxFlexShapeDefinitionData, flexBirthTranslation) == 32, "metadata offset");
static_assert(offsetof(VfxAnimatedVector3fVariableData, unknown3c) == 60, "cleanup pointer");
