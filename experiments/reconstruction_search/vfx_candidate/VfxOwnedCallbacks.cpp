#include "VfxOwnedClasses.h"
template<> void MetaDestroy<VfxProbabilityTableData>(void* p) { delete static_cast<VfxProbabilityTableData*>(p); }
template<> void MetaDestruct<VfxProbabilityTableData>(void* p) { static_cast<VfxProbabilityTableData*>(p)->~VfxProbabilityTableData(); }
template<> void MetaDestroy<VfxAnimatedVector3fVariableData>(void* p) { delete static_cast<VfxAnimatedVector3fVariableData*>(p); }
template<> void MetaDestruct<VfxAnimatedVector3fVariableData>(void* p) { static_cast<VfxAnimatedVector3fVariableData*>(p)->~VfxAnimatedVector3fVariableData(); }
template<> void MetaDestroy<ValueVector3>(void* p) { delete static_cast<ValueVector3*>(p); }
template<> void MetaDestruct<ValueVector3>(void* p) { static_cast<ValueVector3*>(p)->~ValueVector3(); }
template<> void MetaDestroy<FlexValueVector3>(void* p) { delete static_cast<FlexValueVector3*>(p); }
template<> void MetaDestruct<FlexValueVector3>(void* p) { static_cast<FlexValueVector3*>(p)->~FlexValueVector3(); }
template<> void MetaDestroy<VfxFlexShapeDefinitionData>(void* p) { delete static_cast<VfxFlexShapeDefinitionData*>(p); }
template<> void MetaDestruct<VfxFlexShapeDefinitionData>(void* p) { static_cast<VfxFlexShapeDefinitionData*>(p)->~VfxFlexShapeDefinitionData(); }
