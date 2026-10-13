// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: x509_lu.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: c36500 _X509_STORE_set_cleanup
// match: d830d0 _X509_STORE_set_cert_crl
// match: dbec60 _X509_STORE_set_verify
// match: dbec70 _X509_STORE_set_check_crl
// match: dbec90 _X509_STORE_set_verify_cb
// match: dc0cc0 _X509_LOOKUP_ctrl
// match: dc0cf0 _X509_OBJECT_free
// match: dc0d30 _X509_OBJECT_new
// match: dc15f0 _X509_STORE_CTX_get_by_subject
// match: dc1720 _X509_STORE_add_cert
// match: dc1760 _X509_STORE_add_crl
// match: dc17a0 _X509_STORE_add_lookup
// match: dc18c0 _X509_STORE_free
// match: dc19b0 _X509_STORE_new
// match: dc1b10 _x509_object_cmp
// match: dc1b60 _x509_object_idx_cnt
// match: dc1c90 _x509_store_add
#define OPENSSL_FILE "crypto\\x509\\x509_lu.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/x509/x509_lu.c"
