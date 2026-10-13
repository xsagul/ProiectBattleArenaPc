// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ec_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dc94f0 _EC_GROUP_check_discriminant
// match: dc9530 _EC_GROUP_clear_free
// match: dc9600 _EC_GROUP_cmp
// match: dc9850 _EC_GROUP_copy
// match: dc9a90 _EC_GROUP_dup
// match: dc9c40 _EC_GROUP_free
// match: dc9cf0 _EC_GROUP_get_cofactor
// match: dc9d30 _EC_GROUP_get_curve_GFp
// match: dc9d70 _EC_GROUP_get_degree
// match: dc9db0 _EC_GROUP_get_order
// match: dc9df0 _EC_GROUP_new
// match: dc9ee0 _EC_GROUP_order_bits
// match: dc9ef0 _EC_GROUP_set_curve_GFp
// match: dc9f30 _EC_GROUP_set_generator
// match: dca260 _EC_GROUP_set_seed
// match: dca2f0 _EC_POINT_add
// match: dca3a0 _EC_POINT_clear_free
// match: dca3e0 _EC_POINT_cmp
// match: dca470 _EC_POINT_copy
// match: dca4f0 _EC_POINT_dbl
// match: dca580 _EC_POINT_free
// match: dca5b0 _EC_POINT_get_affine_coordinates
// match: dca6b0 _EC_POINT_invert
// match: dca730 _EC_POINT_is_at_infinity
// match: dca7a0 _EC_POINT_is_on_curve
// match: dca810 _EC_POINT_make_affine
// match: dca880 _EC_POINT_mul
// match: dca8d0 _EC_POINT_new
// match: dca990 _EC_POINT_set_Jprojective_coordinates_GFp
// match: dcaa10 _EC_POINT_set_affine_coordinates
// match: dcab20 _EC_POINT_set_to_infinity
// match: dcab80 _EC_POINTs_make_affine
// match: dcac20 _EC_POINTs_mul
// match: dcad60 _EC_pre_comp_free
// match: dcada0 _ec_group_do_inverse_ord
// match: dcae70 _ec_group_simple_order_bits
// match: dcae90 _ec_point_blind_coordinates
#define OPENSSL_FILE "crypto\\ec\\ec_lib.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ec_lib.c"
