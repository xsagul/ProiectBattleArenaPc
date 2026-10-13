// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: dh_ameth.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e1c3a0 _dh_pub_decode
// match: e1c4d0 _dh_pub_encode
// match: e1c5d0 _dh_priv_decode
// match: e1c710 _dh_priv_encode
// match: e1c830 _dh_param_decode
// match: e1c890 _dh_param_encode
// match: e1c8d0 _dh_bits
// match: e1c900 _dh_cmp_parameters
// match: e1c970 _dh_copy_parameters
// match: e1c9b0 _dh_missing_parameters
// match: e1c9d0 _dh_pub_cmp
// match: e1cab0 _dh_pkey_ctrl
// match: e1cbc0 _dh_pkey_public_check
// match: e1cc10 _dh_cms_encrypt
// match: e1cfe0 _dh_cms_set_peerkey
// match: e1d180 _dh_cms_set_shared_info
// match: e1d3e0 _do_dh_print
// match: e1d690 _int_dh_bn_cpy
// match: e1d6f0 _int_dh_param_copy
#define OPENSSL_FILE "crypto\\dh\\dh_ameth.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/dh/dh_ameth.c"
