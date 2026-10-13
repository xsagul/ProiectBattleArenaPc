// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: a_int.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e07220 _ASN1_ENUMERATED_get
// match: e072b0 _ASN1_INTEGER_cmp
// match: e07300 _ASN1_INTEGER_get
// match: e07360 _ASN1_INTEGER_get_uint64
// match: e07400 _ASN1_INTEGER_set
// match: e07460 _asn1_get_uint64
// match: e074f0 _asn1_string_get_int64
// match: e07630 _asn1_string_set_int64
// match: e076e0 _asn1_string_to_bn
// match: e07770 _bn_to_asn1_string
// match: e07870 _c2i_ASN1_INTEGER
// match: e07940 _c2i_ibuf
// match: e07ac0 _c2i_uint64_int
// match: e07b70 _i2c_ASN1_INTEGER
// match: e07b90 _i2c_ibuf
// match: e07cd0 _i2c_uint64_int
// match: e07d40 _twos_complement
#define OPENSSL_FILE "crypto\\asn1\\a_int.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/asn1/a_int.c"
