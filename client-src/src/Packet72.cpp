// The reader of packet id 72 (object of 11 bytes: the header and one byte at +0xa). After the header comes one byte
// of bits; bit 0 says the field is on the wire (ReadValidated8_79c530, gen/FieldInlineEnums.cpp), else the field
// takes its default: the value of a global byte, put through the field's in-memory chain where it lies.
// match: 884270 ?Read@Packet72@@QAE_NPAPBEPBE@Z
#include "Packet.h"
#include "FieldCodec.h"

char ReadValidated8_79c530(u8* out, const u8** cursor, const u8* end);
extern const u8 g_1b3d360[256];
extern u8 g_36f73cc;        // the default value, in clear

// A value in clear goes into the field and is encoded there. The form that gives the client's code takes both by
// reference (taking the field by pointer, or setting it in the reader's own body, gives other registers).
inline void SetField0a(u8& field, const u8& value) {
    field = value;
    for (u8* b = &field; b != &field + 1; ++b) {
        u8 x = *b;
        x = ~x; x = g_1b3d360[x]; x = Ror(x, 3); x = Ror(x, 1); x += 0x40; x ^= 0xe9; x -= 0x77; x = Rol(x, 3);
        *b = x;
    }
}

#pragma pack(push, 1)
struct Packet72 : Packet {
    u8 field0a;         // +0xa
    bool Read(const u8** cursor, const u8* end);
};
#pragma pack(pop)

bool Packet72::Read(const u8** cursor, const u8* end) {
    if (!Packet::Read(cursor, end)) return false;
    const u8* p = *cursor;
    if ((u32)(end - p) < 1) return false;
    *cursor = p + 1;
    if (!(*p & 1)) {
        SetField0a(field0a, g_36f73cc);
        return true;
    }
    return ReadValidated8_79c530(&field0a, cursor, end) != 0;
}
