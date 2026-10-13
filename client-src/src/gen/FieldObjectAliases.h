// Shared layouts reconstructed from the object assignments and vector ownership paths.
// object: 7ec350 FieldObj_7ec350
#pragma once
#include "../types.h"

struct FieldElement7b89e0
{
    virtual void Slot0();
    virtual void Slot1();
    virtual void Slot2();
    virtual ~FieldElement7b89e0();
    u8 fields[204];
    FieldElement7b89e0(const FieldElement7b89e0& other); // rva 0x7b89e0
};

struct FieldVector7eadb0
{
    FieldElement7b89e0* data;
    u32 count;
    u32 capacity;
    FieldVector7eadb0& operator=(const FieldVector7eadb0& other);
};

struct FieldObj_7ec350
{
    virtual void Slot0();
    virtual char Read(const u8** cursor, const u8* end);
    u32 member04;
    u32 member08;
    u8 member0c;
    FieldVector7eadb0 vector10;
    u8 member1c;
    u32 member20;
    u32 member24;
    u32 member28;
    u32 member2c;
    FieldObj_7ec350();
    FieldObj_7ec350& operator=(const FieldObj_7ec350& other);
    ~FieldObj_7ec350();
};

static_assert(sizeof(FieldElement7b89e0) == 208);
static_assert(sizeof(FieldVector7eadb0) == 12);
static_assert(sizeof(FieldObj_7ec350) == 48);
