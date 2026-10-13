// OpenSSL 1.1.1m (VC-WIN32 configuration, its own build options), prebuilt for the client with MSVC 14.30.30709: t1_lib.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.30.30709
// flags: -MT -Zl -Gs0 -GF -Gy -W3 -wd4090 -O2 -Itools/third_party/openssl-1.1.1m -Itools/third_party/openssl-1.1.1m/include -Itools/third_party/openssl-1.1.1m/crypto/modes -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448 -Itools/third_party/openssl-1.1.1m/crypto/ec/curve448/arch_32 -DL_ENDIAN -DOPENSSL_PIC -DOPENSSL_CPUID_OBJ -DOPENSSL_BN_ASM_PART_WORDS -DOPENSSL_IA32_SSE2 -DOPENSSL_BN_ASM_MONT -DOPENSSL_BN_ASM_GF2m -DSHA1_ASM -DSHA256_ASM -DSHA512_ASM -DRC4_ASM -DMD5_ASM -DRMD160_ASM -DAESNI_ASM -DVPAES_ASM -DWHIRLPOOL_ASM -DGHASH_ASM -DECP_NISTZ256_ASM -DPOLY1305_ASM -DOPENSSL_SYS_WIN32 -DWIN32_LEAN_AND_MEAN -DUNICODE -D_UNICODE -D_CRT_SECURE_NO_DEPRECATE -D_WINSOCK_DEPRECATED_NO_WARNINGS -DNDEBUG
// match: d8cee0 _PACKET_get_net_2
// match: d91350 _check_cert_usable
// match: d91430 _find_sig_alg
// match: d91610 _get_sigorhash
// match: d91770 _has_usable_cert
// match: d917d0 _nid_cb
// match: d918c0 _sig_cb
// match: d91a70 _sigalg_security_bits
// match: d91ae0 _ssl_check_ca_name
// match: d91b40 _ssl_cipher_disabled
// match: d91c10 _ssl_get_auto_dh
// match: d91d40 _ssl_security_cert
// match: d91ea0 _ssl_security_cert_chain
// match: d920e0 _ssl_set_client_disabled
// match: d92230 _ssl_set_sig_mask
// match: d922d0 _tls12_check_peer_sigalg
// match: d92660 _tls12_copy_sigalgs
// match: d92740 _tls12_get_psigalgs
// match: d927f0 _tls12_shared_sigalgs
// match: d92890 _tls12_sigalg_allowed
// match: d92b00 _tls1_check_cert_param
// match: d92bc0 _tls1_check_chain
// match: d931f0 _tls1_check_ec_tmp_key
// match: d93420 _tls1_check_group_id
// match: d93500 _tls1_check_pkey_comp
// match: d935b0 _tls1_check_sig_alg
// match: d93690 _tls1_clear
// match: d936d0 _tls1_free
// match: d93700 _tls1_get_formatlist
// match: d93750 _tls1_get_group_id
// match: d93790 _tls1_get_legacy_sigalg
// match: d938b0 _tls1_get_supported_groups
// match: d93940 _tls1_group_id_lookup
// match: d93960 _tls1_in_list
// match: d93990 _tls1_lookup_md
// match: d939d0 _tls1_new
// match: d93a00 _tls1_process_sigalgs
// match: d93c20 _tls1_save_sigalgs
// match: d93c90 _tls1_save_u16
// match: d93d70 _tls1_set_cert_validity
// match: d93e00 _tls1_set_groups
// match: d93f00 _tls1_set_groups_list
// match: d940c0 _tls1_set_peer_legacy_sigalg
// match: d94110 _tls1_set_server_sigalgs
// match: d942c0 _tls1_set_sigalgs
// match: d94410 _tls1_set_sigalgs_list
// match: d94550 _tls1_shared_group
// match: d946f0 _tls_check_sigalg_curve
// match: d94780 _tls_choose_sigalg
// match: d94be0 _tls_curve_allowed
// match: d94c30 _tls_decrypt_ticket
// match: d950d0 _tls_get_ticket_from_client
// match: d95150 _tls_use_ticket
#define OPENSSL_FILE "ssl\\t1_lib.c"
#define OPENSSL_LINE __LINE__
#include "../../../../tools/third_party/openssl-1.1.1m/ssl/t1_lib.c"
