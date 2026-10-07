// rva 0x2efcc0  writes one message into a datagram's payload: a 16-bit header - payload length in the high 13 bits,
// bit 2 "same channel as the previous message", bit 1 "number is the previous one plus one", bit 0 "a fragment" -
// then only what the header does not already say: channel, number, fragment id / count / index, and the payload.
// (The same record format was measured on the wire: docs/MIGRARE_12.23.md "Transportul complet".)
// match: 2efcc0 ?Write@LnpMessage
#include "LnpMessage.h"

bool LnpMessage::Write(LnpBuffer& out, const LnpMessage& previous) const
{
    bool sameChannel = channel == previous.channel;
    bool nextNumber = number == previous.number + 1;
    bool fragment = fragmentId > 0;
    u16 header = (nextNumber ? 2 : 0) | (sameChannel ? 4 : 0) | (fragment ? 1 : 0) | (payload.size << 3);
    out.Append(&header, sizeof(header));     // as bytes; the fields below go as typed values
    if (!sameChannel)
        out.Put(channel);
    if (!nextNumber)
        out.Put(number);
    if (fragment)
    {
        out.Put(fragmentId);
        out.Put(fragmentCount);
        out.Put(fragmentIndex);
    }
    out.Append(payload.data, payload.size);
    return true;
}
