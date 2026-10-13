// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ec2_smpl.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e5a6c0 _ec_GF2m_simple_group_init
// match: e5a720 _ec_GF2m_simple_group_clear_finish
// match: e5a770 _ec_GF2m_simple_group_copy
// match: e5a840 _ec_GF2m_simple_group_set_curve
// match: e5a920 _ec_GF2m_simple_group_get_curve
// match: e5a980 _ec_GF2m_simple_group_get_degree
// match: e5a9a0 _ec_GF2m_simple_group_check_discriminant
// match: e5aa30 _ec_GF2m_simple_point_init
// match: e5aa90 _ec_GF2m_simple_point_set_affine_coordinates
// match: e5ab30 _ec_GF2m_simple_point_get_affine_coordinates
// match: e5abf0 _ec_GF2m_simple_add
// match: e5af80 _ec_GF2m_simple_dbl
// match: e5afa0 _ec_GF2m_simple_invert
// match: e5b000 _ec_GF2m_simple_is_on_curve
// match: e5b150 _ec_GF2m_simple_cmp
// match: e5b2d0 _ec_GF2m_simple_make_affine
// match: e5b3c0 _ec_GF2m_simple_points_make_affine
// match: e5b410 _ec_GF2m_simple_field_mul
// match: e5b440 _ec_GF2m_simple_field_sqr
// match: e5b480 _ec_GF2m_simple_ladder_pre
// match: e5b640 _ec_GF2m_simple_ladder_step
// match: e5b7f0 _ec_GF2m_simple_ladder_post
// match: e5bb50 _ec_GF2m_simple_points_mul
// match: e5bc90 _ec_GF2m_simple_field_inv
#define OPENSSL_FILE "crypto\\ec\\ec2_smpl.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ec2_smpl.c"
