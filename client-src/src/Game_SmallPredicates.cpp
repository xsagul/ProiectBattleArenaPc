// Two of the smallest functions of the client. The names are ours.
#include "GameClient.h"

// rva 0x3630c0  Game_IsConnected: true when the byte at +0x1a8 is set and the local player slot (+0x1a7, stored by
// the 574 handler at rva 0x364850) is 1..51. Its caller at rva 0x324f50 logs "Game Server Connection Established" the
// first time this returns true. What sets +0x1a8 is not measured.
// match: 3630c0 IsConnected@GameClient
bool GameClient::IsConnected() const
{
    return flag1a8 && localSlot != 0 && localSlot < 52;
}

// rva 0x146910  C2S_ReaderStub: the reader every client->server packet class shares; it reads nothing.
// match: 146910 Read@C2SPacket
struct C2SPacket
{
    bool Read(const u8* data, u32 size);
};

bool C2SPacket::Read(const u8*, u32)
{
    return false;
}
