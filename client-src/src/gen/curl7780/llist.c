// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: llist.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b8c360 _Curl_llist_destroy
// match: b8c410 _Curl_llist_init
// match: b8c430 _Curl_llist_insert_next
// match: b8c4b0 _Curl_llist_remove
// match: d84cf0 _Curl_llist_count
#include "../../../../tools/third_party/curl-7.78.0/lib/llist.c"
