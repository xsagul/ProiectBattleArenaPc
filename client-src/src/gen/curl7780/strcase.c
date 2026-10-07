// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: strcase.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b8f5e0 _Curl_raw_toupper
// match: b92510 _Curl_strcasecompare
// match: b926a0 _Curl_strncasecompare
// match: b92730 _Curl_strntolower
// match: b92780 _Curl_strntoupper
#include "../../../../tools/third_party/curl-7.78.0/lib/strcase.c"
