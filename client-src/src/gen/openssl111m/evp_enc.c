// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: evp_enc.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: db9350 _EVP_CIPHER_CTX_copy
// match: db9470 _EVP_CIPHER_CTX_ctrl
// match: db9500 _EVP_CIPHER_CTX_free
// match: db9580 _EVP_CIPHER_CTX_new
// match: db95a0 _EVP_CIPHER_CTX_rand_key
// match: db95e0 _EVP_CIPHER_CTX_reset
// match: db9650 _EVP_CIPHER_CTX_set_key_length
// match: db96d0 _EVP_CipherInit_ex
// match: db9aa0 _EVP_DecryptFinal_ex
// match: db9c20 _EVP_DecryptInit
// match: db9cd0 _EVP_DecryptUpdate
// match: db9f00 _EVP_EncryptFinal_ex
// match: dba020 _EVP_EncryptUpdate
// match: dba060 _evp_EncryptDecryptUpdate
// match: dba310 _is_partially_overlapping
#define OPENSSL_FILE "crypto\\evp\\evp_enc.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/evp/evp_enc.c"
