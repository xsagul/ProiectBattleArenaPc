// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: x509_vfy.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d7f1b0 _X509_STORE_CTX_get_check_revocation
// match: d89ec0 _X509_STORE_CTX_get_lookup_crls
// match: d8a0b0 _X509_STORE_CTX_get0_chain
// match: dbec80 _X509_STORE_CTX_set_verify_cb
// match: dc1e70 _X509_STORE_CTX_cleanup
// match: dc1f20 _X509_STORE_CTX_get1_chain
// match: dc1f40 _X509_STORE_CTX_get_error
// match: dc2350 _X509_STORE_CTX_set_default
// match: dc2390 _X509_STORE_CTX_set_flags
// match: dc23d0 _X509_cmp_time
// match: dc25b0 _X509_gmtime_adj
// match: dc27a0 _augment_stack
// match: dc31b0 _check_auth_level
// match: dc3310 _check_chain_extensions
// match: dc3940 _check_crl_path
// match: dc3a20 _check_dane_issuer
// match: dc3c10 _check_key_level
// match: dc4c10 _dane_verify
// match: dc4db0 _find_issuer
// match: dc5070 _get_crl_sk
// match: dc5350 _idp_check_dp
// match: dc5470 _internal_verify
// match: dc5690 _verify_chain
// match: dc57a0 _x509_check_cert_time
// match: dc8520 _X509_STORE_CTX_get_explicit_policy
// match: dcb4d0 _X509_STORE_CTX_set_verify
// match: dd3a80 _X509_STORE_CTX_get_check_policy
// match: dd3ac0 _X509_STORE_CTX_get_get_crl
// match: ddbf50 _X509_STORE_CTX_get_error_depth
// match: ddef80 _X509_STORE_CTX_set0_untrusted
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/x509/x509_vfy.c"
