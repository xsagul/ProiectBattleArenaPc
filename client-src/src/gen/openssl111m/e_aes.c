// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: e_aes.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dba400 _aes_ecb_cipher
// match: dba940 _aes_gcm_init_key
// match: dbaa50 _aes_xts_ctrl
// match: dbaf60 _aes_ccm_init_key
// match: dbb4b0 _aes_ocb_init_key
// match: dbb640 _aes_ocb_cleanup
// match: dbb7d0 _aes_ofb_cipher
// match: dbba90 _aes_ctr_cipher
// match: dbbb40 _aesni_gcm_init_key
// match: dbbc30 _aes_gcm_cipher
// match: dbbf70 _aesni_ccm_init_key
// match: dbc310 _aesni_ocb_init_key
// match: dbcf40 _aes_gcm_tls_cipher
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/evp/e_aes.c"
