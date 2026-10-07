// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: formdata.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b864b0 _Curl_getformdata
// match: b9bcb0 _curl_formfree
// match: b9bd20 _curl_formget
#include "../../../../tools/third_party/curl-7.78.0/lib/formdata.c"
