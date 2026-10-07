// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: base64.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b80130 _Curl_base64_decode
// match: b98230 _base64_encode
#include "../../../../tools/third_party/curl-7.78.0/lib/base64.c"
