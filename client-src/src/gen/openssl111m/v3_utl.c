// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: v3_utl.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e08fd0 _X509V3_NAME_from_section
// match: e09080 _X509V3_add_value_uchar
// match: e090d0 _X509V3_add_value_bool
// match: e094e0 _X509V3_get_value_int
// match: e09720 _X509_check_email
// match: e09790 _X509_check_host
// match: e09800 _X509_check_ip
// match: e09830 _a2i_IPADDRESS
// match: e099b0 _a2i_ipadd
// match: e09d80 _do_x509_check
// match: e09f40 _equal_case
// match: e0a030 _equal_nocase
// match: e0a2e0 _ipv4_from_asc
// match: e0a370 _ipv6_cb
// match: e0a450 _name_cmp
// match: e0a5c0 _skip_prefix
// match: e0a610 _strip_spaces
// match: e0a6a0 _valid_star
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/x509v3/v3_utl.c"
