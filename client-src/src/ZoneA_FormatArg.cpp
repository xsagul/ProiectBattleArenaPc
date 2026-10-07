// Six small functions, one per value type, of a printf-style text formatter. Each takes the formatter's state,
// writes into it which conversion letters the value's type accepts (and, for the 64-bit integers, the length modifier
// "ll"), and hands the value itself to the variadic function at rva 0x97d0d0 together with two words of the state.
// The state's layout is only what these six use; the names are ours.
//   rva 0x2d14a0  u8      "ucdioxX"            rva 0x2d14d0  u16     "ucdioxX"
//   rva 0x2d1500  float   "gaefGAEF"           rva 0x2d1530  double  "gaefGAEF"
//   rva 0x2d1560  i64     "dciouxX" + "ll"     rva 0x2d1590  u64     "ucdioxX" + "ll"
// match: 2d14a0 ??$FormatArg_Put@E@@YAXPAUFormatState@@@Z
// match: 2d14d0 ??$FormatArg_Put@G@@YAXPAUFormatState@@@Z
// match: 2d1500 ??$FormatArg_Put@M@@YAXPAUFormatState@@@Z
// match: 2d1530 ??$FormatArg_Put@N@@YAXPAUFormatState@@@Z
// match: 2d1560 ??$FormatArg_Put@_J@@YAXPAUFormatState@@@Z
// match: 2d1590 ??$FormatArg_Put@_K@@YAXPAUFormatState@@@Z
#include "types.h"

struct FormatState
{
    u8 unknown00[0x14];
    const char* letters;        // +0x14  the conversion letters this value may be printed with
    u8 unknown18[4];
    const char* lengthModifier; // +0x1c
    const void* value;          // +0x20  where the value to print is
    u32 unknown24;
    u32 unknown28;
};

void FormatState_Print(FormatState* state, u32 a, u32 b, ...);    // rva 0x97d0d0

template <class T>
void FormatArg_Put(FormatState* state);

template <>
void FormatArg_Put<u8>(FormatState* state)
{
    const u8* value = (const u8*)state->value;
    state->letters = "ucdioxX";
    FormatState_Print(state, state->unknown24, state->unknown28, *value);
}

template <>
void FormatArg_Put<u16>(FormatState* state)
{
    const u16* value = (const u16*)state->value;
    state->letters = "ucdioxX";
    FormatState_Print(state, state->unknown24, state->unknown28, *value);
}

template <>
void FormatArg_Put<float>(FormatState* state)
{
    const float* value = (const float*)state->value;
    state->letters = "gaefGAEF";
    FormatState_Print(state, state->unknown24, state->unknown28, *value);
}

template <>
void FormatArg_Put<double>(FormatState* state)
{
    const double* value = (const double*)state->value;
    state->letters = "gaefGAEF";
    FormatState_Print(state, state->unknown24, state->unknown28, *value);
}

template <>
void FormatArg_Put<long long>(FormatState* state)
{
    const long long* value = (const long long*)state->value;
    state->letters = "dciouxX";
    state->lengthModifier = "ll";
    FormatState_Print(state, state->unknown24, state->unknown28, *value);
}

template <>
void FormatArg_Put<u64>(FormatState* state)
{
    const u64* value = (const u64*)state->value;
    state->letters = "ucdioxX";
    state->lengthModifier = "ll";
    FormatState_Print(state, state->unknown24, state->unknown28, *value);
}
