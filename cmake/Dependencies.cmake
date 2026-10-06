# Third-party libraries, kept as source in third_party/ (downloaded from their official releases, checksums verified):
#   ENet 1.3.18  - the reliable-UDP library League's game protocol is built on
#   Lua 5.1.5    - the scripting language of League's spell and buff scripts (Building Blocks)
#   zstd 1.5.6   - the compression of .wad.client entries
#   xxHash 0.8.2 - xxh64, the hash of the paths inside .wad.client archives
set(TP ${CMAKE_SOURCE_DIR}/third_party)

# ---------------------------------------------------------------- zstd (decompression only: all the game needs)
file(GLOB ZSTD_SOURCES ${TP}/zstd-1.5.6/lib/common/*.c ${TP}/zstd-1.5.6/lib/decompress/*.c)
add_library(zstd STATIC ${ZSTD_SOURCES})
target_include_directories(zstd PUBLIC ${TP}/zstd-1.5.6/lib)
target_compile_definitions(zstd PRIVATE ZSTD_DISABLE_ASM ZSTD_MULTITHREAD=0)
if(MSVC)
  target_compile_options(zstd PRIVATE /W0)
else()
  target_compile_options(zstd PRIVATE -w)
endif()

# ---------------------------------------------------------------- xxHash (header only)
add_library(xxhash INTERFACE)
target_include_directories(xxhash INTERFACE ${TP}/xxHash-0.8.2)
target_compile_definitions(xxhash INTERFACE XXH_INLINE_ALL)

# ---------------------------------------------------------------- ENet
file(GLOB ENET_SOURCES ${TP}/enet-1.3.18/*.c)
add_library(enet STATIC ${ENET_SOURCES})
target_include_directories(enet PUBLIC ${TP}/enet-1.3.18/include)
if(WIN32)
  target_link_libraries(enet PUBLIC ws2_32 winmm)
endif()
if(MSVC)
  target_compile_options(enet PRIVATE /W0)
else()
  target_compile_options(enet PRIVATE -w)
endif()

# ---------------------------------------------------------------- Lua 5.1
file(GLOB LUA_SOURCES ${TP}/lua-5.1.5/src/*.c)
list(FILTER LUA_SOURCES EXCLUDE REGEX ".*/(lua|luac|print)\\.c$")
add_library(lua51 STATIC ${LUA_SOURCES})
target_include_directories(lua51 PUBLIC ${TP}/lua-5.1.5/src)
if(MSVC)
  target_compile_options(lua51 PRIVATE /W0)
else()
  target_compile_options(lua51 PRIVATE -w)
endif()
