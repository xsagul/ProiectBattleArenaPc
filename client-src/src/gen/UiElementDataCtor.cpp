// match: adfd20 ??0UiElementData@@QAE@XZ
// match: ae3530 ??_GUiElementIData@@UAEPAXI@Z
// match: ae2b30 ??_GUiElementData@@UAEPAXI@Z
// same: aed850 ?GetClass@UiElementIData@@UBEPBUMetaClass@@XZ
// same: aed7d0 ?GetClass@UiElementData@@UBEPBUMetaClass@@XZ
#include "BinClasses.h"
UiElementData::UiElementData() = default;
const MetaClass* UiElementIData::GetClass() const { return &UiElementIData_Meta; }
const MetaClass* UiElementData::GetClass() const { return &UiElementData_Meta; }
