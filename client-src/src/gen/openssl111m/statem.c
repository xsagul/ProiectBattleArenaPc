// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: statem.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d89ed0 _SSL_in_before
// match: d89f00 _SSL_is_init_finished
// match: d89f30 _ossl_statem_app_data_allowed
// match: d89f70 _ossl_statem_check_finish_init
// match: d89ff0 _ossl_statem_clear
// match: d8a030 _ossl_statem_export_allowed
// match: d8a050 _ossl_statem_fatal
// match: d8a0c0 _ossl_statem_in_error
// match: d8a0d0 _ossl_statem_set_in_handshake
// match: d8a0f0 _ossl_statem_set_in_init
// match: d8a100 _ossl_statem_set_renegotiate
// match: d8a120 _ossl_statem_skip_early_data
// match: d8a150 _read_state_machine
// match: d8a4d0 _state_machine
// match: d8a860 _statem_flush
// match: d8a8a0 _write_state_machine
#define OPENSSL_FILE "ssl\\statem\\statem.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/statem/statem.c"
