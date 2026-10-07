// rva 0x2e0cd0  LNP_AppQueueObserver: a message with a payload is put on the application's queue as an event of
// type 2; the per-frame pump (rva 0x370810 -> 0x2dbdc0) takes it from there. Always answers false.
// match: 2e0cd0 ?OnMessage@LnpAppObserver
#include "LnpMessage.h"

bool LnpAppObserver::OnMessage(const LnpMessage& message)
{
    if (message.payload.size != 0)
    {
        LnpEvent event = { 2, message.peerId, 0, 0, message };
        events.Push(event);
    }
    return false;
}

// rva 0x2df4e0 and 0x2df810: the same for the two other kinds of event, 0 and 1, which carry a peer id and one or
// two bytes instead of a message (what the kinds and the bytes mean is not measured yet).
// match: 2df4e0 ?OnEvent0@LnpAppObserver
bool LnpAppObserver::OnEvent0(u64 peerId, u8 byte10, u32, u32)
{
    LnpEvent event = { 0, peerId, byte10, 0 };
    events.Push(event);
    return false;
}

// match: 2df810 ?OnEvent1@LnpAppObserver
bool LnpAppObserver::OnEvent1(u64 peerId, u8 byte10, u32, u32, u8 byte11)
{
    LnpEvent event = { 1, peerId, byte10, byte11 };
    events.Push(event);
    return false;
}

// rva 0x2ec600: the game thread's side, once per frame (called through rva 0x2dbdc0). Every event waiting on the
// queue goes to a callback: a message (kind 2) to onMessage with its peer, channel, time and bytes; the two other
// kinds to onPeer with the peer, whether it is kind 0, and the event's two bytes.
// match: 2ec600 ?Update@LnpAppObserver
// Not identical yet: 509 bytes against the client's 511, the same instructions (the queue's Pop inline, the block
// freed after its last node, both callbacks called through std::function with copies of their arguments) but another
// stack layout: the client's frame is 8 bytes bigger (0x88), keeps the three 8-byte argument copies above the event
// and gives the channel copy a slot of its own; ours puts the event on top and shares that slot. Loop shapes (while /
// for / switch / continue) and 26 option sets do not change it.
void LnpAppObserver::Update()
{
    LnpEvent event;
    while (events.Pop(event))
    {
        if (event.type == 2)
        {
            if (onMessage)
                onMessage(event.message.peerId, event.message.channel, event.message.time, event.message.payload.data,
                          event.message.payload.size);
        }
        else
        {
            if (onPeer)
                onPeer(event.peerId, event.type == 0, event.unknown10, event.unknown11);
        }
    }
}
