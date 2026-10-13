// flags: -O2 -std:c++17 -GR-
#include "UiAtlas.h"
#include "gen/MetaClasses.h"

// match: adef20 ??0AtlasData@ui_native@@QAE@XZ
// same: 109610 ??_GObject@ui_native@@UAEPAXI@Z
// match: adb910 ??$MetaConstruct@UAtlasData@@@@YAXPAX@Z
// match: adb8f0 ??$MetaCreate@UAtlasData@@@@YAPAXXZ
// match: adc5a0 ??$MetaDestruct@UAtlasData@@@@YAXPAX@Z
// match: adc650 ??$MetaDestroy@UAtlasData@@@@YAXPAX@Z
// match: adc5d0 ??$MetaVirtual2@UAtlasData@@@@YAXPAX@Z
// match: aeef30 ?PostLoad@AtlasDataBase@ui_native@@UAEXXZ
// match: ae2570 ??_GAtlasData@ui_native@@UAEPAXI@Z
// match: ae25b0 ??_GAtlasDataBase@ui_native@@UAEPAXI@Z
// same: aed930 ?GetClass@AtlasData@ui_native@@UBEPBUMetaClass@@XZ
// same: aed940 ?GetClass@AtlasDataBase@ui_native@@UBEPBUMetaClass@@XZ
// same: e9b30 ?GetMode@AtlasData@ui_native@@UBEEXZ
// match: adb970 ??$MetaCreate@UAtlasData3SliceH@@@@YAPAXXZ
// match: adb990 ??$MetaConstruct@UAtlasData3SliceH@@@@YAXPAX@Z
// match: adc620 ??$MetaDestroy@UAtlasData3SliceH@@@@YAXPAX@Z
// same: adc5a0 ??$MetaDestruct@UAtlasData3SliceH@@@@YAXPAX@Z
// same: adc5d0 ??$MetaVirtual2@UAtlasData3SliceH@@@@YAXPAX@Z
// match: ae24f0 ??_GAtlasData3SliceH@ui_native@@UAEPAXI@Z
// match: aed900 ?GetClass@AtlasData3SliceH@ui_native@@UBEPBUMetaClass@@XZ
// match: adb9a0 ??$MetaCreate@UAtlasData3SliceV@@@@YAPAXXZ
// match: adb9c0 ??$MetaConstruct@UAtlasData3SliceV@@@@YAXPAX@Z
// same: adc620 ??$MetaDestroy@UAtlasData3SliceV@@@@YAXPAX@Z
// same: adc5a0 ??$MetaDestruct@UAtlasData3SliceV@@@@YAXPAX@Z
// same: adc5d0 ??$MetaVirtual2@UAtlasData3SliceV@@@@YAXPAX@Z
// same: ae24f0 ??_GAtlasData3SliceV@ui_native@@UAEPAXI@Z
// match: aed910 ?GetClass@AtlasData3SliceV@ui_native@@UBEPBUMetaClass@@XZ
// match: adb9d0 ??$MetaCreate@UAtlasData9Slice@@@@YAPAXXZ
// match: adba40 ??$MetaConstruct@UAtlasData9Slice@@@@YAXPAX@Z
// match: adc570 ??$MetaDestroy@UAtlasData9Slice@@@@YAXPAX@Z
// same: adc5a0 ??$MetaDestruct@UAtlasData9Slice@@@@YAXPAX@Z
// same: adc5d0 ??$MetaVirtual2@UAtlasData9Slice@@@@YAXPAX@Z
// match: ae2530 ??_GAtlasData9Slice@ui_native@@UAEPAXI@Z
// match: aed920 ?GetClass@AtlasData9Slice@ui_native@@UBEPBUMetaClass@@XZ

// The generated metadata's forward-declared AtlasData tag retains its callback
// symbols. Their bodies use the native layout, without redefining BinClasses.
template<> void* MetaCreate<AtlasData>() { return new ui_native::AtlasData; }
template<> void MetaConstruct<AtlasData>(void* p) { new(p) ui_native::AtlasData; }
template<> void MetaDestruct<AtlasData>(void* p) { static_cast<ui_native::AtlasData*>(p)->~AtlasData(); }
template<> void MetaDestroy<AtlasData>(void* p) { delete static_cast<ui_native::AtlasData*>(p); }
template<> void MetaVirtual2<AtlasData>(void* p) { static_cast<ui_native::AtlasData*>(p)->PostLoad(); }

const MetaClass* ui_native::AtlasData::GetClass() const { return &AtlasData_Meta; }
const MetaClass* ui_native::AtlasDataBase::GetClass() const { return &AtlasDataBase_Meta; }

template<> void* MetaCreate<AtlasData9Slice>() { return new ui_native::AtlasData9Slice; }
template<> void MetaConstruct<AtlasData9Slice>(void* p) { new(p) ui_native::AtlasData9Slice; }
template<> void MetaDestruct<AtlasData9Slice>(void* p) { static_cast<ui_native::AtlasData9Slice*>(p)->~AtlasData9Slice(); }
template<> void MetaDestroy<AtlasData9Slice>(void* p) { delete static_cast<ui_native::AtlasData9Slice*>(p); }
template<> void MetaVirtual2<AtlasData9Slice>(void* p) { static_cast<ui_native::AtlasData9Slice*>(p)->PostLoad(); }
const MetaClass* ui_native::AtlasData9Slice::GetClass() const { return &AtlasData9Slice_Meta; }

template<> void* MetaCreate<AtlasData3SliceH>() { return new ui_native::AtlasData3SliceH; }
template<> void MetaConstruct<AtlasData3SliceH>(void* p) { new(p) ui_native::AtlasData3SliceH; }
template<> void MetaDestruct<AtlasData3SliceH>(void* p) { static_cast<ui_native::AtlasData3SliceH*>(p)->~AtlasData3SliceH(); }
template<> void MetaDestroy<AtlasData3SliceH>(void* p) { delete static_cast<ui_native::AtlasData3SliceH*>(p); }
template<> void MetaVirtual2<AtlasData3SliceH>(void* p) { static_cast<ui_native::AtlasData3SliceH*>(p)->PostLoad(); }
const MetaClass* ui_native::AtlasData3SliceH::GetClass() const { return &AtlasData3SliceH_Meta; }

template<> void* MetaCreate<AtlasData3SliceV>() { return new ui_native::AtlasData3SliceV; }
template<> void MetaConstruct<AtlasData3SliceV>(void* p) { new(p) ui_native::AtlasData3SliceV; }
template<> void MetaDestruct<AtlasData3SliceV>(void* p) { static_cast<ui_native::AtlasData3SliceV*>(p)->~AtlasData3SliceV(); }
template<> void MetaDestroy<AtlasData3SliceV>(void* p) { delete static_cast<ui_native::AtlasData3SliceV*>(p); }
template<> void MetaVirtual2<AtlasData3SliceV>(void* p) { static_cast<ui_native::AtlasData3SliceV*>(p)->PostLoad(); }
const MetaClass* ui_native::AtlasData3SliceV::GetClass() const { return &AtlasData3SliceV_Meta; }
