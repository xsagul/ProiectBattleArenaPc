// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: http.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b7b0f0 _https_getsock
// match: b98a50 _checkhttpprefix
// match: ba7ec0 _pickoneauth
#include "../../../../tools/third_party/curl-7.78.0/lib/http.c"
