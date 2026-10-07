// rva 0x370810  Net_PerFrame: pumps the transport and four other objects once per frame, guarded against re-entry, and
// adds the time it took, in milliseconds, to one slot of a table of timers when that table exists.
// match: 370810 Update@GameClient
#include "GameClient.h"

u64 Time_Ticks();       // rva 0x9cbbc0
u64 Time_Frequency();   // rva 0x9cbb70

struct TimerTable
{
    u8 unknown00[0x10];
    float* milliseconds;    // +0x10
    u32 count;              // +0x14
};

extern TimerTable* g_timerTable;        // rva 0x316f45c
extern PumpedGlobal* g_pumpedGlobal;    // rva 0x316fe00

void GameClient::Update()
{
    u32 slot = timerSlot;
    u64 start = Time_Ticks();
    if (!updating)
    {
        updating = true;
        transport.Update();
        pumped160->Update();
        pumped164->Update();
        g_pumpedGlobal->Update();
        pumped1b0.Update();
        updating = false;
    }
    TimerTable* table = g_timerTable;
    if (table)
    {
        u64 elapsed = Time_Ticks() - start;
        if (slot < table->count)
            table->milliseconds[slot] += (float)((double)elapsed * 1000.0 / (double)Time_Frequency());
    }
}
