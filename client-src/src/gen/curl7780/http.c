// libcurl 7.78.0 with OpenSSL, zlib and zstd, protocols other than HTTP(S) and FILE disabled, compiled by Riot as C (several files per compilation unit: grouping not known yet): http.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32 -DHAVE_LIBZ -DHAVE_ZLIB_H -Itools/third_party/zlib-1.2.11 -DHAVE_ZSTD -DHAVE_ZSTD_H -Itools/third_party/zstd-1.4.9/lib -DCURL_DISABLE_DICT -DCURL_DISABLE_FTP -DCURL_DISABLE_GOPHER -DCURL_DISABLE_IMAP -DCURL_DISABLE_LDAP -DCURL_DISABLE_LDAPS -DCURL_DISABLE_MQTT -DCURL_DISABLE_POP3 -DCURL_DISABLE_RTSP -DCURL_DISABLE_SMB -DCURL_DISABLE_SMTP -DCURL_DISABLE_TELNET -DCURL_DISABLE_TFTP
// match: b7b0a0 _http_getsock_do
// match: b7b0f0 _https_getsock
// match: b7b120 _http_setup_conn
// match: b89b80 _Curl_http_host
// match: b8a000 _Curl_http_method
// match: b8a0b0 _Curl_http_output_auth
// match: ba2310 _http_should_fail
// match: ba7ec0 _pickoneauth
// match: bac590 _use_http_1_1plus
#include "../../../../tools/third_party/curl-7.78.0/lib/http.c"
