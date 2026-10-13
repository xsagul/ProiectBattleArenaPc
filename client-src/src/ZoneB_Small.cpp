// Deleting destructors and small functions in Zone B.
// match: 2db8e0 ?ScalarDeletingDestructor@Object2db8e0@@QAEPAXI@Z
#include "types.h"
#include <new>

void Destruct_9bab90(void* p); // rva 0x9bab90



struct Object2db8e0
{
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db8e0::ScalarDeletingDestructor(unsigned int flags)
{
    if (flags & 1)
        ::operator delete(this, 0xb);
    return this;
}

// rva 0x2db050: calls destructor at rva 0x2d8840 and frees 0x24 bytes if flags & 1.
// match: 2db050 ?ScalarDeletingDestructor@Object2db050@@QAEPAXI@Z
struct Object2db050
{
    void Destruct2d8840(); // rva 0x2d8840
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db050::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d8840();
    if (flags & 1)
        ::operator delete(this, 0x24);
    return this;
}

// rva 0x2db070: calls destructor at rva 0x2d8910 and frees 0x24 bytes if flags & 1.
// match: 2db070 ?ScalarDeletingDestructor@Object2db070@@QAEPAXI@Z
struct Object2db070
{
    void Destruct2d8910(); // rva 0x2d8910
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db070::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d8910();
    if (flags & 1)
        ::operator delete(this, 0x24);
    return this;
}

// rva 0x2db120: calls destructor at rva 0x2d8a60 and frees 0x30 bytes if flags & 1.
// match: 2db120 ?ScalarDeletingDestructor@Object2db120@@QAEPAXI@Z
struct Object2db120
{
    void Destruct2d8a60(); // rva 0x2d8a60
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db120::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d8a60();
    if (flags & 1)
        ::operator delete(this, 0x30);
    return this;
}

// rva 0x2db1a0: calls destructor at rva 0x2d8b90 and frees 0x38 bytes if flags & 1.
// match: 2db1a0 ?ScalarDeletingDestructor@Object2db1a0@@QAEPAXI@Z
struct Object2db1a0
{
    void Destruct2d8b90(); // rva 0x2d8b90
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db1a0::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d8b90();
    if (flags & 1)
        ::operator delete(this, 0x38);
    return this;
}

// rva 0x2db090: calls destructor at rva 0x2d8980 and frees 0x474 bytes if flags & 1.
// match: 2db090 ?ScalarDeletingDestructor@Object2db090@@QAEPAXI@Z
struct Object2db090
{
    void Destruct2d8980(); // rva 0x2d8980
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db090::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d8980();
    if (flags & 1)
        ::operator delete(this, 0x474);
    return this;
}

// rva 0x2db220: calls destructor at rva 0x2d8bf0 and frees 0x68 bytes if flags & 1.
// match: 2db220 ?ScalarDeletingDestructor@Object2db220@@QAEPAXI@Z
struct Object2db220
{
    void Destruct2d8bf0(); // rva 0x2d8bf0
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db220::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d8bf0();
    if (flags & 1)
        ::operator delete(this, 0x68);
    return this;
}

// rva 0x2db2b0: calls destructor at rva 0x2d8c60 and frees 0x240 bytes with 0x40 alignment if flags & 1.
// match: 2db2b0 ?ScalarDeletingDestructor@Object2db2b0@@QAEPAXI@Z
struct Object2db2b0
{
    void Destruct2d8c60(); // rva 0x2d8c60
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db2b0::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d8c60();
    if (flags & 1)
        ::operator delete(this, 0x240, std::align_val_t(0x40));
    return this;
}

// rva 0x2db2e0: calls destructor at rva 0x2d8f70 and frees 0x1c0 bytes with 0x40 alignment if flags & 1.
// match: 2db2e0 ?ScalarDeletingDestructor@Object2db2e0@@QAEPAXI@Z
struct Object2db2e0
{
    void Destruct2d8f70(); // rva 0x2d8f70
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db2e0::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d8f70();
    if (flags & 1)
        ::operator delete(this, 0x1c0, std::align_val_t(0x40));
    return this;
}

// rva 0x2db310: calls destructor at rva 0x2d9040 and frees 0x928 bytes if flags & 1.
// match: 2db310 ?ScalarDeletingDestructor@Object2db310@@QAEPAXI@Z
struct Object2db310
{
    void Destruct2d9040(); // rva 0x2d9040
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db310::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d9040();
    if (flags & 1)
        ::operator delete(this, 0x928);
    return this;
}

// rva 0x2db340: calls destructor at rva 0x2d90b0 and frees 0x418 bytes if flags & 1.
// match: 2db340 ?ScalarDeletingDestructor@Object2db340@@QAEPAXI@Z
struct Object2db340
{
    void Destruct2d90b0(); // rva 0x2d90b0
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db340::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d90b0();
    if (flags & 1)
        ::operator delete(this, 0x418);
    return this;
}

// rva 0x2db370: calls destructor at rva 0x2d9110 and frees 0x28 bytes if flags & 1.
// match: 2db370 ?ScalarDeletingDestructor@Object2db370@@QAEPAXI@Z
struct Object2db370
{
    void Destruct2d9110(); // rva 0x2d9110
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db370::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d9110();
    if (flags & 1)
        ::operator delete(this, 0x28);
    return this;
}

// rva 0x2db390: calls destructor at rva 0x2d9170 and frees 0x1c0 bytes with 0x40 alignment if flags & 1.
// match: 2db390 ?ScalarDeletingDestructor@Object2db390@@QAEPAXI@Z
struct Object2db390
{
    void Destruct2d9170(); // rva 0x2d9170
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db390::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d9170();
    if (flags & 1)
        ::operator delete(this, 0x1c0, std::align_val_t(0x40));
    return this;
}

// rva 0x2db420: calls destructor at rva 0x2d93e0 and frees 0x88 bytes if flags & 1.
// match: 2db420 ?ScalarDeletingDestructor@Object2db420@@QAEPAXI@Z
struct Object2db420
{
    void Destruct2d93e0(); // rva 0x2d93e0
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db420::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d93e0();
    if (flags & 1)
        ::operator delete(this, 0x88);
    return this;
}

// rva 0x2db700: calls destructor at rva 0x34c210 and frees 0x1c bytes if flags & 1.
// match: 2db700 ?ScalarDeletingDestructor@Object2db700@@QAEPAXI@Z
struct Object2db700
{
    void Destruct34c210(); // rva 0x34c210
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db700::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct34c210();
    if (flags & 1)
        ::operator delete(this, 0x1c);
    return this;
}

// rva 0x2db720: calls destructor at rva 0xa23f10 and frees 0x74 bytes if flags & 1.
// match: 2db720 ?ScalarDeletingDestructor@Object2db720@@QAEPAXI@Z
struct Object2db720
{
    void Destructa23f10(); // rva 0xa23f10
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db720::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destructa23f10();
    if (flags & 1)
        ::operator delete(this, 0x74);
    return this;
}

// rva 0x2db8b0: the compiler's scalar deleting destructor of a 0x18-byte class with a virtual destructor and an
// RString at +0xc (identical code folding gives the same function to the tables of 11 classes, e.g. 0x157953c).
// match: 2db8b0 ??_GObject2db8b0@@UAEPAXI@Z
#include "RString.h"

struct Object2db8b0
{
    virtual ~Object2db8b0() = default;
    u32 unknown04;
    u32 unknown08;
    RString name;           // +0x0c
    Object2db8b0();
};

Object2db8b0::Object2db8b0() : name("") {}


// rva 0x2db970: calls destructor at rva 0xac9970 and frees 0xc bytes if flags & 1.
// match: 2db970 ?ScalarDeletingDestructor@Object2db970@@QAEPAXI@Z
struct Object2db970
{
    void Destructac9970(); // rva 0xac9970
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2db970::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destructac9970();
    if (flags & 1)
        ::operator delete(this, 0xc);
    return this;
}

// rva 0x2dad60: calls destructor on +4 and frees 8 bytes if flags & 1.
// match: 2dad60 ?ScalarDeletingDestructor@Object2dad60@@QAEPAXI@Z
struct K9baf90
{
    __declspec(noinline) int f(); // rva 0x9baf90, reconstructed in gen/Small_960000.cpp
};

struct Object2dad60
{
    void* vptr;
    K9baf90 member4;

    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2dad60::ScalarDeletingDestructor(unsigned int flags)
{
    this->member4.f();
    if (flags & 1)
        ::operator delete(this, 8);
    return this;
}

// rva 0x2daf70: calls destructor at rva 0x2d86e0 and frees 0x148 bytes if flags & 1.
// match: 2daf70 ?ScalarDeletingDestructor@Object2daf70@@QAEPAXI@Z
struct Object2daf70
{
    void Destruct2d86e0(); // rva 0x2d86e0
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2daf70::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct2d86e0();
    if (flags & 1)
        ::operator delete(this, 0x148);
    return this;
}

// rva 0x2dae90: resets vtable to 0xfb3474, clears member4, and frees 8 bytes if flags & 1.
// match: 2dae90 ?ScalarDeletingDestructor@Object2dae90@@QAEPAXI@Z
extern const void* g_vtablefb3474; // rva 0xfb3474

struct Object2dae90
{
    const void* vtable;
    u32 member4;

    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2dae90::ScalarDeletingDestructor(unsigned int flags)
{
    this->member4 = 0;
    this->vtable = &g_vtablefb3474;
    if (flags & 1)
        ::operator delete(this, 8);
    return this;
}

// rva 0x2dbff0: clones 8-byte object using operator new(8) and sets vtable 0x15796e0.
// match: 2dbff0 ?Clone@Object2dbff0@@QAEPAUCloned2dbff0@@XZ
extern const void* g_vtable15796e0; // rva 0x15796e0

struct Cloned2dbff0
{
    const void* vtable;
    u32 val4;
};

struct Object2dbff0
{
    u32 pad0;
    u32 val4;

    Cloned2dbff0* Clone();
};

Cloned2dbff0* Object2dbff0::Clone()
{
    Cloned2dbff0* obj = (Cloned2dbff0*)::operator new(8);
    if (obj)
    {
        obj->vtable = &g_vtable15796e0;
        obj->val4 = this->val4;
        return obj;
    }
    return nullptr;
}

// rva 0x2dabb0: calls destructor at rva 0x5d5f20 and frees 0x87d0 bytes if flags & 1.
// match: 2dabb0 ?ScalarDeletingDestructor@Object2dabb0@@QAEPAXI@Z
struct Object2dabb0
{
    void Destruct5d5f20(); // rva 0x5d5f20
    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2dabb0::ScalarDeletingDestructor(unsigned int flags)
{
    this->Destruct5d5f20();
    if (flags & 1)
        ::operator delete(this, 0x87d0);
    return this;
}

// rva 0x2dad10: deleting destructor of Object2da8b0 (size 0x5e0, GlobalInstance base).
// match: 2dad10 ?ScalarDeletingDestructor@Object2da8b0@@QAEPAXI@Z
struct Sub2d7ec0
{
    void Destruct(); // rva 0x2d7ec0
};

struct Sub2d8030
{
    void Destruct(); // rva 0x2d8030
};

extern const void* g_vtable157a6c4; // rva 0x157a6c4
extern void* g_instance3172a60;    // rva 0x3172a60

struct Object2da8b0
{
    const void* vtable;
    u8 pad04[0x1c];
    Sub2d8030 member20;

    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2da8b0::ScalarDeletingDestructor(unsigned int flags)
{
    ((Sub2d8030*)((char*)this + 0x20))->Destruct();
    ((Sub2d7ec0*)((char*)this + 0x10))->Destruct();
    ((Sub2d7ec0*)((char*)this + 0x04))->Destruct();
    this->vtable = &g_vtable157a6c4;
    g_instance3172a60 = nullptr;
    if (flags & 1)
        ::operator delete(this, 0x5e0);
    return this;
}

// rva 0x2dafa0: deleting destructor of Object2da7c0 (size 8, GlobalInstance base).
// match: 2dafa0 ?ScalarDeletingDestructor@Object2da7c0@@QAEPAXI@Z
extern const void* g_vtable157931c; // rva 0x157931c
extern void* g_instance316fda8;    // rva 0x316fda8

struct Object2da7c0
{
    const void* vtable;
    u32 member4;

    void* ScalarDeletingDestructor(unsigned int flags);
};

void* Object2da7c0::ScalarDeletingDestructor(unsigned int flags)
{
    this->vtable = &g_vtable157931c;
    g_instance316fda8 = nullptr;
    if (flags & 1)
        ::operator delete(this, 8);
    return this;
}







