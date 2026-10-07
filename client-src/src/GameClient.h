// The object the per-frame network pump (rva 0x370810) and the 574 handler work on; one instance, pointer at
// rva 0x317bb44. Only the members used by reconstructed functions are named; the names are ours.
#pragma once
#include "types.h"

struct LnpClient        // +0x44: the transport; its per-frame pump is rva 0x2dbdc0
{
    void Update();
};

struct Pumped160 { void Update(); };    // rva 0x41a670
struct Pumped164 { void Update(); };    // rva 0x3754d0
struct Pumped1b0 { void Update(); };    // rva 0x38ccd0
struct PumpedGlobal { void Update(); }; // rva 0x21dea0, object pointer at rva 0x316fe00

struct GameClient
{
    u8 unknown000[0x44];
    LnpClient transport;        // +0x44
    u8 unknown045[0x160 - 0x45];
    Pumped160* pumped160;       // +0x160
    Pumped164* pumped164;       // +0x164
    u8 unknown168[0x1a7 - 0x168];
    u8 localSlot;               // +0x1a7  written by the 574 handler (rva 0x364850)
    bool flag1a8;               // +0x1a8
    bool updating;              // +0x1a9  set while Update runs
    u8 unknown1aa[0x1b0 - 0x1aa];
    Pumped1b0 pumped1b0;        // +0x1b0
    u8 unknown1b1[0x2c8 - 0x1b1];
    u32 timerSlot;              // +0x2c8

    bool IsConnected() const;
    void Update();
};
