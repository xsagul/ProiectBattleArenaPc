// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ec_ameth.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e1e3f0 _eckey_pub_encode
// match: e1e4f0 _eckey_pub_decode
// match: e1e5e0 _eckey_pub_cmp
// match: e1e650 _eckey_priv_decode
// match: e1e730 _eckey_priv_encode
// match: e1e8e0 _ec_bits
// match: e1e900 _ec_security_bits
// match: e1e960 _ec_missing_parameters
// match: e1e980 _ec_copy_parameters
// match: e1e9f0 _ec_cmp_parameters
// match: e1ea40 _eckey_param_decode
// match: e1eb10 _old_ec_priv_decode
// match: e1eb80 _ec_pkey_ctrl
// match: e1edb0 _ec_pkey_check
// match: e1ee00 _ec_pkey_param_check
// match: e1ee40 _do_EC_KEY_print
// match: e1f050 _ecdh_cms_decrypt
// match: e1f260 _ecdh_cms_encrypt
// match: e1f610 _ecdh_cms_set_shared_info
// match: e1f890 _eckey_param2type
// match: e1f9a0 _eckey_type2param
#define OPENSSL_FILE "crypto\\ec\\ec_ameth.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ec_ameth.c"
