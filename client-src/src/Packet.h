// The start of every packet object of the client, and the reader of the 6 bytes every packet body starts with
// (rva 0x83fee0; 46 packet ids have nothing else and use it as their whole reader). A packet class's own reader has
// this one inside it (inline), then one or more bytes of bits that say, field by field, whether the field is read off
// the wire or takes its default (first one rebuilt: Packet182.cpp, rva 0x88d110).
//
// Names are ours. The object really starts with a table of virtual functions (reader at slot 1); here it is a plain
// pointer until the other slots are rebuilt.
#pragma once
#include "types.h"

#pragma pack(push, 1)
struct Packet {
    void* vtable;
    u16 header4;        // +4
    u32 header6;        // +6
    inline bool Read(const u8** cursor, const u8* end);
};
#pragma pack(pop)

inline bool Packet::Read(const u8** cursor, const u8* end) {
    const u8* p = *cursor;
    if ((u32)(end - p) < 6) return false;
    header4 = *(const u16*)p;
    header6 = *(const u32*)(p + 2);
    *cursor += 6;
    return true;
}
