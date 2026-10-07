// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: obj_dat.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: ddc370 _OBJ_bsearch_
// match: ddc3e0 _OBJ_bsearch_ex_
// match: ddc6e0 _OBJ_get0_data
// match: ddc700 _OBJ_ln2nid
// match: ddc9b0 _OBJ_obj2nid
// match: ddcf40 _OBJ_sn2nid
// match: ddd1b0 _added_obj_cmp
// match: ddd2d0 _added_obj_hash
// match: ddd390 _cleanup1_doall
// match: ddd3b0 _cleanup2_doall
// match: ddd3f0 _obj_cleanup_int
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/objects/obj_dat.c"
