// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: timeval.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b8cfa0 _Curl_now
// match: b927d0 _Curl_timediff
// match: b92860 _Curl_timediff_us
#include "../../../../tools/third_party/curl-7.78.0/lib/timeval.c"
