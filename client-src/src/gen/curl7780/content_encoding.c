// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: content_encoding.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b7b790 _identity_init_writer
// match: b7b7b0 _identity_unencode_write
// match: b7b7e0 _client_init_writer
// match: b7b7f0 _client_unencode_write
#include "../../../../tools/third_party/curl-7.78.0/lib/content_encoding.c"
