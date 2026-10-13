// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ecp_mont.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e3ca30 _ec_GFp_mont_group_init
// match: e3ca50 _ec_GFp_mont_group_set_curve
// match: e3cbd0 _ec_GFp_mont_group_copy
// match: e3cc60 _ec_GFp_mont_field_mul
// match: e3ccb0 _ec_GFp_mont_field_sqr
// match: e3cd00 _ec_GFp_mont_field_inv
// match: e3cdf0 _ec_GFp_mont_field_encode
// match: e3ce30 _ec_GFp_mont_field_decode
// match: e3ce70 _ec_GFp_mont_field_set_to_one
#define OPENSSL_FILE "crypto\\ec\\ecp_mont.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ecp_mont.c"
