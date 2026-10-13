// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ocb128.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dfd840 _CRYPTO_ocb128_aad
// match: dfda40 _CRYPTO_ocb128_cleanup
// match: dfda80 _CRYPTO_ocb128_copy_ctx
// match: dfdb20 _CRYPTO_ocb128_decrypt
// match: dfddd0 _CRYPTO_ocb128_encrypt
// match: dfe0f0 _CRYPTO_ocb128_init
// match: dfe240 _CRYPTO_ocb128_setiv
// match: dfe430 _ocb_block_lshift
// match: dfe4c0 _ocb_block_xor
// match: dfe5e0 _ocb_finish
// match: dfe6f0 _ocb_lookup_l
#define OPENSSL_FILE "crypto\\modes\\ocb128.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/modes/ocb128.c"
