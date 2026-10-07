// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: openssl.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: bac6a0 _ossl_associate_connection
// match: baca60 _ossl_check_cxn
// match: bacb50 _ossl_engines_list
// match: bacba0 _ossl_close
// match: bace50 _ossl_connect
// match: bace70 _ossl_data_pending
// match: bacec0 _ossl_version
// match: bacf50 _ossl_random
// match: bacfa0 _ossl_sha256sum
// match: bad000 _ossl_get_internals
// match: bad020 _ossl_disassociate_connection
// match: bad160 _SSL_ERROR_to_str
// match: bade50 _do_file_type
// match: badee0 _get_cert_chain
// match: bae910 _ossl_closeone
// match: bae9a0 _ossl_connect_common
// match: baffb0 _ossl_new_session_cb
// match: bb08c0 _ossl_trace
// match: bb0e00 _passwd_callback
// match: bb1d10 _verifystatus
// match: bb1f80 _x509_name_oneline
#include "../../../../tools/third_party/curl-7.78.0/lib/vtls/openssl.c"
