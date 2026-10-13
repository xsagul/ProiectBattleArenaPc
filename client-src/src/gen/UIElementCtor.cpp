// match: adfb60 ??0UIElement@@QAE@XZ
// match: ae34f0 ??_GUIElementI@@UAEPAXI@Z
// same: aedb50 ?GetClass@UIElementI@@UBEPBUMetaClass@@XZ
// same: aed7b0 ?GetClass@UIElement@@UBEPBUMetaClass@@XZ
#include "BinClasses.h"
UIElement::UIElement() = default;
const MetaClass* UIElementI::GetClass() const { return &UIElementI_Meta; }
const MetaClass* UIElement::GetClass() const { return &UIElement_Meta; }
