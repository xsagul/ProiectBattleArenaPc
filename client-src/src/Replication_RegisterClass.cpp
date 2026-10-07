// rva 0x19ccc0  Replication_RegisterClass: adds one named value to a replication table and returns its index; a name
// already in the table returns the existing index (tools/repl_names.py reads these tables from a memory image:
// +0 count, +4 float bits, +8 offsets, +0x88 names). The names are ours.
// match: 19ccc0 Register@ReplicationTable
#include "types.h"

extern "C" int __cdecl _stricmp(const char*, const char*);

struct ReplicationTable
{
    u32 count;              // +0x00
    u32 floatBits[1];       // +0x04  bit i set: value i is a float
    u32 offsets[32];        // +0x08  offset of the value inside the object
    const char* names[32];  // +0x88

    u32 Register(char* object, char* value, const char* name, bool isFloat);
};

u32 ReplicationTable::Register(char* object, char* value, const char* name, bool isFloat)
{
    for (u32 i = 0; i < count; i++)
    {
        if (_stricmp(names[i], name) == 0)
            return i;
    }
    offsets[count] = value - object;
    names[count] = name;
    u32& word = floatBits[count >> 5];
    u32 bit = 1 << (count & 31);
    if (isFloat)
        word |= bit;
    else
        word &= ~bit;
    return count++;
}
