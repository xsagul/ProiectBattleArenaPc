// match: a57d10 ??$MetaCreate@UVfxProbabilityTableData@@@@YAPAXXZ
// match: a58af0 ??$MetaConstruct@UVfxProbabilityTableData@@@@YAXPAX@Z
// match: a58140 ??$MetaDestroy@UVfxProbabilityTableData@@@@YAXPAX@Z
// match: a58180 ??$MetaDestruct@UVfxProbabilityTableData@@@@YAXPAX@Z
// match: a59340 ??$MetaCreate@UVfxAnimatedVector3fVariableData@@@@YAPAXXZ
// match: a59470 ??$MetaConstruct@UVfxAnimatedVector3fVariableData@@@@YAXPAX@Z
// match: a585f0 ??$MetaDestroy@UVfxAnimatedVector3fVariableData@@@@YAXPAX@Z
// match: a58640 ??$MetaDestruct@UVfxAnimatedVector3fVariableData@@@@YAXPAX@Z
// same: 1db9e0 ??$MetaCreate@UValueVector3@@@@YAPAXXZ
// same: 1dba10 ??$MetaConstruct@UValueVector3@@@@YAXPAX@Z
// match: a58930 ??$MetaDestroy@UValueVector3@@@@YAXPAX@Z
// match: a57cc0 ??$MetaDestruct@UValueVector3@@@@YAXPAX@Z
// match: a58330 ??$MetaCreate@UFlexValueVector3@@@@YAPAXXZ
// match: a583e0 ??$MetaConstruct@UFlexValueVector3@@@@YAXPAX@Z
// match: a57f40 ??$MetaDestroy@UFlexValueVector3@@@@YAXPAX@Z
// match: a57fa0 ??$MetaDestruct@UFlexValueVector3@@@@YAXPAX@Z
// match: 24e360 ??$MetaCreate@UVfxFlexShapeDefinitionData@@@@YAPAXXZ
// same: 24e3b0 ??$MetaConstruct@UVfxFlexShapeDefinitionData@@@@YAXPAX@Z
// match: a57e70 ??$MetaDestroy@UVfxFlexShapeDefinitionData@@@@YAXPAX@Z
// match: a57ea0 ??$MetaDestruct@UVfxFlexShapeDefinitionData@@@@YAXPAX@Z
// same: a58d20 ??$MetaCreate@UVfxFieldAccelerationDefinitionData@@@@YAPAXXZ
// same: a58d60 ??$MetaConstruct@UVfxFieldAccelerationDefinitionData@@@@YAXPAX@Z
// same: a57f40 ??$MetaDestroy@UVfxFieldAccelerationDefinitionData@@@@YAXPAX@Z
// same: a57fa0 ??$MetaDestruct@UVfxFieldAccelerationDefinitionData@@@@YAXPAX@Z
// same: a58dd0 ??$MetaCreate@UVfxFieldOrbitalDefinitionData@@@@YAPAXXZ
// same: a58e10 ??$MetaConstruct@UVfxFieldOrbitalDefinitionData@@@@YAXPAX@Z
// same: a57f40 ??$MetaDestroy@UVfxFieldOrbitalDefinitionData@@@@YAXPAX@Z
// same: a57fa0 ??$MetaDestruct@UVfxFieldOrbitalDefinitionData@@@@YAXPAX@Z
// match: a58f20 ??$MetaCreate@UVfxParentInheritanceParams@@@@YAPAXXZ
// match: a58f60 ??$MetaConstruct@UVfxParentInheritanceParams@@@@YAXPAX@Z
// same: a57f40 ??$MetaDestroy@UVfxParentInheritanceParams@@@@YAXPAX@Z
// same: a57fa0 ??$MetaDestruct@UVfxParentInheritanceParams@@@@YAXPAX@Z
// match: a59260 ??$MetaCreate@UVfxTrailDefinitionData@@@@YAPAXXZ
// match: a592b0 ??$MetaConstruct@UVfxTrailDefinitionData@@@@YAXPAX@Z
// match: a57c60 ??$MetaDestroy@UVfxTrailDefinitionData@@@@YAXPAX@Z
// same: a57cc0 ??$MetaDestruct@UVfxTrailDefinitionData@@@@YAXPAX@Z
// match: a581b0 ??$MetaVirtual2@UVfxProbabilityTableData@@@@YAXPAX@Z
#include "BinClasses.h"
extern const float g_VfxZeroUpper,g_VfxZeroLower,g_VfxOneUpper,g_VfxOneLower;
template<> void* MetaCreate<VfxProbabilityTableData>() { return new VfxProbabilityTableData; }
template<> void MetaConstruct<VfxProbabilityTableData>(void* p) { new(p) VfxProbabilityTableData; }
template<> void MetaDestroy<VfxProbabilityTableData>(void* p) { delete static_cast<VfxProbabilityTableData*>(p); }
template<> void MetaDestruct<VfxProbabilityTableData>(void* p) { static_cast<VfxProbabilityTableData*>(p)->~VfxProbabilityTableData(); }
template<> void* MetaCreate<VfxAnimatedVector3fVariableData>() { return VfxDynamicAllocate(nullptr); }
template<> void MetaConstruct<VfxAnimatedVector3fVariableData>(void* p) { new(p) VfxAnimatedVector3fVariableData; }
template<> void MetaDestroy<VfxAnimatedVector3fVariableData>(void* p) { delete static_cast<VfxAnimatedVector3fVariableData*>(p); }
template<> void MetaDestruct<VfxAnimatedVector3fVariableData>(void* p) { static_cast<VfxAnimatedVector3fVariableData*>(p)->~VfxAnimatedVector3fVariableData(); }
template<> void* MetaCreate<ValueVector3>() { return new ValueVector3; }
template<> void MetaConstruct<ValueVector3>(void* p) { new(p) ValueVector3; }
template<> void MetaDestroy<ValueVector3>(void* p) { delete static_cast<ValueVector3*>(p); }
template<> void MetaDestruct<ValueVector3>(void* p) { static_cast<ValueVector3*>(p)->~ValueVector3(); }
template<> void* MetaCreate<FlexValueVector3>() { return new FlexValueVector3; }
template<> void MetaConstruct<FlexValueVector3>(void* p) { new(p) FlexValueVector3; }
template<> void MetaDestroy<FlexValueVector3>(void* p) { delete static_cast<FlexValueVector3*>(p); }
template<> void MetaDestruct<FlexValueVector3>(void* p) { static_cast<FlexValueVector3*>(p)->~FlexValueVector3(); }
template<> void* MetaCreate<VfxFlexShapeDefinitionData>() { return new VfxFlexShapeDefinitionData; }
template<> void MetaConstruct<VfxFlexShapeDefinitionData>(void* p) { new(p) VfxFlexShapeDefinitionData; }
template<> void MetaDestroy<VfxFlexShapeDefinitionData>(void* p) { delete static_cast<VfxFlexShapeDefinitionData*>(p); }
template<> void MetaDestruct<VfxFlexShapeDefinitionData>(void* p) { static_cast<VfxFlexShapeDefinitionData*>(p)->~VfxFlexShapeDefinitionData(); }
template<> void* MetaCreate<VfxFieldAccelerationDefinitionData>() { return new VfxFieldAccelerationDefinitionData; }
template<> void MetaConstruct<VfxFieldAccelerationDefinitionData>(void* p) { new(p) VfxFieldAccelerationDefinitionData; }
template<> void MetaDestroy<VfxFieldAccelerationDefinitionData>(void* p) { delete static_cast<VfxFieldAccelerationDefinitionData*>(p); }
template<> void MetaDestruct<VfxFieldAccelerationDefinitionData>(void* p) { static_cast<VfxFieldAccelerationDefinitionData*>(p)->~VfxFieldAccelerationDefinitionData(); }
template<> void* MetaCreate<VfxFieldOrbitalDefinitionData>() { return new VfxFieldOrbitalDefinitionData; }
template<> void MetaConstruct<VfxFieldOrbitalDefinitionData>(void* p) { new(p) VfxFieldOrbitalDefinitionData; }
template<> void MetaDestroy<VfxFieldOrbitalDefinitionData>(void* p) { delete static_cast<VfxFieldOrbitalDefinitionData*>(p); }
template<> void MetaDestruct<VfxFieldOrbitalDefinitionData>(void* p) { static_cast<VfxFieldOrbitalDefinitionData*>(p)->~VfxFieldOrbitalDefinitionData(); }
template<> void* MetaCreate<VfxParentInheritanceParams>() { return new VfxParentInheritanceParams; }
template<> void MetaConstruct<VfxParentInheritanceParams>(void* p) { new(p) VfxParentInheritanceParams; }
template<> void MetaDestroy<VfxParentInheritanceParams>(void* p) { delete static_cast<VfxParentInheritanceParams*>(p); }
template<> void MetaDestruct<VfxParentInheritanceParams>(void* p) { static_cast<VfxParentInheritanceParams*>(p)->~VfxParentInheritanceParams(); }
template<> void* MetaCreate<VfxTrailDefinitionData>() { return new VfxTrailDefinitionData; }
template<> void MetaConstruct<VfxTrailDefinitionData>(void* p) { new(p) VfxTrailDefinitionData; }
template<> void MetaDestroy<VfxTrailDefinitionData>(void* p) { delete static_cast<VfxTrailDefinitionData*>(p); }
template<> void MetaDestruct<VfxTrailDefinitionData>(void* p) { static_cast<VfxTrailDefinitionData*>(p)->~VfxTrailDefinitionData(); }
template<> void MetaVirtual2<VfxProbabilityTableData>(void* p) {
    auto v=static_cast<VfxProbabilityTableData*>(p);
    v->unknown1d=false;
    v->unknown1c=(v->keyTimes.count==0);
    if(v->keyTimes.count==2) {
        auto key=v->keyTimes.data;
        Vector2 keys{key[0],key[1]};
        if(keys.x<=g_VfxZeroUpper && keys.x>=g_VfxZeroLower &&
           keys.y<=g_VfxOneUpper && keys.y>=g_VfxOneLower) v->unknown1d=true;
    }
}
