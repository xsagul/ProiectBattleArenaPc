// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: eng_lib.c, the functions of it that are in the client (tools/match_objs.py).
// same: 129c80 _ENGINE_get_id
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: dd97d0 _ENGINE_free
// match: dd9850 _ENGINE_new
// match: dd98e0 _ENGINE_set_cmd_defns
// match: dd9970 _ENGINE_set_flags
// match: dd9990 _ENGINE_set_id
// match: dd99f0 _ENGINE_set_name
// match: dd9a60 _engine_cleanup_add_first
// match: dd9ad0 _engine_cleanup_add_last
// match: dd9b60 _engine_cleanup_cb_free
// match: dd9b80 _engine_cleanup_int
// match: dd9bc0 _engine_free_util
// match: dd9c40 _engine_set_all_null
#define OPENSSL_FILE "crypto\\engine\\eng_lib.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/engine/eng_lib.c"
