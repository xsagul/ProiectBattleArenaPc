// libcurl 7.78.0 with OpenSSL, compiled by Riot as C: url.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/curl-7.78.0/include -Itools/third_party/curl-7.78.0/lib -Itools/third_party/openssl-1.1.1m/include -DBUILDING_LIBCURL -DCURL_STATICLIB -DUSE_OPENSSL -DNDEBUG -DWIN32
// match: b86040 _Curl_free_request_state
// match: b8b480 _Curl_idnconvert_hostname
// match: b8dca0 _Curl_parse_login_details
// match: b98950 _call_extract_if_dead
// match: b991c0 _conn_reset_all_postponed_data
// match: d89ef0 _get_protocol_family
#include "../../../../tools/third_party/curl-7.78.0/lib/url.c"
