// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: multi.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b8cd80 _Curl_multi_closed
// match: b909c0 _Curl_set_in_callback
// match: b92bd0 _Curl_update_timer
// match: b9c370 _curl_multi_assign
// match: b9c510 _curl_multi_fdset
// match: b9c830 _curl_multi_poll
// match: b9cb50 _curl_multi_setopt
// match: b9ccc0 _curl_multi_socket
// match: b9cd00 _curl_multi_socket_action
// match: b9cd50 _curl_multi_socket_all
// match: b9ce20 _curl_multi_timeout
// match: b9ce80 _curl_multi_wakeup
// match: ba0e10 _trhash_compare
#include "../../../../tools/third_party/curl-7.78.0/lib/multi.c"
