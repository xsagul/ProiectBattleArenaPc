// libcurl 7.78.0 with OpenSSL, zlib and zstd, protocols other than HTTP(S) and FILE disabled, compiled by Riot as C (several files per compilation unit: grouping not known yet): urlapi.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32 -DHAVE_LIBZ -DHAVE_ZLIB_H -Itools/third_party/zlib-1.2.11 -DHAVE_ZSTD -DHAVE_ZSTD_H -Itools/third_party/zstd-1.4.9/lib -DCURL_DISABLE_DICT -DCURL_DISABLE_FTP -DCURL_DISABLE_GOPHER -DCURL_DISABLE_IMAP -DCURL_DISABLE_LDAP -DCURL_DISABLE_LDAPS -DCURL_DISABLE_MQTT -DCURL_DISABLE_POP3 -DCURL_DISABLE_RTSP -DCURL_DISABLE_SMB -DCURL_DISABLE_SMTP -DCURL_DISABLE_TELNET -DCURL_DISABLE_TFTP
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
