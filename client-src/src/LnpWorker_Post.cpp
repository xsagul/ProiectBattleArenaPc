// How requests reach the transport's worker thread: each of these builds a command, moves a datagram or a message
// into it, stamps it with the clock and puts it on the worker's queue. They differ only in the command's type.
//   rva 0x2dd7c0  type 0, nothing             rva 0x2dd220  type 1, a peer id and a byte
//   rva 0x2dd2d0  type 2, a peer id, two bytes
//   rva 0x2dd710  type 3, a datagram          rva 0x2dd660  type 4, a datagram
//   rva 0x2dd5a0  type 5, the 40-byte part    rva 0x2dd4e0  type 6, a message
//   rva 0x2dd440  type 7, a message           rva 0x2dd390  type 8, the 24-byte part
// Types 5, 7 and 8 are not stamped with the clock. What each type asks the worker to do is in the worker's loop
// (rva 0x2ec560), not rebuilt yet.
// match: 2dd7c0 ?Post0@LnpWorker
// match: 2dd220 ?Post1@LnpWorker
// match: 2dd2d0 ?Post2@LnpWorker
// match: 2dd5a0 ?PostPart5@LnpWorker
// match: 2dd390 ?PostPart8@LnpWorker
// match: 2dd710 ?PostDatagram3@LnpWorker
// match: 2dd660 ?PostDatagram4@LnpWorker
// match: 2dd4e0 ?PostMessage6@LnpWorker
// match: 2dd440 ?PostMessage7@LnpWorker
#include <utility>
#include "LnpCommand.h"

void LnpWorker::PostDatagram3(LnpDatagram& datagram)
{
    LnpCommand command;
    command.type = 3;
    command.peerId = datagram.peerId;
    command.datagram = std::move(datagram);
    command.datagram.unknown38 = g_lnpClockOwner->clock->Now();
    commands.Push(command);
}

void LnpWorker::PostDatagram4(LnpDatagram& datagram)
{
    LnpCommand command;
    command.type = 4;
    command.peerId = datagram.peerId;
    command.datagram = std::move(datagram);
    command.datagram.unknown38 = g_lnpClockOwner->clock->Now();
    commands.Push(command);
}

void LnpWorker::PostMessage6(LnpMessage& message)
{
    LnpCommand command;
    command.type = 6;
    command.peerId = message.peerId;
    command.message = std::move(message);
    command.message.time = g_lnpClockOwner->clock->Now();
    commands.Push(command);
}

void LnpWorker::PostMessage7(LnpMessage& message)
{
    LnpCommand command;
    command.type = 7;
    command.peerId = message.peerId;
    command.message = std::move(message);
    commands.Push(command);
}

void LnpWorker::Post0()
{
    LnpCommand command;
    command.type = 0;
    command.peerId = 0;
    command.datagram.unknown38 = g_lnpClockOwner->clock->Now();
    commands.Push(command);
}

void LnpWorker::Post1(u64 peerId, u8 byte08)
{
    LnpCommand command;
    command.type = 1;
    command.peerId = peerId;
    command.unknown08 = byte08;
    command.datagram.unknown38 = g_lnpClockOwner->clock->Now();
    commands.Push(command);
}

void LnpWorker::Post2(u64 peerId, u8 byte08, u8 byte09)
{
    LnpCommand command;
    command.type = 2;
    command.peerId = peerId;
    command.unknown08 = byte08;
    command.unknown09 = byte09;
    command.datagram.unknown38 = g_lnpClockOwner->clock->Now();
    commands.Push(command);
}

void LnpWorker::PostPart5(const LnpCommand::Part88& part)
{
    LnpCommand command;
    command.type = 5;
    command.peerId = part.peerId;
    command.part88 = part;
    commands.Push(command);
}

void LnpWorker::PostPart8(const LnpCommand::PartE8& part)
{
    LnpCommand command;
    command.type = 8;
    command.peerId = part.peerId;
    command.partE8 = part;
    commands.Push(command);
}
