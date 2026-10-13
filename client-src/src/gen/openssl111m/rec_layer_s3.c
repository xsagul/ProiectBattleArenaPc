// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: rec_layer_s3.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d8ac70 _RECORD_LAYER_clear
// match: d8ad20 _RECORD_LAYER_get_rrec_length
// match: d8ad30 _RECORD_LAYER_init
// match: d8ad60 _RECORD_LAYER_is_sslv2_record
// match: d8ad80 _RECORD_LAYER_processed_read_pending
// match: d8adb0 _RECORD_LAYER_read_pending
// match: d8adc0 _RECORD_LAYER_release
// match: d8ae00 _RECORD_LAYER_reset_read_sequence
// match: d8ae10 _RECORD_LAYER_reset_write_sequence
// match: d8ae20 _RECORD_LAYER_write_pending
// match: d8ae40 _SSL_set_default_read_buffer_len
// match: d8ae50 _do_ssl3_write
// match: d8b9f0 _ssl3_pending
// match: d8ba30 _ssl3_read_bytes
// match: d8c380 _ssl3_read_n
// match: d8c640 _ssl3_record_sequence_update
// match: d8c660 _ssl3_write_bytes
// match: d8c9a0 _ssl3_write_pending
#define OPENSSL_FILE "ssl\\record\\rec_layer_s3.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/record/rec_layer_s3.c"
