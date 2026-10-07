// rva 0x2ed120 (commands) and 0x2ed000 (events): LnpQueue::Push, see LnpQueue.h.
// Needs C++17: the blocks are aligned to 64 bytes and are allocated with the aligned operator new (two arguments in
// the client's code), which older language modes do not use.
// match: 2ed120 ?Push@?$LnpQueue@ULnpCommand@@
// match: 2ed000 ?Push@?$LnpQueue@ULnpEvent@@
// The blocks' constructors (each makes its 244 or 734 elements) are written by the compiler:
// match: 2d6a10 ??0Block@?$LnpQueue@ULnpCommand@@
// match: 2d69b0 ??0Block@?$LnpQueue@ULnpEvent@@
#include <utility>
#include "LnpCommand.h"
#include "LnpQueue.h"

template <class T, int Count>
void LnpQueue<T, Count>::Push(T& value)
{
    static thread_local Block* block = new Block();
    Node* node = &block->nodes[block->taken++];
    node->block = block;
    if (block->taken == Count)
        block = new Block();
    node->value = std::move(value);
    Node* previous = last.exchange(node);
    previous->next.store(node, std::memory_order_release);
    wake.notify_one();
}

template struct LnpQueue<LnpCommand, 244>;
template struct LnpQueue<LnpEvent, 734>;
