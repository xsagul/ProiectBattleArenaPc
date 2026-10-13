// libcurl 7.78.0 with OpenSSL, zlib and zstd, protocols other than HTTP(S) and FILE disabled, compiled by Riot as C (several files per compilation unit: grouping not known yet): content_encoding.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32 -DHAVE_LIBZ -DHAVE_ZLIB_H -Itools/third_party/zlib-1.2.11 -DHAVE_ZSTD -DHAVE_ZSTD_H -Itools/third_party/zstd-1.4.9/lib -DCURL_DISABLE_DICT -DCURL_DISABLE_FTP -DCURL_DISABLE_GOPHER -DCURL_DISABLE_IMAP -DCURL_DISABLE_LDAP -DCURL_DISABLE_LDAPS -DCURL_DISABLE_MQTT -DCURL_DISABLE_POP3 -DCURL_DISABLE_RTSP -DCURL_DISABLE_SMB -DCURL_DISABLE_SMTP -DCURL_DISABLE_TELNET -DCURL_DISABLE_TFTP
// match: b7b190 _deflate_init_writer
// match: b7b210 _deflate_unencode_write
// match: b7b250 _gzip_close_writer
// match: b7b2a0 _gzip_init_writer
// match: b7b610 _zstd_init_writer
// match: b7b750 _zstd_close_writer
// match: b7b790 _identity_init_writer
// match: b7b7b0 _identity_unencode_write
// match: b7b7e0 _client_init_writer
// match: b7b7f0 _client_unencode_write
// match: b98980 _check_gzip_header
// match: ba26b0 _inflate_stream
// match: ba8080 _process_trailer
// match: ba8110 _process_zlib_error
#include "../../../../tools/third_party/curl-7.78.0/lib/content_encoding.c"
