// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: select.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b8e9b0 _Curl_poll
// match: b91000 _Curl_socket_check
// match: b96b80 _Curl_wait_ms
#include "../../../../tools/third_party/curl-7.78.0/lib/select.c"
