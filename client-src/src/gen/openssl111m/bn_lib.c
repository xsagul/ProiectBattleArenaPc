// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: bn_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dc7510 _BN_GENCB_set
// match: dc7530 _BN_abs_is_word
// match: dc76f0 _BN_bn2bin
// match: dc7710 _BN_bn2binpad
// match: dc7730 _BN_clear_bit
// match: dc7800 _BN_cmp
// match: dc78a0 _BN_consttime_swap
// match: dc79d0 _BN_copy
// match: dc7b70 _BN_get_flags
// match: dc7b80 _BN_get_word
// match: dc7ba0 _BN_is_bit_set
// match: dc7bd0 _BN_is_negative
// match: dc7be0 _BN_is_odd
// match: dc7c00 _BN_is_one
// match: dc7c20 _BN_is_word
// match: dc7c50 _BN_is_zero
// match: dc7c60 _BN_mask_bits
// match: dc7d10 _BN_num_bits
// match: dc7de0 _BN_num_bits_word
// match: dc7eb0 _BN_security_bits
// match: dc7f20 _BN_set_bit
// match: dc7f90 _BN_set_flags
// match: dc7fa0 _BN_set_negative
// match: dc7fd0 _BN_set_word
// match: dc8030 _BN_ucmp
// match: dc8090 _BN_with_flags
// match: dc80d0 _bn2binpad
// match: dc8260 _bn_cmp_part_words
// match: dc82f0 _bn_cmp_words
// match: dc8340 _bn_correct_top
// match: dc8470 _bn_init
// match: dc8490 _bn_wexpand
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/bn/bn_lib.c"
