// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: inet_ntop.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: ba2380 _inet_ntop4
#include "../../../../tools/third_party/curl-7.78.0/lib/inet_ntop.c"
