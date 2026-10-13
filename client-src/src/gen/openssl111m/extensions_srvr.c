// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: extensions_srvr.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: db0ed0 _tls_construct_stoc_alpn
// match: db0f80 _tls_construct_stoc_cookie
// match: db13e0 _tls_construct_stoc_cryptopro_bug
// match: db14f0 _tls_construct_stoc_early_data
// match: db15d0 _tls_construct_stoc_ec_pt_formats
// match: db1690 _tls_construct_stoc_ems
// match: db1700 _tls_construct_stoc_etm
// match: db17a0 _tls_construct_stoc_key_share
// match: db19f0 _tls_construct_stoc_maxfragmentlen
// match: db1a90 _tls_construct_stoc_next_proto_neg
// match: db1b60 _tls_construct_stoc_psk
// match: db1bf0 _tls_construct_stoc_renegotiate
// match: db1cc0 _tls_construct_stoc_server_name
// match: db1d50 _tls_construct_stoc_session_ticket
// match: db1dd0 _tls_construct_stoc_status_request
// match: db1eb0 _tls_construct_stoc_supported_groups
// match: db2060 _tls_construct_stoc_supported_versions
// match: db2110 _tls_construct_stoc_use_srtp
// match: db21c0 _tls_parse_ctos_alpn
// match: db2320 _tls_parse_ctos_cookie
// match: db2a70 _tls_parse_ctos_early_data
// match: db2ad0 _tls_parse_ctos_ec_pt_formats
// match: db2b90 _tls_parse_ctos_ems
// match: db2bd0 _tls_parse_ctos_etm
// match: db2bf0 _tls_parse_ctos_key_share
// match: db2ee0 _tls_parse_ctos_maxfragmentlen
// match: db2f80 _tls_parse_ctos_npn
// match: db2fb0 _tls_parse_ctos_post_handshake_auth
// match: db3730 _tls_parse_ctos_psk_kex_modes
// match: db37e0 _tls_parse_ctos_renegotiate
// match: db38d0 _tls_parse_ctos_server_name
// match: db3ac0 _tls_parse_ctos_session_ticket
// match: db3b10 _tls_parse_ctos_sig_algs
// match: db3be0 _tls_parse_ctos_sig_algs_cert
// match: db3d90 _tls_parse_ctos_status_request
// match: db4090 _tls_parse_ctos_supported_groups
// match: db41b0 _tls_parse_ctos_use_srtp
#define OPENSSL_FILE "ssl\\statem\\extensions_srvr.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/statem/extensions_srvr.c"
