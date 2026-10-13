// libcurl 7.78.0 with OpenSSL, zlib and zstd, protocols other than HTTP(S) and FILE disabled, compiled by Riot as C (several files per compilation unit: grouping not known yet): vtls.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32 -DHAVE_LIBZ -DHAVE_ZLIB_H -Itools/third_party/zlib-1.2.11 -DHAVE_ZSTD -DHAVE_ZSTD_H -Itools/third_party/zstd-1.4.9/lib -DCURL_DISABLE_DICT -DCURL_DISABLE_FTP -DCURL_DISABLE_GOPHER -DCURL_DISABLE_IMAP -DCURL_DISABLE_LDAP -DCURL_DISABLE_LDAPS -DCURL_DISABLE_MQTT -DCURL_DISABLE_POP3 -DCURL_DISABLE_RTSP -DCURL_DISABLE_SMB -DCURL_DISABLE_SMTP -DCURL_DISABLE_TELNET -DCURL_DISABLE_TFTP
// match: b7cc60 _multissl_version
// match: b7cdc0 _multissl_init
// match: b7cde0 _multissl_connect
// match: b7ce00 _multissl_connect_nonblocking
// match: b7ce20 _multissl_getsock
// match: b7ce40 _multissl_get_internals
// match: b7ce60 _multissl_close
// match: b80e90 _Curl_clone_primary_ssl_config
// match: b85f60 _Curl_free_primary_ssl_config
// match: b91880 _Curl_ssl_addsessionid
// match: b91f80 _Curl_ssl_delsessionid
// match: b92240 _Curl_ssl_getsock
// match: b922c0 _Curl_ssl_kill_session
// match: babf30 _ssl_connect_init_proxy
#include "../../../../tools/third_party/curl-7.78.0/lib/vtls/vtls.c"
