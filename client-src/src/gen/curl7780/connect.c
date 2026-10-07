// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: connect.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b82490 _Curl_conncontrol
// match: b82720 _Curl_conninfo_local
// match: b99190 _conn_is_conn
#include "../../../../tools/third_party/curl-7.78.0/lib/connect.c"
