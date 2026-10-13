// flags: -O2 -std:c++17 -d2SSAOptimizer-
#include "types.h"

// rva 0x2e4990: true when the object has something at +0x74 and game.cfg has [General] EnableReplayApi set.
// match: 2e4990 ?ReplayApiEnabled@Object2e4990
// The legacy SSA profile below empirically reproduces all 36 bytes and the call/literal targets.
// This proves one equivalent compilation form; it does not identify the client's original flags.
bool Config_GetBool(const char* section, const char* key, bool fallback);  // rva 0x996470

struct Object2e4990
{
    u8 unknown00[0x74];
    u32 value74;    // +0x74

    bool ReplayApiEnabled() const;
};

bool Object2e4990::ReplayApiEnabled() const
{
    if (value74 != 0 && Config_GetBool("General", "EnableReplayApi", false))
        return true;
    return false;
}

