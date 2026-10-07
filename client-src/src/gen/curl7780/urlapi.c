// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: urlapi.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: 2f3700 _sscanf
// match: b9d520 _curl_url
// match: b9d530 _curl_url_cleanup
// match: b9d550 _curl_url_dup
// match: ba12c0 _find_host_sep
// match: ba1350 _free_urlhandle
// match: ba2c40 _ipv4_normalize
// match: ba2de0 _junkscan
// match: ba77d0 _parseurl
#include "../../../../tools/third_party/curl-7.78.0/lib/urlapi.c"
