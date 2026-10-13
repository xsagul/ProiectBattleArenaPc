// The reader of packet id 182 (object of 24 bytes): the first packet class's reader rebuilt. After the header comes
// one byte of bits; bit 0 says the field at +0xc is on the wire (read by the function at rva 0x805e00), else the
// field is empty (the dword at +0x10 is cleared).
// match: 88d110 ?Read@Packet182@@QAE_NPAPBEPBE@Z
#include "Packet.h"

// the reader of the field's type (not rebuilt yet; it gives back a value the packet reader turns into a bool)
char Read_805e00(u32* out, const u8** cursor, const u8* end);

#pragma pack(push, 1)
struct Packet182 : Packet {
    u16 pad0a;
    u32 field0c;        // +0xc
    u32 field10;        // +0x10
    u32 field14;
    bool Read(const u8** cursor, const u8* end);
};
#pragma pack(pop)

bool Packet182::Read(const u8** cursor, const u8* end) {
    if (!Packet::Read(cursor, end)) return false;
    const u8* p = *cursor;
    if ((u32)(end - p) < 1) return false;
    *cursor = p + 1;
    if (!(*p & 1)) {
        field10 = 0;
        return true;
    }
    return Read_805e00(&field0c, cursor, end) != 0;
}
