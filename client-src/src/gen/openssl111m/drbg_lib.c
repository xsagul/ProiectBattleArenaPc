// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: drbg_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dfe8f0 _drbg_bytes
// match: dfea20 _drbg_add
// match: dfeb10 _drbg_seed
// match: dfec20 _drbg_status
// match: dfec80 _RAND_DRBG_bytes
// match: dfef00 _RAND_DRBG_free
// match: dfef80 _RAND_DRBG_generate
// match: dff140 _RAND_DRBG_get0_public
// match: dff250 _RAND_DRBG_instantiate
// match: dff450 _RAND_DRBG_reseed
// match: dff5c0 _RAND_DRBG_set
// match: dff6d0 _do_rand_drbg_init_ossl_
// match: dff750 _drbg_delete_thread_state
// match: dff860 _drbg_setup
// match: dff910 _rand_drbg_cleanup_int
// match: dff970 _rand_drbg_new
// match: dffad0 _rand_drbg_restart
#define OPENSSL_FILE "crypto\\rand\\drbg_lib.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/rand/drbg_lib.c"
