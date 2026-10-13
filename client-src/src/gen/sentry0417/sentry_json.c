// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_json.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c963b0 _can_write_item
// match: c96420 _decode_string_inplace
// match: c965d0 _jsmn_parse
// match: c96a00 _jsmn_parse_string
// match: c96b90 _read_escaped_unicode_char
// match: c96bf0 _sentry__jsonwriter_free
// match: c96c20 _sentry__jsonwriter_into_string
// match: c96c70 _sentry__jsonwriter_new
// match: c96cd0 _sentry__jsonwriter_write_bool
// match: c96d00 _sentry__jsonwriter_write_double
// match: c96dd0 _sentry__jsonwriter_write_int32
// match: c96e70 _sentry__jsonwriter_write_key
// match: c96ee0 _sentry__jsonwriter_write_list_end
// match: c96f40 _sentry__jsonwriter_write_list_start
// match: c96fc0 _sentry__jsonwriter_write_msec_timestamp
// match: c97020 _sentry__jsonwriter_write_null
// match: c97080 _sentry__jsonwriter_write_object_end
// match: c970e0 _sentry__jsonwriter_write_object_start
// match: c97160 _sentry__jsonwriter_write_str
// match: c97190 _sentry__jsonwriter_write_uuid
// match: c97240 _sentry__value_from_json
// match: c97300 _tokens_to_value
// match: c97630 _write_char
// match: c97690 _write_json_str
// match: c97c50 _write_str
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_json.c"
