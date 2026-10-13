// flags: -O2 -std:c++17 -GR-
#include "UiAtlas.h"

namespace ui_native {

// same: ab2ac0 ?FindTexture@TextureManager@ui_native@@QAE?AUTextureReference@2@ABUMetaString@@@Z
TextureReference TextureManager::FindTexture(const MetaString& name) {
    return FindTexture(0, name.data);
}

// same: ab2ae0 ?FindTexture@TextureManager@ui_native@@QAE?AUTextureReference@2@PBD@Z
TextureReference TextureManager::FindTexture(const char* name) {
    return FindTexture(0, name);
}

} // namespace ui_native
