// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: e_aes.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dba350 _aes_cbc_cipher
// match: dba400 _aes_ecb_cipher
// match: dba470 _aes_gcm_cleanup
// match: dba4d0 _aes_gcm_ctrl
// match: dba940 _aes_gcm_init_key
// match: dbaa50 _aes_xts_ctrl
// match: dbaae0 _aes_xts_init_key
// match: dbac90 _aes_ccm_ctrl
// match: dbaf60 _aes_ccm_init_key
// match: dbb090 _aes_wrap_init_key
// match: dbb150 _aes_wrap_cipher
// match: dbb2f0 _aes_ocb_ctrl
// match: dbb4b0 _aes_ocb_init_key
// match: dbb640 _aes_ocb_cleanup
// match: dbb660 _aesni_init_key
// match: dbb740 _aesni_cbc_cipher
// match: dbb780 _aesni_ecb_cipher
// match: dbb7d0 _aes_ofb_cipher
// match: dbb920 _aes_cfb1_cipher
// match: dbba90 _aes_ctr_cipher
// match: dbbb40 _aesni_gcm_init_key
// match: dbbc30 _aes_gcm_cipher
// match: dbbd70 _aesni_xts_init_key
// match: dbbeb0 _aes_xts_cipher
// match: dbbf70 _aesni_ccm_init_key
// match: dbc040 _aes_ccm_cipher
// match: dbc310 _aesni_ocb_init_key
// match: dbc460 _aes_ocb_cipher
// match: dbc770 _aes_init_key
// match: dbcd30 _aes_ccm_tls_cipher
// match: dbcf40 _aes_gcm_tls_cipher
#define OPENSSL_FILE "crypto\\evp\\e_aes.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/evp/e_aes.c"
