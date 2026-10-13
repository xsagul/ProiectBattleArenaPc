// match: ae0ac0 ??0UiPositionRect@@QAE@XZ
// match: adb850 ??$MetaConstruct@UAnchorSingle@@@@YAXPAX@Z
// same: 109480 ??_GAnchorSingle@@UAEPAXI@Z
// match: ae38e0 ??_GUiPositionRect@@UAEPAXI@Z
// same: aed8f0 ?GetClass@AnchorSingle@@UBEPBUMetaClass@@XZ
// same: aedbd0 ?GetClass@UiPositionRect@@UBEPBUMetaClass@@XZ
#include "BinClasses.h"
UiPositionRect::UiPositionRect() = default;
template<> void MetaConstruct<AnchorSingle>(void* p) { new(p) AnchorSingle; }
const MetaClass* AnchorSingle::GetClass() const { return &AnchorSingle_Meta; }
const MetaClass* UiPositionRect::GetClass() const { return &UiPositionRect_Meta; }
