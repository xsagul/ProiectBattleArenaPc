// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: extensions.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: da0610 _init_session_ticket
// match: da0680 _init_npn
// match: da0720 _final_alpn
// match: da0820 _init_certificate_authorities
// match: da0980 _init_etm
// match: da09a0 _init_ems
// match: da0a60 _init_psk_kex_modes
// match: da0d10 _init_srtp
// match: da0ef0 _init_post_handshake_auth
// match: da1010 _extension_is_relevant
// match: da10c0 _should_add_extension
// match: da16d0 _tls_parse_all_extensions
// match: da17f0 _tls_parse_extension
// match: da1ca0 _tls_validate_all_contexts
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/statem/extensions.c"
