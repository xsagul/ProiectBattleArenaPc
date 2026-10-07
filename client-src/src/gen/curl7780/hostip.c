// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: hostip.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b90580 _Curl_resolv_timeout
// match: b9ae60 _create_hostcache_id
// match: ba1bb0 _hostcache_timestamp_remove
#include "../../../../tools/third_party/curl-7.78.0/lib/hostip.c"
