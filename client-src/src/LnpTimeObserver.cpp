// rva 0x2e2b10: for the peer a datagram belongs to, keeps the largest value seen of "the datagram's time at +0x38
// plus this object's number at +0x30". Always answers false. What the two numbers are (a send time and an offset or a
// timeout, by the look of it) is not measured.
// match: 2e2b10 ?OnDatagram@LnpTimeObserver
#include <algorithm>
#include "LnpDatagram.h"

struct LnpPeerTimes
{
    u8 unknown00[0x10];
    double latest;      // +0x10
};

struct LnpTimeObserver
{
    u8 unknown00[0x30];
    double added30;     // +0x30

    LnpPeerTimes* Find(i64 peerId);     // rva 0x2de900
    bool OnDatagram(LnpDatagram& datagram);
};

bool LnpTimeObserver::OnDatagram(LnpDatagram& datagram)
{
    LnpPeerTimes* peer = Find(datagram.peerId);
    peer->latest = std::max(peer->latest, datagram.unknown38 + added30);
    return false;
}
