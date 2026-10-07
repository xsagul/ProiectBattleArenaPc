// The queue the transport's threads talk through (events to the game at rva 0x2ed000, commands to the worker at rva
// 0x2ed120 - the same code for two element types). Any thread may push without a lock: each thread takes elements
// from a 64 KiB block of its own, links the new one behind the last with one atomic exchange and wakes the reader.
// Layout and sizes are the client's; the names are ours.
#pragma once
#include <atomic>
#include <condition_variable>
#include <mutex>
#include <utility>
#include "types.h"

template <class T, int Count>
struct LnpQueue
{
    struct Block;

    struct Node
    {
        T value;
        Block* block = nullptr;     // the block it was taken from
        std::atomic<Node*> next{ nullptr };
    };

    struct Block
    {
        Node nodes[Count];
        alignas(64) u32 taken = 0;      // how many of the nodes have been handed out
        alignas(64) u32 released = 0;   // how many of them have been read and are done with
    };

    std::mutex mutex;                   // +0x00
    std::condition_variable wake;       // +0x30
    alignas(64) u8 unknown80[0x40];
    alignas(64) Node* first;                // +0xc0   the node read last; the next one to read hangs behind it
    alignas(64) std::atomic<Node*> last;    // +0x100

    void Push(T& value);

    // Takes the oldest element, if there is one. Only one thread reads. A block is freed when its last node has been
    // read. (In the client this is inside its users, e.g. rva 0x2ec600.)
    bool Pop(T& value)
    {
        Node* read = first;
        Node* next = read->next.load(std::memory_order_acquire);
        if (!next)
            return false;
        value = std::move(next->value);
        first = next;
        Block* block = read->block;
        if (block && ++block->released == Count)
            delete block;
        return true;
    }
};
