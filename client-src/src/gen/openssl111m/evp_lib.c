// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: evp_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: c364f0 _EVP_CIPHER_CTX_set_num
// match: dc84b0 _EVP_CIPHER_CTX_block_size
// match: dc84c0 _EVP_CIPHER_CTX_buf_noconst
// match: dc84d0 _EVP_CIPHER_CTX_iv_length
// match: dc8510 _EVP_CIPHER_CTX_iv_noconst
// match: dc8530 _EVP_CIPHER_CTX_original_iv
// match: dc8540 _EVP_CIPHER_CTX_test_flags
// match: dc88b0 _EVP_CIPHER_type
// match: dc8b00 _EVP_Cipher
// match: dc8b10 _EVP_MD_CTX_clear_flags
// match: dc8b30 _EVP_MD_CTX_set_flags
// match: dc8b40 _EVP_MD_CTX_test_flags
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/evp/evp_lib.c"
