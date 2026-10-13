// libcurl 7.78.0 with OpenSSL, zlib and zstd, protocols other than HTTP(S) and FILE disabled, compiled by Riot as C (several files per compilation unit: grouping not known yet): cookie.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32 -DHAVE_LIBZ -DHAVE_ZLIB_H -Itools/third_party/zlib-1.2.11 -DHAVE_ZSTD -DHAVE_ZSTD_H -Itools/third_party/zstd-1.4.9/lib -DCURL_DISABLE_DICT -DCURL_DISABLE_FTP -DCURL_DISABLE_GOPHER -DCURL_DISABLE_IMAP -DCURL_DISABLE_LDAP -DCURL_DISABLE_LDAPS -DCURL_DISABLE_MQTT -DCURL_DISABLE_POP3 -DCURL_DISABLE_RTSP -DCURL_DISABLE_SMB -DCURL_DISABLE_SMTP -DCURL_DISABLE_TELNET -DCURL_DISABLE_TFTP
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
