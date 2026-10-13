// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ssl_cert.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d87050 _SSL_CTX_add_client_CA
// match: d870c0 _SSL_CTX_set0_CA_list
// match: d870f0 _SSL_add_dir_cert_subjects_to_stack
// match: d87390 _SSL_add_file_cert_subjects_to_stack
// match: d874c0 _SSL_get0_CA_list
// match: d874e0 _SSL_get_client_CA_list
// match: d87520 _SSL_get_ex_data_X509_STORE_CTX_idx
// match: d87550 _SSL_set0_CA_list
// match: d87580 _ssl_build_cert_chain
// match: d878a0 _ssl_cert_add0_chain_cert
// match: d87920 _ssl_cert_add1_chain_cert
// match: d879b0 _ssl_cert_dup
// match: d87e50 _ssl_cert_free
// match: d87f80 _ssl_cert_lookup_by_idx
// match: d87fa0 _ssl_cert_lookup_by_nid
// match: d87fd0 _ssl_cert_lookup_by_pkey
// match: d88010 _ssl_cert_new
// match: d880b0 _ssl_cert_select_current
// match: d88130 _ssl_cert_set0_chain
// match: d881e0 _ssl_cert_set1_chain
// match: d88230 _ssl_cert_set_cert_store
// match: d88270 _ssl_cert_set_current
// match: d882e0 _ssl_ctx_security
// match: d88310 _ssl_get_security_level_bits
// match: d88360 _ssl_security
// match: d884d0 _ssl_verify_cert_chain
// match: d88710 _ssl_x509_store_ctx_init_ossl_
// match: d88740 _xname_cmp
#define OPENSSL_FILE "ssl\\ssl_cert.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/ssl_cert.c"
