// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ec_key.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dcaee0 _EC_KEY_can_sign
// match: dcaf70 _EC_KEY_clear_flags
// match: dcb140 _EC_KEY_decoded_from_explicit_params
// match: dcb160 _EC_KEY_dup
// match: dcb2a0 _EC_KEY_key2buf
// match: dcb2e0 _EC_KEY_new_by_curve_name
// match: dcb330 _EC_KEY_oct2key
// match: dcb4e0 _EC_KEY_set_flags
// match: dcb4f0 _EC_KEY_set_group
// match: dcb530 _EC_KEY_up_ref
// match: dcb850 _ec_key_simple_generate_public_key
// match: dcb960 _ossl_ec_key_gen
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ec_key.c"
