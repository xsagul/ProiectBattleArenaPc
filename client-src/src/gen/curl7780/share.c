// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: share.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b90ed0 _Curl_share_lock
// match: b90f10 _Curl_share_unlock
// match: b9d160 _curl_share_init
#include "../../../../tools/third_party/curl-7.78.0/lib/share.c"
