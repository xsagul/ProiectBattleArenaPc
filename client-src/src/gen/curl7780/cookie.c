// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: cookie.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b839d0 _Curl_cookie_cleanup
// match: b83a80 _Curl_cookie_clearall
// match: b83b20 _Curl_cookie_freelist
// match: b99920 _cookie_output
// match: b99bc0 _cookie_sort
// match: b99ca0 _cookie_sort_ct
// match: ba13d0 _freecookie
// match: ba1470 _get_netscape_format
// match: ba9c40 _remove_expired
// match: baa2e0 _sanitize_cookie_path
// match: bac0b0 _tailmatch
#include "../../../../tools/third_party/curl-7.78.0/lib/cookie.c"
