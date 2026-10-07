// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: curve448.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e50e10 _X448
// match: e50e30 _x448_derive_public_key
// match: e51010 _add_niels_to_pt
// match: e511b0 _curve448_base_double_scalarmul_non_secret
// match: e51690 _curve448_point_decode_like_eddsa_and_mul_by_ratio
// match: e51940 _curve448_point_eq
// match: e519b0 _curve448_point_mul_by_ratio_and_encode_like_eddsa
// match: e51c70 _curve448_precomputed_scalarmul
// match: e52080 _gf_cond_neg
// match: e52100 _gf_cond_swap
// match: e522d0 _niels_to_pt
// match: e52340 _pniels_to_pt
// match: e523d0 _point_double_internal
// match: e52670 _pt_to_pniels
// match: e526d0 _recode_wnaf
// match: e52890 _sub_niels_from_pt
// match: e52a30 _x448_int
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/curve448/curve448.c"
