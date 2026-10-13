// rva 0x2dcd40  reads one message from a datagram's payload, the reverse of Write (rva 0x2efcc0): the 16-bit header,
// then the channel, the number and the fragment fields the header says are present - the others come from the
// previous message - and the payload. False when the datagram ends too early.
// match: 2dcd40 ?Read@LnpMessage
// 282 of 360 bytes the same. The cause is known: ours keeps "previous" in a register (ebp) from the start and then has
// to load the buffer's size again; the client keeps the size in ebp and loads "previous" from its stack slot where it
// is used (once per path). With the two uses of "previous" replaced by constants ours is the client's code exactly;
// with "previous" read through a volatile pointer it is 346 of 360. What Riot wrote that keeps it out of a register
// is not found (a by-value handle, a lambda, a reference to the pointer, an inline wrapper: no).
#include "LnpMessage.h"

bool LnpMessage::Read(LnpBuffer& in, const LnpMessage& previous)
{
    u16 header ;
    const auto & local382 = in . Read ( header ) ;
    bool ok = local382 ;
    bool fragment = header & 1 ;
    header >>= 1 ;
    bool nextNumber = 1 & header ;
    header >>= 1 ;
    bool sameChannel = header & 1 ;
    header >>= 1 ;
    if ( sameChannel ) channel = previous . channel ;
    else ok &= in . Read ( channel ) ;
    if ( nextNumber ) number = previous . number + 1 ;
    else ok &= in . Read ( number ) ;
    if ( fragment ) {
        ok &= in . Read ( fragmentId ) ;
        ok &= in . Read ( fragmentCount ) ;
        ok &= in . Read ( fragmentIndex ) ;
    }
    ok &= in . ReadBuffer ( & payload , header ) ;
    text30 = "" ;
    return ok ;
}
