// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ssl3_record.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: da9640 _SSL3_RECORD_clear
// match: da9680 _SSL3_RECORD_release
// match: da96c0 _SSL3_RECORD_set_seq_num
// match: da96e0 _dtls1_get_record
// match: da9970 _dtls1_process_record
// match: da9dc0 _early_data_count_ok
// match: da9ec0 _ssl3_cbc_copy_mac
// match: daa070 _ssl3_do_compress
// match: daa0b0 _ssl3_do_uncompress
// match: daa120 _ssl3_get_record
// match: daad90 _ssl3_record_app_data_waiting
// match: daadd0 _tls1_cbc_remove_padding
// match: daaf20 _tls1_enc
// match: dab660 _tls1_mac
#define OPENSSL_FILE "ssl\\record\\ssl3_record.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/record/ssl3_record.c"
