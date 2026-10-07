// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: splay.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b91450 _Curl_splay
// match: b915a0 _Curl_splaygetbest
// match: b91650 _Curl_splayinsert
// match: b91770 _Curl_splayremove
#include "../../../../tools/third_party/curl-7.78.0/lib/splay.c"
