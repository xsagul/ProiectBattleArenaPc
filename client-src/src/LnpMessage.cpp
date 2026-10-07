// rva 0x2d5c00  the copy constructor of LnpMessage, written by the compiler from the members (the payload's copy
// shares the block and adds one to its count). In a file of its own so that code copying a message calls it, as the
// client does; in the same file as its user the compiler puts it inline.
// match: 2d5c00 ??0LnpMessage@@QAE@ABU0@@Z
#include <vector>
#include "LnpMessage.h"

LnpMessage::LnpMessage(const LnpMessage& other) = default;

// rva 0x2d98c0  the move assignment of LnpMessage, also written by the compiler from the members: the payload's
// block changes owner and the source is left empty. The event queue (rva 0x2ed000) uses it.
// match: 2d98c0 ??4LnpMessage@@QAEAAU0@$$QAU0@@Z
LnpMessage& LnpMessage::operator=(LnpMessage&& other) = default;

// rva 0x2d2da0  the standard library's "destroy a range" for messages (what a std::vector<LnpMessage> runs over its
// elements): written by the compiler from <xmemory>, with the buffer's destructor inside.
// match: 2d2da0 ??$_Destroy_range@V?$allocator@ULnpMessage@@
void LnpMessageList_Clear(std::vector<LnpMessage>& list)
{
    list.clear();
}
