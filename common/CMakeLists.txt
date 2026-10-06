# Code shared by the client and the server: League's data formats, the network protocol, deterministic time and random.
add_library(ba_common STATIC
  src/Hash.cpp
  src/Wad.cpp
  src/PropertyBin.cpp
  src/HashNames.cpp
  src/Texture.cpp
  src/TexturePixels.cpp
  src/Model.cpp
  src/MapGeometry.cpp
  src/NavGrid.cpp
  src/MapObjects.cpp
  src/MapGame.cpp
  src/CharacterData.cpp
  src/SpellData.cpp
  src/ItemData.cpp
  src/StringTable.cpp
  src/GameData.cpp
  src/ShaderCache.cpp
)
target_include_directories(ba_common PUBLIC include)
target_link_libraries(ba_common PUBLIC xxhash zstd)
