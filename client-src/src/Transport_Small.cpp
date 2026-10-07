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

// rva 0x2e4990: true when the object has something at +0x74 and game.cfg has [General] EnableReplayApi set.
// match: 2e4990 ?ReplayApiEnabled@Object2e4990
// 35 bytes like the client's, 27 the same: after the call the client branches ("je; mov al, 1; ret; xor al, al; ret")
// where ours sets the result directly (setne al). Return types bool / u8 / char on either function do not change it.
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
