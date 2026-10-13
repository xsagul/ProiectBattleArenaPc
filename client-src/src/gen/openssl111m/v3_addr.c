// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: v3_addr.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: df31d0 _i2r_IPAddrBlocks
// match: df3540 _v2i_IPAddrBlocks
// match: df3d10 _IPAddressFamily_cmp
// match: df3dd0 _IPAddressOrRange_cmp
// match: df3fd0 _IPAddressOrRanges_canonize
// match: df44b0 _X509v3_addr_add_prefix
// match: df4520 _X509v3_addr_is_canonical
// match: df4ae0 _addr_contains
// match: df4da0 _addr_expand
// match: df4e20 _addr_validate_path_internal
// match: df5260 _i2r_address
// match: df5430 _make_IPAddressFamily
// match: df5580 _make_addressPrefix
// match: df5640 _make_addressRange
// match: df5810 _make_prefix_or_range
// match: df58a0 _range_should_be_prefix
// match: df5a80 _v4IPAddressOrRange_cmp
// match: df5aa0 _v6IPAddressOrRange_cmp
#define OPENSSL_FILE "crypto\\x509v3\\v3_addr.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/x509v3/v3_addr.c"
