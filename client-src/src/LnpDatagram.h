// One datagram of Riot's transport in memory, before encryption (wire format measured on captured datagrams:
// tools/lnp.py, docs/MIGRARE_12.23.md "Transportul complet"). Offsets are the ones the client's code uses; the names
// are ours.
#pragma once
#include <bitset>
#include <map>
#include <vector>
#include "LnpBuffer.h"

typedef long long i64;

extern const u32 g_lnpCrcTable[256];    // rva 0x1578bb0 (.rdata), polynomial 0x04C11DB7

struct LnpCipher
{
    void Crypt(u8* data, u32 size, int mode);   // rva 0x9c4f80 (Blowfish, CFB); library code, not rebuilt here
    void Decrypt(u8* data, u32 size, int mode); // rva 0x9c3340
};

// The bytes handed to the cipher: a length and where they start. As a record (and with the length first) and not as
// two arguments: only so does the same compiler address the bytes in the reversal loop as [start + index], like the
// client, and take the registers the client takes.
struct LnpBytes
{
    u16 size;
    u8* data;
};

struct LnpCrypto
{
    bool enabled;                           // +0x00  [Network] EnableEncryption
    std::map<i64, LnpCipher*> ciphers;      // +0x04  by peer id

    // Encrypts in place when encryption is on: cipher, bytes reversed, cipher again. False: no cipher for the peer.
    bool Encrypt(i64 peer, LnpBytes bytes)
    {
        if (enabled)
        {
            if (!ciphers.count(peer))
                return false;
            LnpCipher* cipher = ciphers[peer];
            cipher->Crypt(bytes.data, bytes.size, 2);
            for (int i = 0, j = bytes.size - 1; i < j; i++, j--)
            {
                u8 b = bytes.data[i];
                bytes.data[i] = bytes.data[j];
                bytes.data[j] = b;
            }
            cipher->Crypt(bytes.data, bytes.size, 2);
        }
        return true;
    }

    // The same steps with the cipher's other direction.
    bool Decrypt(i64 peer, LnpBytes bytes)
    {
        if (!enabled)
            return true;
        if (!ciphers.count(peer))
            return false;
        LnpCipher* cipher = ciphers[peer];
        cipher->Decrypt(bytes.data, bytes.size, 2);
        for (int i = 0, j = bytes.size - 1; i < j; i++, j--)
        {
            u8 b = bytes.data[i];
            bytes.data[i] = bytes.data[j];
            bytes.data[j] = b;
        }
        cipher->Decrypt(bytes.data, bytes.size, 2);
        return true;
    }
};

// A network address as the transport keeps it: 28 bytes, copied as a block (the size of a sockaddr_in6; not looked
// into further). A new one has 0, 0 and 1 in its last three members and then its sixteen host bytes cleared by the
// constructor's body: that order is what the map's operator[] for peer entries (rva 0x2da4d0) shows.
struct LnpAddress
{
    u8 host[16];
    u16 unknown10 = 0;
    u32 unknown14 = 0;
    u32 unknown18 = 1;

    LnpAddress()
    {
        memset(host, 0, sizeof(host));
    }
};

struct LnpDatagram
{
    i64 peerId = 0;         // +0x00
    short number = 0;       // +0x08  negative: an acknowledgement, which also carries ack.mask
    u8 unknown0a = 0;
    u32 unknown0c = 0;
    u32 unknown10 = 0;
    struct Ack
    {
        short number;       // +0x18  the acknowledged packet number (minus this datagram's own number)
        // A bitset, not a plain 64-bit number: the reader's temporary record gets these eight bytes zeroed as a block
        // before they are assigned, as the client's code does; with a plain number the same compiler drops that store.
        std::bitset<64> mask;   // +0x20

        Ack() : number(0) {}
        Ack(short number, const std::bitset<64>& mask) : number(number), mask(mask) {}
    } ack = Ack(0, std::bitset<64>(0xffffffffffffffff));    // a new datagram: number 0, every bit of the mask set
    // Three pointers that the move assignment (rva 0x2d9a40) treats as a std::vector of 16-byte elements; a list of
    // acknowledgement records by the size, which is all that is known of it.
    std::vector<Ack> acks;  // +0x28
    double unknown38 = 0;   // +0x38  a time; rva 0x2e2b10 keeps the latest per peer
    u8 flag40 = 0;          // +0x40  written as one byte, 0 or 1: the payload is compressed (rva 0x2e2a70 sets it)
    double unknown48 = 0;   // +0x48  a datagram is compressed only while this is not above zero
    LnpBuffer payload;      // +0x50
    LnpAddress address;     // +0x5c  where it came from

    // All three are written by the compiler from the members; they are declared here and defined in
    // LnpDatagram_Life.cpp so that they are functions of their own, as in the client.
    LnpDatagram();                                  // rva 0x2d6700
    ~LnpDatagram();                                 // rva 0x2d8ef0
    LnpDatagram& operator=(LnpDatagram&& other);    // rva 0x2d9a40

    u32 Crc() const;
    bool Write(LnpBuffer& out, LnpCrypto& crypto);
    bool Read(LnpBuffer& in, LnpCrypto& crypto);
};
