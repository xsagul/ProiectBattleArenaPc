// A datagram's constructor, destructor and move assignment. None is written by hand: the compiler makes them from the
// members and their initial values (LnpDatagram.h), and they come out as the client's functions - which is what shows
// the whole 0x78-byte layout of a datagram and what each member starts as.
//   rva 0x2d6700  constructor: everything zero, except the acknowledgement mask (all bits set) and the address (its
//                 last member 1);
//   rva 0x2d8ef0  destructor: gives up the payload's block, frees the vector at +0x28;
//   rva 0x2d9a40  move assignment: plain members copied, the vector and the payload change owner.
// match: 2d6700 ??0LnpDatagram@@QAE@XZ
// match: 2d8ef0 ??1LnpDatagram@@QAE@XZ
// match: 2d9a40 ??4LnpDatagram@@QAEAAU0@$$QAU0@@Z
// The vector's clean-up the move assignment calls is the standard library's, for 16-byte elements:
// match: 2f2bb0 ?_Tidy@?$vector@UAck@LnpDatagram@@
#include "LnpDatagram.h"

LnpDatagram::LnpDatagram() = default;

LnpDatagram::~LnpDatagram() = default;

LnpDatagram& LnpDatagram::operator=(LnpDatagram&& other) = default;
