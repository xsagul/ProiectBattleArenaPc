// libcurl 7.78.0 with OpenSSL, zlib and zstd, protocols other than HTTP(S) and FILE disabled, compiled by Riot as C (several files per compilation unit: grouping not known yet): multi.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32 -DHAVE_LIBZ -DHAVE_ZLIB_H -Itools/third_party/zlib-1.2.11 -DHAVE_ZSTD -DHAVE_ZSTD_H -Itools/third_party/zstd-1.4.9/lib -DCURL_DISABLE_DICT -DCURL_DISABLE_FTP -DCURL_DISABLE_GOPHER -DCURL_DISABLE_IMAP -DCURL_DISABLE_LDAP -DCURL_DISABLE_LDAPS -DCURL_DISABLE_MQTT -DCURL_DISABLE_POP3 -DCURL_DISABLE_RTSP -DCURL_DISABLE_SMB -DCURL_DISABLE_SMTP -DCURL_DISABLE_TELNET -DCURL_DISABLE_TFTP
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
