// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: packet.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: da1db0 _WPACKET_allocate_bytes
// match: da1e20 _WPACKET_close
// match: da1e40 _WPACKET_fill_lengths
// match: da1f00 _WPACKET_get_curr
// match: da1f20 _WPACKET_get_length
// match: da1f50 _WPACKET_get_total_written
// match: da1fe0 _WPACKET_init_static_len
// match: da20e0 _WPACKET_put_bytes__
// match: da2140 _WPACKET_reserve_bytes
// match: da21d0 _WPACKET_set_flags
// match: da2310 _WPACKET_sub_allocate_bytes__
// match: da2370 _WPACKET_sub_memcpy__
// match: da23f0 _WPACKET_sub_reserve_bytes__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/packet.c"
