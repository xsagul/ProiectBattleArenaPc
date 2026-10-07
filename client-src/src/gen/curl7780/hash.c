// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: hash.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b87820 _Curl_hash_next_element
// match: ba1b60 _hash_element_dtor
#include "../../../../tools/third_party/curl-7.78.0/lib/hash.c"
