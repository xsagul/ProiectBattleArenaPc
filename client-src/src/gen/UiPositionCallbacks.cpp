// same: adc0b0 ??$MetaCreate@UUiPositionRect@@@@YAPAXXZ
// same: adc120 ??$MetaConstruct@UUiPositionRect@@@@YAXPAX@Z
// match: add220 ??$MetaCreate@UAnchorSingle@@@@YAPAXXZ
// same: f1270 ??$MetaDestroy@UUiPositionRect@@@@YAXPAX@Z
// same: f12a0 ??$MetaDestruct@UUiPositionRect@@@@YAXPAX@Z
// same: f1270 ??$MetaDestroy@UAnchorSingle@@@@YAXPAX@Z
// same: f12a0 ??$MetaDestruct@UAnchorSingle@@@@YAXPAX@Z
#include "BinClasses.h"
template<> void* MetaCreate<UiPositionRect>() { return new UiPositionRect; }
template<> void MetaConstruct<UiPositionRect>(void* p) { new(p) UiPositionRect; }
template<> void* MetaCreate<AnchorSingle>() { return new AnchorSingle; }
template<> void MetaDestroy<UiPositionRect>(void* p) { delete static_cast<UiPositionRect*>(p); }
template<> void MetaDestruct<UiPositionRect>(void* p) { static_cast<UiPositionRect*>(p)->~UiPositionRect(); }
template<> void MetaDestroy<AnchorSingle>(void* p) { delete static_cast<AnchorSingle*>(p); }
template<> void MetaDestruct<AnchorSingle>(void* p) { static_cast<AnchorSingle*>(p)->~AnchorSingle(); }
