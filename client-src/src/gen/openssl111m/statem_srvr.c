// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: statem_srvr.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d8ceb0 _PACKET_get_bytes
// match: d95180 _PACKET_copy_all
// match: d951c0 _PACKET_copy_bytes
// match: d951f0 _PACKET_equal
// match: d95220 _PACKET_forward
// match: d95240 _PACKET_get_length_prefixed_1
// match: d95290 _PACKET_get_length_prefixed_2
// match: d952f0 _PACKET_get_sub_packet
// match: d95de0 _ossl_statem_server_post_work
// match: d96c90 _send_certificate_request
// match: d96d00 _send_server_key_exchange
// match: da0f70 _PACKET_buf_init
// match: da0fa0 _PACKET_get_length_prefixed_3
// match: da3ee0 _PACKET_get_1
// match: da3f10 _PACKET_get_net_3
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/statem/statem_srvr.c"
