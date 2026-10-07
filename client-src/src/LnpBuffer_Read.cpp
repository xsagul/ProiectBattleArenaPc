// Kept apart from LnpBuffer.cpp: in one file with Reserve, the compiler puts Reserve inline here (214 bytes), and the
// client calls it. Which of Riot's files held what is not known; this only reproduces "Reserve is not inlined".
#include "LnpBuffer.h"

// rva 0x2ed2f0  LnpBuffer::ReadBuffer: moves the next count bytes from this buffer to the end of another one. False,
// with nothing read, when fewer than count bytes are left.
// match: 2ed2f0 ?ReadBuffer@LnpBuffer
bool LnpBuffer::ReadBuffer(LnpBuffer* to, u16 count)
{
    if (count <= (u16)(size - position))
    {
        to->Append(data + position, count);
        position += count;
        return true;
    }
    return false;
}

// rva 0x2d2d60  LnpBuffer::Append(bytes, count), defined in the header; taking its address here makes the compiler
// write it out as a function, as the client has it.
// match: 2d2d60 ?Append@LnpBuffer@@QAE_NPBXG@Z
bool (LnpBuffer::*g_lnpBufferAppend)(const void*, u16) = &LnpBuffer::Append;
