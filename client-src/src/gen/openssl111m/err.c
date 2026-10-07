// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: err.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: db7440 _ERR_clear_last_mark
// match: db7490 _ERR_error_string_n
// match: db7760 _ERR_func_error_string
// match: db77e0 _ERR_get_error
// match: db7800 _ERR_get_error_line_data
// match: db7820 _ERR_get_next_error_library
// match: db7960 _ERR_load_ERR_strings
// match: db7b00 _ERR_load_strings
// match: db7b40 _ERR_load_strings_const
// match: db7b60 _ERR_peek_error
// match: db7b80 _ERR_peek_last_error
// match: db7d80 _ERR_set_mark
// match: db7db0 _ERR_unload_strings
// match: db7e20 _do_err_strings_init_ossl_
// match: db7e90 _err_cleanup
// match: db7ee0 _err_clear_last_constant_time
// match: db7f30 _err_delete_thread_state
// match: db7f60 _err_do_init_ossl_
// match: db7fa0 _err_load_strings
// match: db7ff0 _err_string_data_cmp
// match: db8010 _err_string_data_hash
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/err/err.c"
