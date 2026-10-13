// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: pem_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: de0070 _PEM_ASN1_read
// match: de00e0 _PEM_ASN1_write_bio
// match: de05c0 _PEM_bytes_read_bio
// match: de05f0 _PEM_bytes_read_bio_secmem
// match: de0620 _PEM_def_callback
// match: de06c0 _PEM_do_header
// match: de0910 _PEM_get_EVP_CIPHER_INFO
// match: de0bb0 _PEM_read_bio
// match: de0bd0 _PEM_read_bio_ex
// match: de0ea0 _PEM_write_bio
// match: de1100 _check_pem
// match: de1630 _get_header_and_data
// match: de18b0 _get_name
// match: de1a40 _pem_bytes_read_bio_flags
// match: de1f10 _pem_check_suffix
// match: de1f90 _pem_free
// match: de1fd0 _pem_malloc
// match: de2010 _sanitize_line
#define OPENSSL_FILE "crypto\\pem\\pem_lib.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/crypto/pem/pem_lib.c"
