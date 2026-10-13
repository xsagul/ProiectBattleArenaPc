// The client's narrow, locale-aware string comparator entry point.
// The CRT callee reads byte strings and selects _stricmp_l when locale state is active.
// match: 9ae430 __stricmp
extern "C" int tf72224(const char*, const char*); // rva 0xf72224

extern "C" int _stricmp(const char* left, const char* right)
{
    return tf72224(left, right);
}
