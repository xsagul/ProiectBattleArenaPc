// Small functions from the transport's part of the client (rva 0x2d0000 - 0x2f1000) whose classes are not rebuilt
// yet. Each class here holds only what its one function needs; the names are ours.
#include "types.h"

// rva 0x2dbe90: empties an array of 0x28-byte objects, destroying each through its virtual destructor (fourth entry
// of the table), and sets the count to zero.
// match: 2dbe90 ?Clear@Item28Array
struct Item28
{
    virtual void Virtual0();
    virtual void Virtual1();
    virtual void Virtual2();
    virtual ~Item28();
    u8 unknown04[0x24];
};

struct Item28Array
{
    Item28* items;  // +0x00
    u32 count;      // +0x04

    void Clear();
};

void Item28Array::Clear()
{
    for (Item28* item = items, *end = items + count; item < end; ++item)
        item->~Item28();
    count = 0;
}

// rva 0x2f05f0: sets an object up through the function at rva 0x2f0480 and keeps the third argument at +4.
// match: 2f05f0 ?Set@Object2f05f0
struct Object2f05f0
{
    u32 unknown00;
    u32 value04;    // +0x04

    void SetBase(u32 a, u32 b);     // rva 0x2f0480
    void Set(u32 a, u32 b, u32 c);
};

void Object2f05f0::Set(u32 a, u32 b, u32 c)
{
    SetBase(a, b);
    value04 = c;
}

// rva 0x2d08d0: calls a stored member function on a stored object with the byte the argument points at.
// match: 2d08d0 ?Call@ByteCallback
struct CallbackTarget
{
};

struct ByteCallback
{
    u32 unknown00;
    CallbackTarget* object;                 // +0x04
    void (CallbackTarget::*method)(u32);    // +0x08

    void Call(const u8* value);
};

void ByteCallback::Call(const u8* value)
{
    (object->*method)(*value);
}

// rva 0x2d2cf0: adds the four bytes of a 32-bit value to the transport checksum.
// match: 2d2cf0 ?Add@TransportCrc32
extern const u32 g_lnpCrcTable[256]; // rva 0x1578bb0

struct TransportCrc32
{
    u32 value;
    void Add(const u32& v);
};

void TransportCrc32::Add(const u32& v)
{
    for (u32 i = 0; i < sizeof(v); ++i)
        value = ((value << 8) | ((const u8*)&v)[i]) ^ g_lnpCrcTable[value >> 24];
}

// rva 0x2ea530: notifies every non-null observer through virtual entry +0xc.
// match: 2ea530 ?Notify@BroadcastObserver
struct BroadcastObserver;
struct BroadcastListener
{
    virtual void Slot0();
    virtual void Slot4();
    virtual void Slot8();
    virtual void Changed(BroadcastObserver*);
};

struct BroadcastObserver
{
    u8 unknown00[0x78];
    BroadcastListener** listeners;
    u32 count;
    void Notify();
};

void BroadcastObserver::Notify()
{
    for (BroadcastListener** p = listeners, **end = listeners + count; p != end; ++p)
        if (*p)
            (*p)->Changed(this);
}

#include "LnpCommand.h"

struct PeerState2edca0
{
    u8 unknown00[8];
    double time08;
    u8 unknown10[0x20];
    u8 byte30;
    u8 unknown31[3];
    u32 state34;
};

struct PeerMap2edca0
{
    u8 unknown00[0x28];
    PeerState2edca0& Get(u64 key); // rva 0x2de900
};

struct Parent2edca0
{
    u8 unknown00[0x1730];
    PeerMap2edca0 map;
    double timeout1758;
};

// rva 0x2edca0: schedules a peer unless its state is already 1.
// match: 2edca0 ?Schedule@Wrapper2edca0
struct Wrapper2edca0
{
    Parent2edca0* inner;
    void Schedule(u64 key, u8 byte);
};

void Wrapper2edca0::Schedule(u64 key, u8 byte)
{
    double now = g_lnpClockOwner->clock->Now();
    Parent2edca0* parent = inner;
    PeerState2edca0& peer = parent->map.Get(key);
    if (peer.state34 != 1)
    {
        peer.state34 = 2;
        peer.time08 = now + parent->timeout1758;
        peer.byte30 = byte;
    }
}

#include <set>
void LogChannelText(const char*, const char*); // rva 0x9a8e00

// rva 0x2ec560: logs a channel's reliable and ordered flags.
// match: 2ec560 ?Log@ChannelLogging
// match: 2d3e20 ??$_Find_lower_bound@E@?$_Tree
// match: 2d02b0 ?clear@?$_Tree@V?$_Tset_traits@E
struct ChannelLogging
{
    u8 unknown00[0x1c];
    std::set<u8> reliable;
    std::set<u8> ordered;
    void Log(const char* label, u8 channel) const;
};

void ChannelLogging::Log(const char* label, u8 channel) const
{
    LogChannelText(label, reliable.count(channel) != 0 ? " reliable" : " unreliable");
    LogChannelText(label, ordered.count(channel) != 0 ? " ordered" : " unordered");
}

// Instantiating the set in this translation unit preserves the client's outlined tree search.
template class std::set<u8>;
