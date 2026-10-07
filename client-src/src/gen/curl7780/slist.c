// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: slist.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b90f50 _Curl_slist_append_nodup
// match: b9d400 _curl_slist_append
// match: b9d480 _curl_slist_free_all
#include "../../../../tools/third_party/curl-7.78.0/lib/slist.c"
