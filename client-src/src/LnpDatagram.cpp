// The datagram of Riot's transport: checksum, writer and reader. They are one file here because they were one file
// for Riot's compiler too: alone in a file, Write (or Read) gets the map's operator[] put inline, which the client
// does not have; with both in the file it stays a call, as in the client.

#include "LnpDatagram.h"

// rva 0x2de720  LNP_Crc32: the checksum of one datagram of Riot's transport (measured on 83 captured datagrams,
// tools/lnp.py; docs/MIGRARE_12.23.md "Transportul complet"). Field offsets are the ones the client's code uses;
// the names are ours.
// Compiled with cl 19.32.31328 -O2 this is byte-identical to the client's function (tools/match_func.py): 474 bytes.
// Identical bytes prove the compiler and the options, not the spelling: other spellings may compile to the same bytes.
// match: 2de720 Crc@LnpDatagram
extern "C" __declspec(dllimport) unsigned long __stdcall htonl(unsigned long);

// The running checksum. Kept as an object: with the value in a plain local variable the same compiler writes the last
// loop differently from the client (464 bytes instead of 474).
struct LnpCrc
{
    u32 value;

    LnpCrc() : value(0xffffffff) {}

    void Add(u8 b)
    {
        value = ((value << 8) | b) ^ g_lnpCrcTable[value >> 24];
    }
};

u32 LnpDatagram::Crc() const
{
    LnpCrc crc;
    for (u32 i = 0; i < sizeof(number); i++)
        crc.Add(((const u8*)&number)[i]);
    for (u32 i = 0; i < sizeof(peerId); i++)
        crc.Add(((const u8*)&peerId)[i]);
    for (u32 i = 0; i < sizeof(u64); i++)
        crc.Add((u8)(ack.mask.to_ullong() >> (8 * i)));
    // The counter is set up before the pointer and the length: declared after them, one byte differs
    // (movzx eax, [esi+ebx] instead of [ebx+esi]).
    u32 i = 0;
    const u8* data = payload.data;
    u32 n = payload.size;
    for (; i < n; i++)
        crc.Add(data[i]);
    return htonl(~crc.value);
}

// rva 0x2efe50  LNP_WriteDatagram: appends the datagram to a buffer - number, checksum, one flag byte, the
// acknowledgement mask when the number is negative, the payload - and, when encryption is on, encrypts what it
// appended: cipher, bytes reversed, cipher again. False when there is no cipher for the peer.
// match: 2efe50 ?Write@LnpDatagram
// Not identical yet: 437 bytes like the client's, 235 the same. What already matches and what does not:
// - every append goes through the buffer's generic byte append (LnpBuffer.h) - with a typed "*(T*)p = v; size +=
//   sizeof(T)" the same compiler writes "add word ptr [size], n" and reloads, the client keeps the size in a register;
// - the flag byte is passed by value, the acknowledgement mask is copied before the buffer grows;
// - the encryption is an inlined function taking the peer id by value (the client keeps the copy in the stack slot
//   that held "this");
// - still different: the number is copied with "mov ax, [..]" in the client (ours: movzx), and after the mask is
//   appended the client keeps the new size in a register where ours reloads it.
//
// The std::map code this file instantiates from MSVC 14.32's own headers is identical to the client's copies:
// match: 2d9f00 ??A?$map@_JPAULnpCipher
// match: 2d3f40 ??$_Find_lower_bound@_J@?$_Tree
// match: 124b60 ?_Insert_node@
// match: 125680 ?_Throw_tree_length_error@
bool LnpDatagram::Write(LnpBuffer& out, LnpCrypto& crypto)
{
    u32 crc = Crc();
    u8 flag = flag40;
    u16 start = out.size;
    out.Append(number);
    out.Append(crc);
    out.AppendByte(flag != 0);
    if (number < 0)
    {
        out.Append(ack.mask.to_ullong());
    }
    out.Append(payload.data, payload.size);
    u16 length = out.size - start;
    LnpBytes written = { length, out.data + start };
    return crypto.Encrypt(peerId, written);
}

// rva 0x2dceb0  LNP_ReadDatagram: the reverse of Write - decrypts what is left of the buffer in place (when encryption
// is on), reads number, checksum and flag byte, the acknowledgement mask when the number is negative, takes the rest as
// payload and checks the checksum. False when anything was missing, there was no cipher, or the checksum differs.
// match: 2dceb0 ?Read@LnpDatagram
bool LnpDatagram::Read(LnpBuffer& in, LnpCrypto& crypto)
{
    u32 crc = 0;
    u8 flag = 0;
    LnpBytes rest = { (u16)(in.size - in.position), in.data + in.position };
    bool ok = crypto.Decrypt(peerId, rest);
    ok &= in.Read(number);
    ok &= in.Read(crc);
    ok &= in.Read(flag);
    flag40 = flag & 1;
    if (number < 0)
    {
        u64 mask = 0;
        ok &= in.Read(mask);
        Ack read;
        read.number = -number;
        read.mask = mask;
        ack = read;
    }
    bool complete = in.ReadBuffer(&payload, in.size - in.position) & ok;
    return crc == Crc() ? complete : false;
}
