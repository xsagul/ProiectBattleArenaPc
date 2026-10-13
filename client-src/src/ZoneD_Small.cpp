// Small free functions and one-line members between rva 0x2e3000 and 0x2f4000 whose classes are not rebuilt.
// Each class here holds only what its one function needs; the names are ours.
#include <bitset>
#include "types.h"
#include <new>

// rva 0x2e4940: true when the object the pointer at rva 0x25272b8 leads to has 2 at +8.
// match: 2e4940 ?Object25272b8_Is2@@YA_NXZ
struct Object25272b8
{
    u8 unknown00[8];
    u32 value08;    // +0x08
};

extern Object25272b8* g_object25272b8;  // rva 0x25272b8

bool Object25272b8_Is2()
{
    return g_object25272b8->value08 == 2;
}

// rva 0x2f36e0: keeps a byte in the global at rva 0x317612c.
// match: 2f36e0 ?SetFlag317612c@@YAX_N@Z
extern bool g_flag317612c;  // rva 0x317612c

void SetFlag317612c(bool value)
{
    g_flag317612c = value;
}

// rva 0x2f0950: hands its argument to the member function at rva 0x99f920 of the object at rva 0x3170044.
// match: 2f0950 ?Object3170044_Call@@YAXI@Z
struct Object3170044
{
    void Method99f920(u32 value);   // rva 0x99f920
};

extern Object3170044* g_object3170044;  // rva 0x3170044

void Object3170044_Call(u32 value)
{
    g_object3170044->Method99f920(value);
}

// rva 0x2e8a30 and 0x2e8a50: while the global at rva 0x317613c is zero, call rva 0xa162e0 / 0xa162c0 with 0.
// match: 2e8a30 ?CallA162e0Unless317613c@@YAXXZ
// match: 2e8a50 ?CallA162c0Unless317613c@@YAXXZ
extern u32 g_value317613c;      // rva 0x317613c
void Function_a162e0(u32 value);    // rva 0xa162e0
void Function_a162c0(u32 value);    // rva 0xa162c0

void CallA162e0Unless317613c()
{
    if (g_value317613c == 0)
        Function_a162e0(0);
}

void CallA162c0Unless317613c()
{
    if (g_value317613c == 0)
        Function_a162c0(0);
}

// rva 0x2f2c10: std::bitset<64>::_Xran, the library's "invalid bitset position" error (callers: rva 0x2ed360 and
// 0x2ee8a0, which test bits of a 64-bit mask). Instantiated here by a use of bitset::test.
// match: 2f2c10 ?_Xran@?$bitset@$0EA@@std@@
bool ZoneD_UseBitsetTest(const std::bitset<64>& bits, u32 position)
{
    return bits.test(position);
}

// rva 0x2f2800: calls method at rva 0x40d070 on the sub-object at +0x10 of global 0x316d658.
// match: 2f2800 ?Function2f2800@@YAXXZ
struct Target40d070
{
    void Method40d070(); // rva 0x40d070
};

struct Object316d658
{
    u8 pad[0x10];
    Target40d070* sub10;
};

extern Object316d658* g_object316d658; // rva 0x316d658

void Function2f2800()
{
    g_object316d658->sub10->Method40d070();
}

// rva 0x2f2870: calls the 5th virtual method (offset 0x10) on the object pointed to by *ptr.
// match: 2f2870 ?CallVirtual10_2f2870@@YGXPAPAUInterface2f2870@@@Z
struct Interface2f2870
{
    virtual void Method00() = 0;
    virtual void Method04() = 0;
    virtual void Method08() = 0;
    virtual void Method0c() = 0;
    virtual void Method10() = 0;
};

void __stdcall CallVirtual10_2f2870(Interface2f2870** ptr)
{
    (*ptr)->Method10();
}

// rva 0x2f2740: sets vtable 0x157adcc into dst and returns dst.
// match: 2f2740 ?Construct157adcc@@YGPAXPAX@Z
extern const void* g_vtable157adcc; // rva 0x157adcc

void* __stdcall Construct157adcc(void* dst)
{
    *(const void**)dst = &g_vtable157adcc;
    return dst;
}

// rva 0x2f2750: sets vtable 0x157adb4 into dst and returns dst.
// match: 2f2750 ?Construct157adb4@@YGPAXPAX@Z
extern const void* g_vtable157adb4; // rva 0x157adb4

void* __stdcall Construct157adb4(void* dst)
{
    *(const void**)dst = &g_vtable157adb4;
    return dst;
}

// rva 0x2f2760: sets vtable 0x157ae2c into dst and returns dst.
// match: 2f2760 ?Construct157ae2c@@YGPAXPAX@Z
extern const void* g_vtable157ae2c; // rva 0x157ae2c

void* __stdcall Construct157ae2c(void* dst)
{
    *(const void**)dst = &g_vtable157ae2c;
    return dst;
}

// rva 0x2f2770: sets vtable 0x157ade4 into dst and returns dst.
// match: 2f2770 ?Construct157ade4@@YGPAXPAX@Z
extern const void* g_vtable157ade4; // rva 0x157ade4

void* __stdcall Construct157ade4(void* dst)
{
    *(const void**)dst = &g_vtable157ade4;
    return dst;
}

// rva 0x2f2700: copies an 8-byte object with vtable 0x157ae14 into dst.
// match: 2f2700 ?Clone@Object2f2700@@QBEPAXPAX@Z
extern const void* g_vtable157ae14; // rva 0x157ae14

struct Object2f2700
{
    const void* vtable;
    u32 val4;

    void* Clone(void* dst) const;
};

void* Object2f2700::Clone(void* dst) const
{
    *(const void**)dst = &g_vtable157ae14;
    *(u32*)((char*)dst + 4) = this->val4;
    return dst;
}

// rva 0x2f2720: copies a 12-byte object with vtable 0x157ae44 into dst.
// match: 2f2720 ?Clone@Object2f2720@@QBEPAXPAX@Z
extern const void* g_vtable157ae44; // rva 0x157ae44

struct Data8 { u32 a; u32 b; };

struct Object2f2720
{
    const void* vtable;
    Data8 data;

    void* Clone(void* dst) const;
};

void* Object2f2720::Clone(void* dst) const
{
    *(const void**)dst = &g_vtable157ae44;
    *(Data8*)((char*)dst + 4) = this->data;
    return dst;
}



// rva 0x2f08b0: sets u32 at +0x1630 of the inner object.
// match: 2f08b0 ?SetVal1630@Wrapper2f08b0@@QAEXI@Z
struct Target2f08b0
{
    u8 pad[0x1630];
    u32 val1630;
};

struct Wrapper2f08b0
{
    Target2f08b0* inner;

    void SetVal1630(u32 val);
};

void Wrapper2f08b0::SetVal1630(u32 val)
{
    inner->val1630 = val;
}

// rva 0x2ee180: calls method at rva 0x34f000 on result of rva 0x353670 passing &sub38.
// match: 2ee180 ?Method2ee180@Object2ee180@@QAEXXZ
// rva 0x2ee2f0: calls method at rva 0x36eba0 on result of rva 0x353670 passing &sub38.
// match: 2ee2f0 ?Method2ee2f0@Object2ee180@@QAEXXZ
struct Target34f000
{
    void Method34f000(void* arg); // rva 0x34f000
    void Method36eba0(void* arg); // rva 0x36eba0
};

int k353670(); // rva 0x353670, reconstructed in gen/Small_2e0000.cpp

struct Object2ee180
{
    u8 pad[0x38];
    u8 sub38[4];

    void Method2ee180();
    void Method2ee2f0();
};

void Object2ee180::Method2ee180()
{
    ((Target34f000*)k353670())->Method34f000(&sub38);
}

void Object2ee180::Method2ee2f0()
{
    ((Target34f000*)k353670())->Method36eba0(&sub38);
}

// rva 0x2e30e0: returns true unless the 64-bit field at +0x88 is 0x00000000ffffffff.
// match: 2e30e0 ?IsValid@Object2e30e0@@QBE_NXZ
struct Object2e30e0
{
    u8 pad[0x88];
    u64 value88;

    bool IsValid() const;
};

bool Object2e30e0::IsValid() const
{
    return value88 != 0x00000000ffffffffULL;
}



// rva 0x2e6c80: calls method at rva 0x32f7d0 on sub-object +0x348 of global 0x3176824 if present.
// match: 2e6c80 ?Function2e6c80@@YAXI@Z
struct Sub3176824
{
    void Method32f7d0(u32 arg); // rva 0x32f7d0
};

struct Object3176824
{
    u8 pad[0x348];
    Sub3176824 sub348;
};

extern Object3176824* g_object3176824; // rva 0x3176824

void Function2e6c80(u32 arg)
{
    if (g_object3176824)
        g_object3176824->sub348.Method32f7d0(arg);
}

// rva 0x2f0930: sets double at +0x420 and +0x1758 of the inner object.
// match: 2f0930 ?SetTime@Wrapper2f0930@@QAEXN@Z
struct Target2f0930
{
    u8 pad420[0x420];
    double time420; // +0x420
    u8 pad1758[0x1758 - 0x428];
    double time1758; // +0x1758
};

struct Wrapper2f0930
{
    Target2f0930* inner;

    void SetTime(double time);
};

void Wrapper2f0930::SetTime(double time)
{
    inner->time420 = time;
    inner->time1758 = time;
}















// rva 0x2f27d0: invokes the callback with three 64-bit values and two 32-bit values.
// match: 2f27d0 ?Invoke@Delegate2f27d0
struct Delegate2f27d0
{
    void* vtable;
    void (*fn)(u32, u64, u64, u64, u32);
    void Invoke(u32 a, const u64& b, const u64& c, const u64& d, const u32& e);
};

void Delegate2f27d0::Invoke(u32 a, const u64& b, const u64& c, const u64& d, const u32& e)
{
    fn(a, b, c, d, e);
}
