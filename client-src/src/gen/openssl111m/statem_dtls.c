// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: statem_dtls.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: da2580 _dtls1_close_construct_packet
// match: da2790 _dtls1_do_write
// match: da2bb0 _dtls1_get_message_header
// match: da2c30 _dtls1_hm_fragment_free
// match: da2c90 _dtls1_hm_fragment_new
// match: da2d80 _dtls1_preprocess_fragment
// match: da2e80 _dtls1_process_out_of_seq_message
// match: da30a0 _dtls1_read_failed
// match: da3120 _dtls1_reassemble_fragment
// match: da3430 _dtls1_retransmit_buffered_messages
// match: da3670 _dtls1_set_handshake_header
// match: da37d0 _dtls_get_message
// match: da3980 _dtls_get_reassembled_message
#define OPENSSL_FILE "ssl\\statem\\statem_dtls.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/statem/statem_dtls.c"
