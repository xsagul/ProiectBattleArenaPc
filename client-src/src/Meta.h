// The client's reflection: every data class that .bin files can hold has a global class description (MetaClass) made
// at start-up. The description knows the class's name hash, how to make / place / destroy an object of it, its size and
// alignment, its base class's description and its members (name hash, offset, .bin type code). Names of classes and
// members are Riot's (their FNV-1a hashes are in the client and in data/hashes); names of the C++ machinery are ours.
// Measured: rva 0x9b9a60 (constructor), 0x9bb6c0 (destructor), 0x9bd410 (AddMember), the start-up functions of the
// descriptions (rva 0x89210, 0x87940, 0x87660 and the others generated in gen/MetaClasses.cpp).
#pragma once
#include "types.h"
#include <new>     // operator new: Riot's replacement at rva 0x9bb8d0; placement new without a null test

// FNV-1a of the lower-case text: the hash .bin files use for class and member names.
constexpr u32 Hash(const char* s)
{
    u32 h = 0x811c9dc5u;
    for (; *s; ++s)
        h = (h ^ (u8)(*s >= 'A' && *s <= 'Z' ? *s + 32 : *s)) * 0x01000193u;
    return h;
}
template <u32 H> struct HashOf { static constexpr u32 value = H; };
#define HASH(s) HashOf<Hash(s)>::value

struct MetaClass
{
    typedef void* (*CreateFn)();
    typedef void (*DestroyFn)(void*);
    typedef void* (*ConstructFn)(void*);
    typedef void (*DestructFn)(void*);
    typedef void (*Virtual2Fn)(void*);

    u32 unknown00;
    u32 hash;                   // +0x04
    CreateFn create;            // +0x08  new T (null for an abstract class)
    DestroyFn destroy;          // +0x0c  delete
    ConstructFn construct;      // +0x10  new (p) T (null for an abstract class)
    DestructFn destruct;        // +0x14  p->~T()
    Virtual2Fn virtual2;        // +0x18  calls the object's third virtual function (slot 2; empty in most classes)
    const MetaClass* parent;    // +0x1c
    u32 size;                   // +0x20
    u32 align;                  // +0x24
    bool unknown28;
    bool unknown29;
    bool unknown2a;
    u8 unknown2b[0x50 - 0x2b];  // member list (+0x2c) and two vectors (+0x38, +0x44)

    MetaClass(u32 hash, CreateFn create, DestroyFn destroy, ConstructFn construct, DestructFn destruct,
              Virtual2Fn virtual2, u32 size, u32 align, bool unknown28, bool unknown29);      // rva 0x9b9a60
    ~MetaClass();                                                                           // rva 0x9bb6c0

    void AddMember(u32 hash, u32 offset, u32 code, u32 unknown0, const MetaClass* of, void* elements, u32 unknown1,
                   const char* text, u32 last);                                             // rva 0x9bd410
    // one member of C++ type T; defined for each type in Meta_Members.cpp (the start-up functions call it)
    template <class T> void AddMember(u32 hash, u32 offset, u32 last);
};

// Each description is a global of a class of its own whose inline constructor does the whole set-up: the base
// constructor with the class's facts, then the base class's description (an address, or a call when that description
// lives in another file) and the members in order (gen/MetaClasses.cpp). Measured on rva 0x8b7f0: a lambda or a
// shared template constructor leaves calls the client does not have; this form gives the client's code.

// The functions a description points at, one per class (identical code folding gives most of them one address).
template <class T> void* MetaCreate();
template <class T> void MetaDestroy(void* p);
template <class T> void* MetaConstruct(void* p);
template <class T> void MetaDestruct(void* p);
template <class T> void MetaVirtual2(void* p);
template <class T> const MetaClass* MetaStaticClass();   // the description of T, from a function of T's own file

// The C++ base of the described classes that have a virtual table (name ours): slot 0 the destructor, slot 1 the
// class's description (MetaStaticClass of the class has the same code), slot 2 a function that is empty in most.
struct BinObject
{
    virtual ~BinObject() {}                     // inline: the deleting destructors only store its table (rva 0x1533474)
    virtual const MetaClass* GetClass() const = 0;
    virtual void Virtual2();
};


// C++ types of members, by .bin type code (names ours).
struct Vector2 { float x, y; };
struct Vector3 { float x, y, z; };
struct Vector4 { float x, y, z, w; };
struct Matrix44 { float m[16]; };
struct Color { u8 r, g, b, a; };
struct HashValue { u32 value; };
struct FileLink { u64 value; };
template <class T> struct MetaEmbed;     // code 0x83: a T held by value
template <class T> struct MetaLink;      // code 0x84: a reference to a T by name
template <class T> struct MetaPointer;   // code 0x82: an owned T or derived
// containers (the variant number tells apart container types the client has with the same elements)
template <class E, int Variant = 0> struct BinList;        // code 0x80
template <class E, int Variant = 0> struct BinList2;       // code 0x81
template <class E, int Variant = 0> struct BinOption;      // code 0x85
template <class K, class V, int Variant = 0> struct BinMap;     // code 0x86
template <u32 Code, u32 Size> struct BinValue;              // an element whose C++ type is not known yet

// The .bin type code of a member type and the description it refers to (for the codes that refer to one).
template <class T> struct MetaType;
#define META_TYPE(T, c)     template <> struct MetaType<T> { enum : u32 { code = c }; static const MetaClass* Of() { return nullptr; } };
META_TYPE(bool, 1)
META_TYPE(signed char, 2)
META_TYPE(u8, 3)
META_TYPE(short, 4)
META_TYPE(u16, 5)
META_TYPE(int, 6)
META_TYPE(u32, 7)
META_TYPE(long long, 8)
META_TYPE(u64, 9)
META_TYPE(float, 0xa)
META_TYPE(Vector2, 0xb)
META_TYPE(Vector3, 0xc)
META_TYPE(Vector4, 0xd)
META_TYPE(Matrix44, 0xe)
META_TYPE(Color, 0xf)
META_TYPE(struct MetaString, 0x10)
META_TYPE(HashValue, 0x11)
META_TYPE(FileLink, 0x12)
#undef META_TYPE
// Where the member function of type W<K> gets the description of K from: its address, or (MetaFromCall<W<K>>) a call
// of MetaStaticClass<K>() when the description was not visible in the file that made the function.
template <class T> struct MetaFromCall { static constexpr bool value = false; };
template <class T, class K> const MetaClass* MetaOf()
{
    if constexpr (MetaFromCall<T>::value)
        return MetaStaticClass<K>();
    else
        return MetaClassOf((K*)nullptr);
}
template <class K> struct MetaType<MetaPointer<K>> { enum : u32 { code = 0x82 }; static const MetaClass* Of() { return MetaOf<MetaPointer<K>, K>(); } };
template <class K> struct MetaType<MetaEmbed<K>> { enum : u32 { code = 0x83 }; static const MetaClass* Of() { return MetaOf<MetaEmbed<K>, K>(); } };
template <class K> struct MetaType<MetaLink<K>> { enum : u32 { code = 0x84 }; static const MetaClass* Of() { return MetaOf<MetaLink<K>, K>(); } };
