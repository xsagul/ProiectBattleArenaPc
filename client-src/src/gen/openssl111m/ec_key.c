// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ec_key.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dcaee0 _EC_KEY_can_sign
// match: dcaf00 _EC_KEY_check_key
// match: dcaf70 _EC_KEY_clear_flags
// match: dcaf80 _EC_KEY_copy
// match: dcb140 _EC_KEY_decoded_from_explicit_params
// match: dcb160 _EC_KEY_dup
// match: dcb1a0 _EC_KEY_free
// match: dcb240 _EC_KEY_generate_key
// match: dcb2a0 _EC_KEY_key2buf
// match: dcb2e0 _EC_KEY_new_by_curve_name
// match: dcb330 _EC_KEY_oct2key
// match: dcb3a0 _EC_KEY_oct2priv
// match: dcb3e0 _EC_KEY_priv2buf
// match: dcb4e0 _EC_KEY_set_flags
// match: dcb4f0 _EC_KEY_set_group
// match: dcb530 _EC_KEY_up_ref
// match: dcb550 _ec_key_simple_check_key
// match: dcb760 _ec_key_simple_generate_key
// match: dcb850 _ec_key_simple_generate_public_key
// match: dcb870 _ec_key_simple_oct2priv
// match: dcb8f0 _ec_key_simple_priv2oct
// match: dcb960 _ossl_ec_key_gen
#define OPENSSL_FILE "crypto\\ec\\ec_key.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ec_key.c"
