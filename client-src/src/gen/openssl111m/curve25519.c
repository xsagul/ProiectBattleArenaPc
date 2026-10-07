// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: curve25519.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: 223dd0 _fe_0
// match: e45380 _ED25519_verify
// match: e455b0 _X25519
// match: e455e0 _X25519_public_from_private
// match: e457e0 _fe_cmov
// match: e45860 _fe_cswap
// match: e45930 _fe_frombytes
// match: e45d70 _fe_invert
// match: e45ff0 _fe_mul
// match: e46920 _fe_mul121666
// match: e46bb0 _fe_neg
// match: e46c10 _fe_pow22523
// match: e46e80 _fe_sq
// match: e474a0 _fe_sq2
// match: e47b10 _fe_tobytes
// match: e47dd0 _ge_add
// match: e48140 _ge_double_scalarmult_vartime
// match: e489e0 _ge_frombytes_vartime
// match: e48d90 _ge_madd
// match: e490f0 _ge_msub
// match: e49450 _ge_p2_dbl
// match: e49710 _ge_p3_dbl
// match: e497b0 _ge_p3_to_cached
// match: e498a0 _ge_tobytes
// match: e49920 _ge_scalarmult_base
// match: e49d70 _ge_sub
// match: e4a0e0 _sc_muladd
// match: e4e1d0 _slide
// match: e4e2c0 _table_select
// match: e4e630 _x25519_sc_reduce
// match: e506c0 _x25519_scalar_mult_generic
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/curve25519.c"
