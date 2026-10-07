// rva 0x2dbdc0  the transport's per-frame pump as the game sees it (called from rva 0x370810): it only hands over to
// the part at +0x1c0 of the implementation object (rva 0x2ec600).
// match: 2dbdc0 ?Update@LnpClient
#include "LnpMessage.h"

struct LnpClientImpl
{
    u8 unknown000[0x1c0];
    LnpAppObserver dispatcher;  // +0x1c0  its Update is rva 0x2ec600 (LnpAppObserver.cpp)
};

struct LnpClient
{
    LnpClientImpl* impl;        // +0x00

    void Update();
};

void LnpClient::Update()
{
    impl->dispatcher.Update();
}
