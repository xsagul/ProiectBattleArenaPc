// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ssl_sess.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d82df0 _SSL_CTX_add_session
// match: d82fc0 _SSL_CTX_flush_sessions
// match: d83040 _SSL_CTX_remove_session
// match: d830e0 _SSL_SESSION_free
// match: d83210 _SSL_SESSION_get0_cipher
// match: d83220 _SSL_SESSION_get_time
// match: d83230 _SSL_SESSION_is_resumable
// match: d83260 _SSL_SESSION_list_remove
// match: d832f0 _SSL_SESSION_new
// match: d833e0 _SSL_SESSION_set_cipher
// match: d83400 _SSL_SESSION_set_protocol_version
// match: d83410 _SSL_SESSION_up_ref
// match: d83430 _SSL_get_session
// match: d83440 _SSL_set_session
// match: d83530 _lookup_sess_in_cache
// match: d836a0 _ssl_clear_bad_session
// match: d836f0 _ssl_generate_session_id
// match: d83890 _ssl_get_new_session
// match: d83bb0 _ssl_get_prev_session
// match: d84020 _ssl_session_dup
// match: d842e0 _timeout_cb
// match: dbe9f0 _SSL_CTX_get_timeout
#define OPENSSL_FILE "ssl\\ssl_sess.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/ssl_sess.c"
