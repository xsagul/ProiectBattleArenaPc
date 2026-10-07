// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ecp_smpl.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e39da0 _ec_GFp_simple_group_init
// match: e39e60 _ec_GFp_simple_group_copy
// match: e3a040 _ec_GFp_simple_group_get_curve
// match: e3a320 _ec_GFp_simple_point_init
// match: e3a380 _ec_GFp_simple_point_finish
// match: e3a3b0 _ec_GFp_simple_point_clear_finish
// match: e3a3e0 _ec_GFp_simple_point_copy
// match: e3a440 _ec_GFp_simple_point_set_to_infinity
// match: e3a460 _ec_GFp_simple_set_Jprojective_coordinates_GFp
// match: e3a5a0 _ec_GFp_simple_get_Jprojective_coordinates_GFp
// match: e3a960 _ec_GFp_simple_add
// match: e3ae50 _ec_GFp_simple_dbl
// match: e3b240 _ec_GFp_simple_invert
// match: e3b290 _ec_GFp_simple_is_at_infinity
// match: e3b2a0 _ec_GFp_simple_is_on_curve
// match: e3b510 _ec_GFp_simple_cmp
// match: e3bea0 _ec_GFp_simple_ladder_pre
// match: e3c120 _ec_GFp_simple_ladder_step
// match: e3c5d0 _ec_GFp_simple_ladder_post
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ecp_smpl.c"
