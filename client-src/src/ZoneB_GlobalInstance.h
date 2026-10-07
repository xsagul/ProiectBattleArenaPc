// A base class many of the client's one-of-a-kind objects have: its constructor stores the object's address in a
// global pointer of its own (rva 0x2d6ec0 does it for the object at rva 0x18d9ac8) and its virtual destructor clears
// that pointer. The base is 4 bytes (only the table pointer) and its table has one entry, the destructor. The names
// are ours.
#pragma once
#include "types.h"

template <class T>
struct GlobalInstance
{
    static T* instance;

    GlobalInstance() { instance = (T*)this; }
    virtual ~GlobalInstance() { instance = nullptr; }
};
