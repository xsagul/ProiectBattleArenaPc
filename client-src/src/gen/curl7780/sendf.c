// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: sendf.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b8f600 _Curl_read
// match: b8f670 _Curl_read_plain
// match: b96e50 _Curl_write
#include "../../../../tools/third_party/curl-7.78.0/lib/sendf.c"
