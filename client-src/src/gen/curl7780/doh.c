// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: doh.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b9e770 _doh_decode
// match: b9eb40 _doh_write_cb
// match: babed0 _skipqname
#include "../../../../tools/third_party/curl-7.78.0/lib/doh.c"
