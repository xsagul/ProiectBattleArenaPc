// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: bio_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dbe180 _BIO_callback_ctrl
// match: dbe270 _BIO_clear_flags
// match: dbe280 _BIO_copy_next_retry
// match: dbe2a0 _BIO_ctrl
// match: dbe380 _BIO_ctrl_pending
// match: dbe3a0 _BIO_find_type
// match: dbe3e0 _BIO_free
// match: dbe480 _BIO_free_all
// match: dbe560 _BIO_gets
// match: dbe700 _BIO_indent
// match: dbe8d0 _BIO_int_ctrl
// match: dbe900 _BIO_new
// match: dbea00 _BIO_pop
// match: dbea50 _BIO_push
// match: dbeaa0 _BIO_puts
// match: dbec50 _BIO_set_flags
// match: dbeca0 _BIO_test_flags
// match: dbecb0 _BIO_up_ref
// match: dbed10 _bio_call_callback
// match: dbedb0 _bio_cleanup
// match: dbedf0 _bio_read_intern
// match: dbef30 _bio_write_intern
#define OPENSSL_FILE "crypto\\bio\\bio_lib.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/bio/bio_lib.c"
