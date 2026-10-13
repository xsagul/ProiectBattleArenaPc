// match: adfc40 ??0UiElementAsset@@QAE@XZ
// same: aedac0 ?GetClass@UiElementAsset@@UBEPBUMetaClass@@XZ
#include "BinClasses.h"
UiElementAsset::UiElementAsset() {
    unknown84=false;
    unknown98=g_UiAssetDefaultVector;
    unknowna8=g_UiAssetDefaultLow;
    unknownac=g_UiAssetDefaultHigh;
    unknownb0=g_UiAssetDefaultLow;
    unknownb4=g_UiAssetDefaultHigh;
}
const MetaClass* UiElementAsset::GetClass() const { return &UiElementAsset_Meta; }
