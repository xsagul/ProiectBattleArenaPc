// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: easy.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b99590 _conn_upkeep
// match: b9aec0 _curl_easy_cleanup
// match: b9b2a0 _curl_easy_getinfo
// match: b9b2c0 _curl_easy_init
// match: b9bc30 _curl_easy_upkeep
// match: b9bf80 _curl_global_init_mem
#include "../../../../tools/third_party/curl-7.78.0/lib/easy.c"
