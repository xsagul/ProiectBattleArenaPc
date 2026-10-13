// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: rec_layer_d1.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d9abb0 _DTLS_RECORD_LAYER_clear
// match: d9ad20 _DTLS_RECORD_LAYER_free
// match: d9aee0 _DTLS_RECORD_LAYER_new
// match: d9af90 _DTLS_RECORD_LAYER_set_saved_w_epoch
// match: d9b020 _do_dtls1_write
// match: d9b4b0 _dtls1_buffer_record
// match: d9b640 _dtls1_copy_record
// match: d9b6c0 _dtls1_get_bitmap
// match: d9b720 _dtls1_process_buffered_records
// match: d9b8c0 _dtls1_read_bytes
// match: d9c000 _dtls1_reset_seq_numbers
// match: d9c090 _dtls1_retrieve_buffered_record
// match: d9c0e0 _dtls1_write_bytes
#define OPENSSL_FILE "ssl\\record\\rec_layer_d1.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/record/rec_layer_d1.c"
