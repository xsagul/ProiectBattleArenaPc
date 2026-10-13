// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: v3_purp.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dd4eb0 _check_purpose_ssl_client
// match: dd4f20 _check_purpose_ssl_server
// match: dd4f90 _check_purpose_ns_ssl_server
// match: dd5010 _check_purpose_smime_sign
// match: dd5050 _check_purpose_smime_encrypt
// match: dd5090 _check_purpose_crl_sign
// match: dd50d0 _check_purpose_timestamp_sign
// match: dd5150 _ocsp_helper
// match: dd5170 _X509_PURPOSE_get0
// match: dd51b0 _X509_PURPOSE_get_by_id
// match: dd5200 _X509_check_akid
// match: dd52e0 _X509_check_issued
// match: dd53b0 _X509_check_purpose
// match: dd5440 _X509_get_extended_key_usage
// match: dd5470 _X509_get_extension_flags
// match: dd5490 _X509_get_key_usage
// match: dd54c0 _check_ca
// match: dd5530 _check_sig_alg_match
// match: dd55c0 _nid_cmp_BSEARCH_CMP_FN
// match: dd55d0 _purpose_smime
// match: dd5630 _setup_crldp
// match: dd5780 _x509_likely_issued
// match: dd5810 _x509_signing_allowed
// match: dd5860 _x509v3_cache_extensions
#define OPENSSL_FILE "crypto\\x509v3\\v3_purp.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/x509v3/v3_purp.c"
