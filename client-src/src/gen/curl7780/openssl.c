// libcurl 7.78.0 with OpenSSL, zlib and zstd, protocols other than HTTP(S) and FILE disabled, compiled by Riot as C (several files per compilation unit: grouping not known yet): openssl.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32 -DHAVE_LIBZ -DHAVE_ZLIB_H -Itools/third_party/zlib-1.2.11 -DHAVE_ZSTD -DHAVE_ZSTD_H -Itools/third_party/zstd-1.4.9/lib -DCURL_DISABLE_DICT -DCURL_DISABLE_FTP -DCURL_DISABLE_GOPHER -DCURL_DISABLE_IMAP -DCURL_DISABLE_LDAP -DCURL_DISABLE_LDAPS -DCURL_DISABLE_MQTT -DCURL_DISABLE_POP3 -DCURL_DISABLE_RTSP -DCURL_DISABLE_SMB -DCURL_DISABLE_SMTP -DCURL_DISABLE_TELNET -DCURL_DISABLE_TFTP
// match: bac6a0 _ossl_associate_connection
// match: bac850 _ossl_set_engine
// match: baca60 _ossl_check_cxn
// match: bacaf0 _ossl_set_engine_default
// match: bacb50 _ossl_engines_list
// match: bacba0 _ossl_close
// match: bace00 _ossl_close_all
// match: bace50 _ossl_connect
// match: bace70 _ossl_data_pending
// match: bacec0 _ossl_version
// match: bacf50 _ossl_random
// match: bacfa0 _ossl_sha256sum
// match: bad000 _ossl_get_internals
// match: bad020 _ossl_disassociate_connection
// match: bad160 _SSL_ERROR_to_str
// match: bad1f0 _cert_stuff
// match: bade50 _do_file_type
// match: bae910 _ossl_closeone
// match: bae9a0 _ossl_connect_common
// match: baffb0 _ossl_new_session_cb
// match: bb08c0 _ossl_trace
// match: bb0e00 _passwd_callback
// match: bb1f80 _x509_name_oneline
#include "../../../../tools/third_party/curl-7.78.0/lib/vtls/openssl.c"
