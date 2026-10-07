// A message of the transport as it travels inside the client (0x34 bytes) and the event that carries one to the
// application's queue (0x50 bytes). Only what reconstructed functions use is named; the names are ours.
#pragma once
#include <functional>
#include "LnpBuffer.h"
#include "LnpQueue.h"

struct LnpMessage
{
    u64 peerId = 0;             // +0x00
    u16 number = 0;             // +0x08  per channel, one more than the message before
    u8 unknown0a = 0;
    u8 channel = 0;             // +0x0b
    u16 unknown0c = 0;
    double time = 0;            // +0x10  set from the clock when the message is queued for the worker (rva 0x2dd4e0)
    u16 fragmentId = 0;         // +0x18  0: the message is whole
    u8 fragmentCount = 0;       // +0x1a
    u8 fragmentIndex = 0;       // +0x1b
    u32 unknown1c = 0;
    u32 unknown20 = 0;
    LnpBuffer payload;          // +0x24
    const char* text30 = nullptr;   // +0x30  the reader sets it to an empty string

    // Every member starts at zero (the client zeroes them one by one wherever it makes a message; where it makes one
    // inside a bigger object it first clears all 0x38 bytes: no constructor written by hand, only these initialisers).
    LnpMessage() = default;

    // Declared here and defined in LnpMessage.cpp, so that it is a function of its own, as in the client
    // (rva 0x2d5c00); left to the compiler inside the class, it is put inline wherever a message is copied.
    LnpMessage(const LnpMessage& other);
    LnpMessage& operator=(LnpMessage&& other);     // rva 0x2d98c0, likewise

    bool Write(LnpBuffer& out, const LnpMessage& previous) const;
    bool Read(LnpBuffer& in, const LnpMessage& previous);
};

struct LnpEvent
{
    u32 type;           // +0x00  2: a message arrived
    u64 peerId;         // +0x08
    u8 unknown10;       // +0x10  two separate bytes: the queue (rva 0x2ed000) copies them one by one
    u8 unknown11;
    LnpMessage message; // +0x18
};

typedef LnpQueue<LnpEvent, 734> LnpEventQueue;      // Push: rva 0x2ed000 (LnpQueue.cpp)

// The part of the transport the game talks to (at +0x1c0 of the transport's implementation object): the transport's
// threads put events on its queue, the game's thread takes them off once per frame and hands them to two callbacks.
struct LnpAppObserver
{
    u8 unknown00[0x80];
    LnpEventQueue events;       // +0x80
    std::function<void(u64 peerId, bool event0, u8 byte10, u8 byte11)> onPeer;                          // +0x1c0
    std::function<void(u64 peerId, u8 channel, double time, const u8* data, u32 size)> onMessage;       // +0x1e8

    bool OnMessage(const LnpMessage& message);
    bool OnEvent0(u64 peerId, u8 byte10, u32 unused1, u32 unused2);
    bool OnEvent1(u64 peerId, u8 byte10, u32 unused1, u32 unused2, u8 byte11);
    void Update();
};
