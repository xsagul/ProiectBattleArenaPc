// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ssl_conf.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dacb40 _cmd_SignatureAlgorithms
// match: dacb80 _cmd_ClientSignatureAlgorithms
// match: dacbc0 _cmd_Groups
// match: dacc00 _cmd_ECDHParameters
// match: dacd70 _cmd_Protocol
// match: dacda0 _cmd_MinProtocol
// match: dacdc0 _cmd_MaxProtocol
// match: dacde0 _cmd_Options
// match: dace20 _cmd_VerifyMode
// match: dace60 _cmd_Certificate
// match: dacf10 _cmd_PrivateKey
// match: dacf60 _cmd_ServerInfoFile
// match: dacfd0 _cmd_VerifyCAPath
// match: dacff0 _cmd_VerifyCAFile
// match: dad070 _cmd_DHParameters
// match: dad1c0 _SSL_CONF_CTX_finish
// match: dad2c0 _SSL_CONF_CTX_free
// match: dad330 _SSL_CONF_CTX_new
// match: dad360 _SSL_CONF_CTX_set_ssl
// match: dad3d0 _SSL_CONF_CTX_set_ssl_ctx
// match: dad440 _SSL_CONF_cmd
// match: dad580 _do_store
// match: dad5f0 _min_max_proto
// match: dad680 _ssl_conf_cmd_lookup
// match: dad730 _ssl_conf_cmd_skip_prefix
// match: dad7c0 _ssl_set_option
// match: dad820 _ssl_set_option_list
#define OPENSSL_FILE "ssl\\ssl_conf.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/ssl_conf.c"
