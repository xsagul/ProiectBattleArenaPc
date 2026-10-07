// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: vtls.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b7cc60 _multissl_version
// match: b7cdc0 _multissl_init
// match: b7cde0 _multissl_connect
// match: b7ce00 _multissl_connect_nonblocking
// match: b7ce20 _multissl_getsock
// match: b7ce40 _multissl_get_internals
// match: b7ce60 _multissl_close
// match: b80e90 _Curl_clone_primary_ssl_config
// match: b85f60 _Curl_free_primary_ssl_config
// match: b92240 _Curl_ssl_getsock
// match: b922c0 _Curl_ssl_kill_session
// match: babf30 _ssl_connect_init_proxy
#include "../../../../tools/third_party/curl-7.78.0/lib/vtls/vtls.c"
