// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: statem_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d8cf40 _check_for_downgrade
// match: d8cfc0 _check_in_list
// match: d8d020 _construct_ca_names
// match: d8d130 _construct_key_exchange_tbs
// match: d8d1d0 _create_synthetic_message_hash
// match: d8d2e0 _get_ca_names
// match: d8d320 _get_cert_verify_tbs_data
// match: d8d450 _parse_ca_names
// match: d8d610 _ssl3_do_write
// match: d8d6f0 _ssl3_output_cert_chain
// match: d8d760 _ssl3_take_mac
// match: d8d7b0 _ssl_add_cert_chain
// match: d8d9b0 _ssl_add_cert_to_wpacket
// match: d8da80 _ssl_allow_compression
// match: d8dab0 _ssl_check_version_downgrade
// match: d8db30 _ssl_choose_client_version
// match: d8ddb0 _ssl_choose_server_version
// match: d8e0b0 _ssl_get_min_max_version
// match: d8e270 _ssl_method_error
// match: d8e310 _ssl_set_client_hello_version
// match: d8e380 _ssl_set_version_bound
// match: d8e3f0 _ssl_version_supported
// match: d8e5f0 _ssl_x509err2alert
// match: d8e620 _tls13_restore_handshake_digest_for_pha
// match: d8e690 _tls13_save_handshake_digest_for_pha
// match: d8e740 _tls_close_construct_packet
// match: d8eca0 _tls_finish_handshake
// match: d8ef00 _tls_get_message_body
// match: d8f0e0 _tls_get_message_header
// match: d8f2f0 _tls_process_cert_verify
// match: d8f7c0 _tls_process_change_cipher_spec
// match: d8f8d0 _tls_process_finished
// match: d8fbd0 _tls_process_key_update
// match: d8fca0 _tls_setup_handshake
// match: d8fed0 _version_cmp
#define OPENSSL_FILE "ssl\\statem\\statem_lib.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/statem/statem_lib.c"
