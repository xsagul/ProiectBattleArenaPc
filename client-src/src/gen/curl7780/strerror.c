// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: strerror.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b925b0 _Curl_strerror
// match: b9b800 _curl_easy_strerror
// match: b9cd90 _curl_multi_strerror
// match: b9d3a0 _curl_share_strerror
// match: ba1510 _get_winapi_error
// match: ba15d0 _get_winsock_error
#include "../../../../tools/third_party/curl-7.78.0/lib/strerror.c"
