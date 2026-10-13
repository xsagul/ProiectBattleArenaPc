// The one-byte steps of the packet field encoding: a field's bytes go through a chain of these (each field has its
// own chain and constants; see tools/gen_fields.py). The forms below are the ones that compile to the client's code
// (first function matched: rva 0x778ec0).
#pragma once
#include "types.h"

// the bits of a byte in reverse order
inline u8 Rev(u8 b) { return (u8)(((b * 0x0802LU & 0x22110LU) | (b * 0x8020LU & 0x88440LU)) * 0x10101LU >> 16); }
// A promoted byte follows a different compiler path when the preceding XOR is also promoted. Call with a byte
// (or an explicit u8 conversion); arithmetic is unsigned and the returned byte is the same bit permutation.
__forceinline u8 RevPromoted(u32 b) { return (u8)(((b * 0x0802U & 0x22110U) | (b * 0x8020U & 0x88440U)) * 0x10101U >> 16); }
inline u8 Rol(u8 x, int n) { return (u8)((x << n) | (x >> (8 - n))); }
inline u8 Ror(u8 x, int n) { return (u8)((x >> n) | (x << (8 - n))); }
// neighbouring bits (Swap1) or pairs of bits (Swap2) change places
inline u8 Swap1(u8 x) { return (u8)(((x >> 1) & 0x55) | ((x & 0x55) << 1)); }
inline u8 Swap2(u8 x) { return (u8)(((x >> 2) & 0x33) | ((x & 0x33) << 2)); }
