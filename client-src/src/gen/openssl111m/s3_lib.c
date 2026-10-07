// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: s3_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: 9bb8e0 _ssl_undefined_function_1
// match: d9cda0 _ssl3_set_handshake_header
// match: d9cdf0 _cipher_compare
// match: d9ce30 _ssl3_callback_ctrl
// match: d9ce80 _ssl3_choose_cipher
// match: d9dc80 _ssl3_ctx_callback_ctrl
// match: d9e6d0 _ssl3_get_cipher
// match: d9e6f0 _ssl3_get_cipher_by_char
// match: d9e760 _ssl3_get_cipher_by_id
// match: d9e7c0 _ssl3_get_cipher_by_std_name
// match: d9e8a0 _ssl3_get_req_cert_type
// match: d9ea70 _ssl3_put_cipher_by_char
// match: d9eae0 _ssl3_read_internal
// match: d9eb90 _ssl3_renegotiate
// match: d9ecb0 _ssl3_shutdown
// match: d9ed70 _ssl3_write
// match: d9ef80 _ssl_dh_to_pkey
// match: d9efc0 _ssl_fill_hello_random
// match: d9f270 _ssl_generate_param_group
// match: d9f350 _ssl_generate_pkey
// match: d9f530 _ssl_get_algorithm2
// match: d9f580 _ssl_sort_cipher_list
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/s3_lib.c"
