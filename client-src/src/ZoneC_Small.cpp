// Small functions between rva 0x2dc000 and 0x2e0000 whose classes are not rebuilt. Each class here holds only what
// its function needs; the names are ours.
#include "types.h"

// rva 0x2ddf20: two calls, one after the other (the second as a tail call). Called once, from rva 0x32fa20.
// match: 2ddf20 ?Call2ddf20@@YAXXZ
void Func_a19c70();     // rva 0xa19c70
void Func_a1a080();     // rva 0xa1a080

void Call2ddf20()
{
    Func_a19c70();
    Func_a1a080();
}

// rva 0x2deb60: the entry of a table of ten text pointers at rva 0x15785c0 (the first is "Spawn_Barracks"... see the
// strings behind the table).
// match: 2deb60 ?Name2deb60@@YAPBDH@Z
extern const char* const g_names15785c0[10];    // rva 0x15785c0

const char* Name2deb60(int index)
{
    return g_names15785c0[index];
}

// rva 0x2deb70: the 64-bit number at +0x88 of an object (11 callers all over the game).
// match: 2deb70 ?Get88@Object2deb70
struct Object2deb70
{
    u8 unknown00[0x88];
    u64 value88;    // +0x88

    u64 Get88() const;
};

u64 Object2deb70::Get88() const
{
    return value88;
}

// rva 0x2deab0 and 0x2df200: two texts chosen by a number of the same object (callers rva 0x66e900 and 0x695030 call
// both): "PC" when the number at +8 is 1, "LoL" / "TFT" when the number at +4 is 1 / 2, else nothing.
// match: 2deab0 ?PlatformName@Object2deab0
// match: 2df200 ?ProductName@Object2deab0
struct Object2deab0
{
    u32 unknown00;
    int product;    // +0x04  1: "LoL", 2: "TFT"
    int platform;   // +0x08  1: "PC"

    const char* PlatformName() const;
    const char* ProductName() const;
    bool IsKind3To5() const;
};

const char* Object2deab0::PlatformName() const
{
    switch (platform)
    {
    case 1:
        return "PC";
    default:
        return nullptr;
    }
}

const char* Object2deab0::ProductName() const
{
    switch (product)
    {
    case 1:
        return "LoL";
    case 2:
        return "TFT";
    default:
        return nullptr;
    }
}

// rva 0x2dedd0: true when the number at +8 of an object is 4, 5 or 3 (tested in that order).
// match: 2dedd0 ?Is4Or5Or3@Object2dedd0
struct Object2dedd0
{
    u8 unknown00[8];
    int value08;    // +0x08

    bool Is4Or5Or3() const;
};

bool Object2dedd0::Is4Or5Or3() const
{
    return value08 == 4 || value08 == 5 || value08 == 3;
}

// rva 0x2dd1b0: deletes the object the global at rva 0x3170044 points to (through its virtual destructor, the first
// entry of its table). The pointer is left as it is.
// match: 2dd1b0 ?Delete3170044@@YAXXZ
struct Object3170044
{
    virtual ~Object3170044();
};

extern Object3170044* g_object3170044;  // rva 0x3170044

void Delete3170044()
{
    delete g_object3170044;
}

// rva 0x2dd120: two calls, then the global at rva 0x3198cb4 is handed to a third function and cleared, if it is set.
// match: 2dd120 ?Close2dd120@@YAXXZ
void Func_a1a0a0();             // rva 0xa1a0a0
void Func_a16270(u32 zero);     // rva 0xa16270
void Func_a15bb0(void* object); // rva 0xa15bb0

extern void* g_object3198cb4;   // rva 0x3198cb4

void Close2dd120()
{
    Func_a1a0a0();
    Func_a16270(0);
    if (g_object3198cb4)
    {
        Func_a15bb0(g_object3198cb4);
        g_object3198cb4 = nullptr;
    }
}

// rva 0x2df1c0: a number for four known 32-bit values (hashes by the look of them) read through a pointer:
// 0x34514000 and 0x31e8a049 give 1, 0xb8ffaf71 and 0x5680a914 give 2, anything else 0.
// match: 2df1c0 ?Kind2df1c0@@YAHPBI@Z
int Kind2df1c0(const u32* hash)
{
    u32 value = *hash;
    if (value == 0x34514000 || value == 0x31e8a049)
        return 1;
    if (value == 0xb8ffaf71)
        return 2;
    if (value == 0x5680a914)
        return 2;
    return 0;
}

// rva 0x2ddcb0: sets byte at +0x162c of the inner object.
// match: 2ddcb0 ?SetByte162c@Wrapper2ddcb0@@QAEXE@Z
// rva 0x2ddcc0: sets byte at +0x19c0 of the inner object.
// match: 2ddcc0 ?SetByte19c0@Wrapper2ddcb0@@QAEXE@Z
struct Target2ddcb0
{
    u8 pad[0x162c];
    u8 byte162c; // +0x162c
    u8 pad2[0x19c0 - 0x162d];
    u8 byte19c0; // +0x19c0
};

struct Wrapper2ddcb0
{
    Target2ddcb0* inner;

    void SetByte162c(u8 value);
    void SetByte19c0(u8 value);
};

void Wrapper2ddcb0::SetByte162c(u8 value)
{
    inner->byte162c = value;
}

void Wrapper2ddcb0::SetByte19c0(u8 value)
{
    inner->byte19c0 = value;
}

// rva 0x2df320: forwards two arguments to method at rva 0x2df220 of the inner object.
// match: 2df320 ?Forward@Wrapper2df320@@QAEHII@Z
struct Inner2df320
{
    int Method2df220(u32 a, u32 b); // rva 0x2df220
};

struct Wrapper2df320
{
    Inner2df320* inner;

    int Forward(u32 a, u32 b);
};

int Wrapper2df320::Forward(u32 a, u32 b)
{
    return inner->Method2df220(a, b);
}

// rva 0x2dead0: returns ptr at +0x10 if non-null, else address of inline buffer at +0x04.
// match: 2dead0 ?c_str@String2dead0@@QBEPBDXZ
struct String2dead0
{
    u32 unknown00;
    char inline_buf[12]; // +0x04..+0x0f
    const char* ptr10;   // +0x10

    const char* c_str() const;
};

const char* String2dead0::c_str() const
{
    if (ptr10)
        return ptr10;
    return inline_buf;
}

// rva 0x2e1d70: dispatches datagram according to its sequence number: negative (ack) -> rva 0x2ed360, positive -> rva 0x2ee8a0, zero -> 1.
// match: 2e1d70 ?HandleDatagram_2e1d70@@YGEPBULnpDatagram@@@Z
// 40 of 42 bytes identical; differs in ecx vs edx temporary register
#include "LnpDatagram.h"


void __stdcall HandleAck_2ed360(const LnpDatagram* d);     // rva 0x2ed360
void __stdcall HandleSeq_2ee8a0(const LnpDatagram* d);     // rva 0x2ee8a0

u8 __stdcall HandleDatagram_2e1d70(const LnpDatagram* d)
{
    u16 number = *(const u16*)((const char*)d + 8);
    if ((short)number < 0)
    {
        HandleAck_2ed360(d);
        return 4;
    }
    if ((short)number > 0)
    {
        HandleSeq_2ee8a0(d);
        return 0;
    }
    return 1;
}






