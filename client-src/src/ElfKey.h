// A 4-byte key made from a name with the ELF (PJW) hash of its lower-case letters, the hash of the old inibin /
// troybin files (name ours). Its globals are made at start-up from a std::string of the literal (rva 0x6b150 and the
// others in gen/ElfKeys.cpp); the destructor is empty but written (each global gets an atexit callback that is `ret`).
#pragma once
#include "types.h"
#include <string>

u32 HashElf(const char* s);     // rva 0x120eb0

struct ElfKey
{
    u32 value;

    ElfKey(const std::string& name) : value(HashElf(name.c_str())) {}
    ~ElfKey() {}
};
