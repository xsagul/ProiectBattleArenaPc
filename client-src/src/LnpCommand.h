// What the game's side hands to the transport's worker thread: one record of 0x100 bytes per request, put on the
// queue at +0x40 of the worker object. The layout is the one the record's constructor (rva 0x2d5ae0) and move
// assignment (rva 0x2d9820) show; only what rebuilt functions use is named. The names are ours.
#pragma once
#include "LnpDatagram.h"
#include "LnpMessage.h"
#include "LnpQueue.h"

struct LnpCommand
{
    u64 peerId = 0;         // +0x00
    u8 unknown08 = 0;
    u8 unknown09 = 0;
    u32 type;               // +0x0c  0..8, see LnpWorker_Post.cpp. Not given a value at first.
    LnpDatagram datagram;   // +0x10
    struct Part88           // +0x88, 40 bytes, copied as a block
    {
        u64 peerId = 0;
        u16 unknown08 = 0;
        u8 unknown0a = 0;
        double unknown10 = 0;
        double unknown18 = 0;
        double unknown20 = 0;
    } part88;
    LnpMessage message;     // +0xb0
    struct PartE8           // +0xe8, 24 bytes, copied as a block
    {
        u64 peerId = 0;
        u32 unknown08 = 0;
        double unknown10 = 0;
    } partE8;

    LnpCommand();                                   // rva 0x2d5ae0  both written by the compiler (LnpCommand.cpp)
    LnpCommand& operator=(LnpCommand&& other);      // rva 0x2d9820
};

typedef LnpQueue<LnpCommand, 244> LnpCommandQueue;  // Push: rva 0x2ed120 (LnpQueue.cpp)

// The clock the transport stamps things with: rva 0xa2c930 on the object at +0x20 of the one rva 0x18d9adc points to.
struct LnpClock
{
    double Now();
};

struct LnpClockOwner
{
    u8 unknown00[0x20];
    LnpClock* clock;        // +0x20
};

extern LnpClockOwner* g_lnpClockOwner;  // rva 0x18d9adc

struct LnpWorker
{
    u8 unknown00[0x40];
    LnpCommandQueue commands;   // +0x40

    void Post0();
    void Post1(u64 peerId, u8 byte08);
    void Post2(u64 peerId, u8 byte08, u8 byte09);
    void PostDatagram3(LnpDatagram& datagram);
    void PostDatagram4(LnpDatagram& datagram);
    void PostPart5(const LnpCommand::Part88& part);
    void PostMessage6(LnpMessage& message);
    void PostMessage7(LnpMessage& message);
    void PostPart8(const LnpCommand::PartE8& part);
};
