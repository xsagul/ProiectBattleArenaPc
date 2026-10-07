// SUPERSEDED (2026-10-07): the start-up functions and member functions are generated now (gen/MetaClasses.cpp,
// gen/MetaMembers.cpp; Meta.h). Kept for its notes on the list member (rva 0x2d0df0) and its elements object.
// (The five forwarding ones, rva 0x2d0e50 / 0x2d0eb0 / 0x2d0ee0 / 0x2d0f10 / 0x2d0e80, are MetaClass::AddMember<T>
// instantiations now, generated in gen/MetaMembers.cpp; only the list member below is still by hand.)
// Six small functions that describe one member each of a data class to the client's class descriptions (the start-up
// functions at rva 0xa48f0 - 0xa4db0 call them on the descriptions at rva 0x31761c0 and neighbours, with the member's
// name hash, its offset in the object and one more word). All six only fill in the arguments of the general function
// at rva 0x9bd410: a type code, the description of the class the member refers to and, for a list, a small object
// that tells the element's type code and size. The names are ours; what the type codes mean is not measured here.
//   rva 0x2d0e50  code 0x84, class description at rva 0x3176160
//   rva 0x2d0eb0  code 0x83, class description at rva 0x3176338
//   rva 0x2d0ee0  code 0x83, class description at rva 0x31766c0
//   rva 0x2d0f10  code 0x83, class description at rva 0x3176710
//   rva 0x2d0e80  code 0x83, class description from the function at rva 0x3f0f90 (it returns rva 0x317ca40)
//   rva 0x2d0df0  code 0x80, class description at rva 0x31763a8, elements of code 0x82 and 4 bytes
#include "types.h"

// What a list member's elements are. The base keeps the two values, the class made here (virtual table at rva
// 0xfb8bd4, six entries) adds only its functions: the client stores the two values first and the table last, which
// is the order of a base class's constructor followed by the derived one's.
struct MetaElementsBase
{
    u8 code;    // +0x04
    u32 size;   // +0x08

    MetaElementsBase(u8 code, u32 size) : code(code), size(size) {}
    virtual ~MetaElementsBase();
    virtual void Virtual1() = 0;
    virtual void Virtual2() = 0;
    virtual void Virtual3() = 0;
    virtual void Virtual4() = 0;
    virtual void Virtual5() = 0;
};

struct MetaElements82 : MetaElementsBase
{
    MetaElements82() : MetaElementsBase(0x82, 4) {}
    ~MetaElements82() override;
    void Virtual1() override;
    void Virtual2() override;
    void Virtual3() override;
    void Virtual4() override;
    void Virtual5() override;
};

struct MetaClass
{
    void AddMember(u32 nameHash, u32 offset, u32 code, u32 zero0, MetaClass* of, MetaElementsBase* elements,
                   u32 zero1, const char* text, u32 last);     // rva 0x9bd410

    void AddMember84_3176160(u32 nameHash, u32 offset, u32 last);
    void AddMember83_3176338(u32 nameHash, u32 offset, u32 last);
    void AddMember83_31766c0(u32 nameHash, u32 offset, u32 last);
    void AddMember83_3176710(u32 nameHash, u32 offset, u32 last);
    void AddMember83_317ca40(u32 nameHash, u32 offset, u32 last);
    void AddMember80_31763a8(u32 nameHash, u32 offset, u32 last);
};

extern MetaClass g_metaClass3176160;    // rva 0x3176160
extern MetaClass g_metaClass3176338;    // rva 0x3176338
extern MetaClass g_metaClass31763a8;    // rva 0x31763a8
extern MetaClass g_metaClass31766c0;    // rva 0x31766c0
extern MetaClass g_metaClass3176710;    // rva 0x3176710
MetaClass* MetaClass317ca40_Get();      // rva 0x3f0f90

void MetaClass::AddMember84_3176160(u32 nameHash, u32 offset, u32 last)
{
    AddMember(nameHash, offset, 0x84, 0, &g_metaClass3176160, nullptr, 0, "", last);
}

void MetaClass::AddMember83_3176338(u32 nameHash, u32 offset, u32 last)
{
    AddMember(nameHash, offset, 0x83, 0, &g_metaClass3176338, nullptr, 0, "", last);
}

void MetaClass::AddMember83_31766c0(u32 nameHash, u32 offset, u32 last)
{
    AddMember(nameHash, offset, 0x83, 0, &g_metaClass31766c0, nullptr, 0, "", last);
}

void MetaClass::AddMember83_3176710(u32 nameHash, u32 offset, u32 last)
{
    AddMember(nameHash, offset, 0x83, 0, &g_metaClass3176710, nullptr, 0, "", last);
}

void MetaClass::AddMember83_317ca40(u32 nameHash, u32 offset, u32 last)
{
    AddMember(nameHash, offset, 0x83, 0, MetaClass317ca40_Get(), nullptr, 0, "", last);
}

void MetaClass::AddMember80_31763a8(u32 nameHash, u32 offset, u32 last)
{
    MetaElementsBase* elements = new MetaElements82();
    AddMember(nameHash, offset, 0x80, 0, &g_metaClass31763a8, elements, 0, "", last);
}
