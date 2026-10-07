// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: rsa_ameth.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e20fa0 _rsa_pub_cmp
// match: e211f0 _rsa_bits
// match: e21230 _rsa_pub_print
// match: e21240 _rsa_priv_print
// match: e21250 _rsa_sig_print
// match: e216b0 _rsa_item_sign
// match: e21770 _rsa_sig_info_set
// match: e21850 _rsa_pkey_check
// match: e21870 _pkey_rsa_print
// match: e21e70 _rsa_cms_encrypt
// match: e22240 _rsa_ctx_to_pss_string
// match: e22280 _rsa_md_to_mgf1
// match: e22350 _rsa_mgf1_decode
// match: e22410 _rsa_param_encode
// match: e22480 _rsa_pss_decode
// match: e22640 _rsa_pss_param_print
// match: e22900 _rsa_pss_params_create
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/rsa/rsa_ameth.c"
