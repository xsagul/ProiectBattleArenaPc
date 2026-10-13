// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: e_capi.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e01840 _CAPI_trace
// match: e018c0 _ERR_CAPI_error
// match: e018f0 _capi_adderror
// match: e01940 _capi_addlasterror
// match: e01990 _capi_cert_get_fname
// match: e01a60 _capi_ctrl
// match: e01e70 _capi_ctx_set_provname
// match: e02010 _capi_destroy
// match: e02080 _capi_dsa_do_sign
// match: e024c0 _capi_dump_cert
// match: e026b0 _capi_find_cert
// match: e02a10 _capi_finish
// match: e02ab0 _capi_get_cert_key
// match: e02b00 _capi_get_key
// match: e02d10 _capi_get_pkey
// match: e03260 _capi_get_prov_info
// match: e03330 _capi_get_provname
// match: e03550 _capi_init
// match: e03920 _capi_list_containers
// match: e03c40 _capi_list_providers
// match: e041d0 _capi_open_store
// match: e04300 _capi_rsa_priv_dec
// match: e04570 _capi_rsa_priv_enc
// match: e045a0 _capi_rsa_sign
// match: e04880 _engine_capi
// match: e04a50 _engine_load_capi_int
// match: e04a80 _lend_tobn
// match: e04ad0 _wide_to_asc
#define OPENSSL_FILE "engines\\e_capi.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/engines/e_capi.c"
