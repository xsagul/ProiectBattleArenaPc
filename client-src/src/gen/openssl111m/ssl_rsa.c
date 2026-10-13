// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ssl_rsa.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d81bd0 _SSL_CTX_use_PrivateKey
// match: d81c10 _SSL_CTX_use_PrivateKey_file
// match: d81d50 _SSL_CTX_use_certificate
// match: d81df0 _SSL_CTX_use_certificate_file
// match: d81f00 _SSL_CTX_use_serverinfo_ex
// match: d82010 _SSL_CTX_use_serverinfo_file
// match: d82400 _SSL_use_PrivateKey
// match: d82440 _SSL_use_PrivateKey_file
// match: d82580 _SSL_use_certificate
// match: d82610 _serverinfo_process_buffer
// match: d82740 _serverinfo_srv_add_cb
// match: d82770 _serverinfo_srv_parse_cb
// match: d82790 _serverinfoex_srv_add_cb
// match: d828a0 _serverinfoex_srv_parse_cb
// match: d828c0 _ssl_set_cert
// match: d829f0 _ssl_set_pkey
// match: d82b00 _use_certificate_chain_file
#define OPENSSL_FILE "ssl\\ssl_rsa.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/ssl_rsa.c"
