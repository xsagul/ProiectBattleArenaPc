// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: ui_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dd7ac0 _UI_get0_action_string
// match: dd7ad0 _UI_get0_result_string
// match: dd7af0 _UI_get0_test_string
// match: dd7b10 _UI_method_get_closer
// match: dd7b20 _UI_method_get_opener
// match: dd7b30 _UI_method_get_reader
// match: dd7b40 _UI_method_get_writer
// match: dd7b50 _UI_method_set_closer
// match: dd7b70 _UI_method_set_opener
// match: dd7b90 _UI_method_set_reader
// match: dd7bb0 _UI_method_set_writer
// match: dd7de0 _UI_set_result
// match: dd8050 _print_error
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/ui/ui_lib.c"
