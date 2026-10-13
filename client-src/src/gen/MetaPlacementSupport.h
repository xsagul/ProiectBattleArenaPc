// Native placement support, distinct from serialized container tags.
#pragma once
#include "ReflectedBuffers.h"
#include <list>
#include <map>
#include <cstddef>
struct Class_bafabcc8;
extern Class_bafabcc8* g_36ed6c0; // VA 0x36ed6c0
template<class T> struct LevelSingleton {
    LevelSingleton(T* owner) { g_36ed6c0 = owner; }
};
struct SummonerIconData;
struct SummonerRegistry {
    u8 unknown00[0x1c];
    std::map<u32,SummonerIconData*> icons;
    void Register(u32 id, SummonerIconData* icon);
    SummonerIconData* Find(u32 id);
};
static_assert(offsetof(SummonerRegistry,icons)==0x1c,"native registry map offset");
extern SummonerRegistry* g_2aa7460; // VA 0x2aa7460
