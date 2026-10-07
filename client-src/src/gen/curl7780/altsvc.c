// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: altsvc.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: bb43d0 _Curl_alpnid2str
// match: bb4400 _Curl_altsvc_cleanup
// match: bb4460 _Curl_altsvc_ctrl
// match: bb4480 _Curl_altsvc_init
// match: bb44c0 _Curl_altsvc_lookup
// match: bb4590 _Curl_altsvc_parse
// match: bb4b50 _Curl_altsvc_save
// match: bb4d90 _altsvc_createid
// match: bb4e20 _altsvc_load
// match: bb50d0 _getalnum
#include "../../../../tools/third_party/curl-7.78.0/lib/altsvc.c"
