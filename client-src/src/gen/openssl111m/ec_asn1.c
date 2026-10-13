// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ec_asn1.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e04ef0 _ECDSA_SIG_set0
// match: e05210 _ECDSA_SIG_free
// match: e05240 _ECDSA_SIG_new
// match: e05280 _ECDSA_size
// match: e05300 _EC_GROUP_get_basis_type
// match: e05350 _EC_GROUP_get_ecparameters
// match: e05510 _EC_GROUP_get_ecpkparameters
// match: e05620 _EC_GROUP_new_from_ecparameters
// match: e05cd0 _EC_GROUP_new_from_ecpkparameters
// match: e05dd0 _d2i_ECParameters
// match: e05f30 _d2i_ECPrivateKey
// match: e06120 _ec_asn1_group2curve
// match: e06350 _ec_asn1_group2fieldid
// match: e066a0 _i2d_ECParameters
// match: e06760 _i2d_ECPrivateKey
// match: e06930 _i2o_ECPublicKey
// match: e06a40 _o2i_ECPublicKey
#define OPENSSL_FILE "crypto\\ec\\ec_asn1.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ec_asn1.c"
