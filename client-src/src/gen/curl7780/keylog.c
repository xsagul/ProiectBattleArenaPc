// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: keylog.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b92a70 _Curl_tls_keylog_close
// match: b92aa0 _Curl_tls_keylog_open
// match: b92b10 _Curl_tls_keylog_write_line
#include "../../../../tools/third_party/curl-7.78.0/lib/vtls/keylog.c"
