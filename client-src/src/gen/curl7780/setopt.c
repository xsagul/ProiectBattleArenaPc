// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: setopt.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b909f0 _Curl_setblobopt
// match: b90a80 _Curl_setstropt
// match: b9b7d0 _curl_easy_setopt
#include "../../../../tools/third_party/curl-7.78.0/lib/setopt.c"
