// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: rsa_pmeth.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: e2d9e0 _pkey_rsa_init
// match: e2da50 _pkey_rsa_copy
// match: e2db30 _pkey_rsa_cleanup
// match: e2db80 _pkey_rsa_sign
// match: e2dd60 _pkey_rsa_verifyrecover
// match: e2dec0 _pkey_rsa_verify
// match: e2e170 _pkey_rsa_encrypt
// match: e2e210 _pkey_rsa_decrypt
// match: e2e2e0 _pkey_rsa_ctrl
// match: e2e720 _pkey_rsa_ctrl_str
// match: e2ed90 _pkey_rsa_keygen
// match: e2ee90 _pkey_pss_init
// match: e2ef60 _check_padding_md
// match: e2f150 _setup_tbuf
#define OPENSSL_FILE "crypto\\rsa\\rsa_pmeth.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/rsa/rsa_pmeth.c"
