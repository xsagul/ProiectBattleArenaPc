// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: file.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b7cab0 _file_done
// match: b7cc30 _file_setup_connection
#include "../../../../tools/third_party/curl-7.78.0/lib/file.c"
