// libcurl 7.78.0 with OpenSSL, zlib and zstd, protocols other than HTTP(S) and FILE disabled, compiled by Riot as C (several files per compilation unit: grouping not known yet): altsvc.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32 -DHAVE_LIBZ -DHAVE_ZLIB_H -Itools/third_party/zlib-1.2.11 -DHAVE_ZSTD -DHAVE_ZSTD_H -Itools/third_party/zstd-1.4.9/lib -DCURL_DISABLE_DICT -DCURL_DISABLE_FTP -DCURL_DISABLE_GOPHER -DCURL_DISABLE_IMAP -DCURL_DISABLE_LDAP -DCURL_DISABLE_LDAPS -DCURL_DISABLE_MQTT -DCURL_DISABLE_POP3 -DCURL_DISABLE_RTSP -DCURL_DISABLE_SMB -DCURL_DISABLE_SMTP -DCURL_DISABLE_TELNET -DCURL_DISABLE_TFTP
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
