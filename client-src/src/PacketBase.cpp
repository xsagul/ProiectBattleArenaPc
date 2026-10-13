// The packet header reader as a function of its own: the reader of the packets that carry nothing but the header
// (ids 2, 10, 18, 31, 36, 92, ... - 46 ids share it).
// match: 83fee0 ?Read@Packet@@QAE_NPAPBEPBE@Z
#include "Packet.h"

// the client's table of virtual functions names it; here its address is taken so that it is emitted
bool (Packet::*g_PacketRead)(const u8**, const u8*) = &Packet::Read;
