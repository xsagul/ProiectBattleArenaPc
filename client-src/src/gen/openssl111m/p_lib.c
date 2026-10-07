// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: p_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: db5e70 _EVP_PKEY_base_id
// match: db5eb0 _EVP_PKEY_bits
// match: db5ed0 _EVP_PKEY_cmp
// match: db5f20 _EVP_PKEY_cmp_parameters
// match: db6110 _EVP_PKEY_free_it
// match: db6410 _EVP_PKEY_get1_tls_encodedpoint
// match: db6440 _EVP_PKEY_get_default_digest_nid
// match: db6470 _EVP_PKEY_missing_parameters
// match: db66a0 _EVP_PKEY_print_public
// match: db6700 _EVP_PKEY_security_bits
// match: db6730 _EVP_PKEY_set1_DH
// match: db6830 _EVP_PKEY_set1_tls_encodedpoint
// match: db6930 _EVP_PKEY_size
// match: db6950 _EVP_PKEY_type
// match: db69a0 _EVP_PKEY_up_ref
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/evp/p_lib.c"
