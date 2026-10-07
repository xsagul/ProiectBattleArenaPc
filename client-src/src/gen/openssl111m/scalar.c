// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: scalar.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e71c40 _curve448_scalar_add
// match: e71da0 _curve448_scalar_decode_long
// match: e71fd0 _curve448_scalar_encode
// match: e72010 _curve448_scalar_halve
// match: e72130 _curve448_scalar_mul
// match: e72160 _curve448_scalar_sub
// match: e72180 _sc_montmul
// match: e722f0 _sc_subx
// match: e72400 _scalar_decode_short
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/curve448/scalar.c"
