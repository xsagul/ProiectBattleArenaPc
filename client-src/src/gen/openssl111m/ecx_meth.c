// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ecx_meth.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e1fa60 _ecx_pub_encode
// match: e1fb80 _ecx_pub_decode
// match: e1fbe0 _ecx_pub_cmp
// match: e1fc40 _ecx_priv_decode
// match: e1fce0 _ecx_priv_encode
// match: e1fe20 _ecx_size
// match: e1fe50 _ecx_bits
// match: e1fe90 _ecx_security_bits
// match: e1fec0 _ecx_free
// match: e1ff50 _ecx_pub_print
// match: e1ff70 _ecx_ctrl
// match: e200b0 _ecd_ctrl
// match: e200d0 _ecx_set_priv_key
// match: e200f0 _ecx_set_pub_key
// match: e201b0 _ecx_get_priv_key
// match: e20280 _ecx_get_pub_key
// match: e20350 _ecd_item_verify
// match: e203e0 _ecd_item_sign25519
// match: e20430 _ecd_sig_info_set25519
// match: e20450 _ecd_item_sign448
// match: e204a0 _ecd_sig_info_set448
// match: e204c0 _pkey_ecx_keygen
// match: e204e0 _pkey_ecx_derive25519
// match: e20550 _pkey_ecx_derive448
// match: e205c0 _pkey_ecx_ctrl
// match: e205e0 _pkey_ecd_digestsign25519
// match: e20650 _pkey_ecd_digestsign448
// match: e206c0 _pkey_ecd_digestverify25519
// match: e20700 _pkey_ecd_digestverify448
// match: e20740 _pkey_ecd_ctrl
// match: e20790 _ecx_key_op
// match: e20a40 _ecx_key_print
// match: e20bb0 _validate_ecx_derive
#define OPENSSL_FILE "crypto\\ec\\ecx_meth.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ec/ecx_meth.c"
