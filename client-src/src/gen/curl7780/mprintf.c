// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: mprintf.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b978b0 _addbyter
// match: b9c150 _curl_mprintf
// match: b9c1a0 _curl_msprintf
// match: b9cf40 _curl_mvfprintf
// match: b9cf60 _curl_mvprintf
// match: b9cf90 _curl_mvsnprintf
// match: b9d000 _curl_mvsprintf
// match: b9f5d0 _dprintf_Pass1
// match: babfb0 _storebuffer
#include "../../../../tools/third_party/curl-7.78.0/lib/mprintf.c"
