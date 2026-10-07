// The part of the transport that knows where each peer is. Per peer it keeps an entry in a map at +0x198:
//   rva 0x2df590  event 0 for a peer: sets the entry's flag at +0x31;
//   rva 0x2df9d0  event 1 for a peer: clears it;
//   rva 0x2e2780  a datagram from a peer: remembers the address it came from, unless one of the entry's two flags is
//                 set; answers 3 for a peer without an entry, else 0.
// (So event 0 and event 1 switch a peer on and off; "connected" and "disconnected" by the look of it.)
// match: 2df590 ?OnEvent0@LnpAddressObserver
// match: 2df9d0 ?OnEvent1@LnpAddressObserver
// match: 2e2780 ?OnDatagram@LnpAddressObserver
// The map's operator[], written by the compiler from <map> and the entry's initial values, is the client's:
// match: 2da4d0 ??A?$map@_JULnpPeerEntry@@
#include "LnpDatagram.h"

struct LnpPeerEntry
{
    LnpAddress address;     // +0x00
    u64 unknown20 = 0;
    u64 unknown28 = 0;
    bool flag30 = false;    // +0x30
    bool flag31 = false;    // +0x31  set by event 0, cleared by event 1
};

struct LnpAddressObserver
{
    u8 unknown000[0x198];
    std::map<i64, LnpPeerEntry> peers;  // +0x198

    bool OnEvent0(i64 peerId, u8 byte10, u32 unused1, u32 unused2);
    bool OnEvent1(i64 peerId, u8 byte10, u32 unused1, u32 unused2, u8 byte11);
    u8 OnDatagram(LnpDatagram& datagram);
};

bool LnpAddressObserver::OnEvent0(i64 peerId, u8, u32, u32)
{
    peers[peerId].flag31 = true;
    return false;
}

bool LnpAddressObserver::OnEvent1(i64 peerId, u8, u32, u32, u8)
{
    peers[peerId].flag31 = false;
    return false;
}

u8 LnpAddressObserver::OnDatagram(LnpDatagram& datagram)
{
    if (!peers.count(datagram.peerId))
        return 3;
    LnpPeerEntry& entry = peers[datagram.peerId];
    if (!entry.flag30 && !entry.flag31)
        entry.address = datagram.address;
    return 0;
}
