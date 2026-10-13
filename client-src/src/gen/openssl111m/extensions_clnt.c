// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: extensions_clnt.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dadd80 _tls_construct_ctos_alpn
// match: dade50 _tls_construct_ctos_cookie
// match: dadf10 _tls_construct_ctos_early_data
// match: dae3b0 _tls_construct_ctos_ec_pt_formats
// match: dae460 _tls_construct_ctos_ems
// match: dae4b0 _tls_construct_ctos_etm
// match: dae520 _tls_construct_ctos_key_share
// match: dae780 _tls_construct_ctos_maxfragmentlen
// match: dae810 _tls_construct_ctos_npn
// match: dae8a0 _tls_construct_ctos_padding
// match: dae9e0 _tls_construct_ctos_post_handshake_auth
// match: daea60 _tls_construct_ctos_psk
// match: daee70 _tls_construct_ctos_psk_kex_modes
// match: daef50 _tls_construct_ctos_renegotiate
// match: daefe0 _tls_construct_ctos_sct
// match: daf050 _tls_construct_ctos_server_name
// match: daf120 _tls_construct_ctos_session_ticket
// match: daf270 _tls_construct_ctos_sig_algs
// match: daf350 _tls_construct_ctos_srp
// match: daf410 _tls_construct_ctos_status_request
// match: daf610 _tls_construct_ctos_supported_groups
// match: daf750 _tls_construct_ctos_supported_versions
// match: daf890 _tls_construct_ctos_use_srtp
// match: daf9c0 _tls_parse_stoc_alpn
// match: dafd00 _tls_parse_stoc_early_data
// match: dafe00 _tls_parse_stoc_ec_pt_formats
// match: daff60 _tls_parse_stoc_ems
// match: daff90 _tls_parse_stoc_etm
// match: daffe0 _tls_parse_stoc_key_share
// match: db0280 _tls_parse_stoc_maxfragmentlen
// match: db0330 _tls_parse_stoc_npn
// match: db04d0 _tls_parse_stoc_psk
// match: db0650 _tls_parse_stoc_renegotiate
// match: db0870 _tls_parse_stoc_sct
// match: db09b0 _tls_parse_stoc_server_name
// match: db0aa0 _tls_parse_stoc_session_ticket
// match: db0b60 _tls_parse_stoc_status_request
// match: db0c20 _tls_parse_stoc_supported_versions
// match: db0cc0 _tls_parse_stoc_use_srtp
// match: db0e10 _use_ecc
#define OPENSSL_FILE "ssl\\statem\\extensions_clnt.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/statem/extensions_clnt.c"
