// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: statem_clnt.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: da3e80 _PACKET_as_length_prefixed_2
// match: da3f60 _PACKET_get_net_4
// match: da4020 _cert_req_allowed
// match: da42f0 _ossl_statem_client_post_process_message
// match: da5580 _set_client_ciphersuite
// match: da5700 _ssl3_check_cert_and_algorithm
// match: da5820 _ssl3_check_client_certificate
// match: da5870 _ssl_cipher_list_to_bytes
// match: da5af0 _tls_construct_cke_gost
// match: da5df0 _tls_construct_cke_psk_preamble
// match: da6060 _tls_construct_cke_rsa
// match: da6c00 _tls_prepare_client_certificate
// match: da6e40 _tls_process_cert_status_body
// match: da6f80 _tls_process_certificate_request
// match: da73b0 _tls_process_initial_server_flight
// match: da7930 _tls_process_new_session_ticket
// match: da7d90 _tls_process_server_certificate
// match: da8270 _tls_process_server_hello
// match: da8b60 _tls_process_ske_dhe
// match: da8e50 _tls_process_ske_ecdhe
// match: da8ff0 _tls_process_ske_srp
#define OPENSSL_FILE "ssl\\statem\\statem_clnt.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/statem/statem_clnt.c"
