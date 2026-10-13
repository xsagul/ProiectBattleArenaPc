// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: stack.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dcd070 _OPENSSL_sk_deep_copy
// match: dcd190 _OPENSSL_sk_delete
// match: dcd1c0 _OPENSSL_sk_delete_ptr
// match: dcd210 _OPENSSL_sk_dup
// match: dcd2d0 _OPENSSL_sk_find
// match: dcd360 _OPENSSL_sk_free
// match: dcd390 _OPENSSL_sk_insert
// match: dcd410 _OPENSSL_sk_is_sorted
// match: dcd430 _OPENSSL_sk_new
// match: dcd460 _OPENSSL_sk_new_null
// match: dcd490 _OPENSSL_sk_new_reserve
// match: dcd500 _OPENSSL_sk_num
// match: dcd510 _OPENSSL_sk_pop
// match: dcd530 _OPENSSL_sk_pop_free
// match: dcd590 _OPENSSL_sk_push
// match: dcd5b0 _OPENSSL_sk_reserve
// match: dcd5e0 _OPENSSL_sk_set
// match: dcd620 _OPENSSL_sk_set_cmp_func
// match: dcd640 _OPENSSL_sk_shift
// match: dcd680 _OPENSSL_sk_sort
// match: dcd6c0 _OPENSSL_sk_value
// match: dcd6e0 _internal_delete
// match: dcd720 _sk_reserve
#define OPENSSL_FILE "crypto\\stack\\stack.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/stack/stack.c"
