// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_utils.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c940c0 _sentry__stringbuilder_append_buf
// match: c97ed0 _init_string_builder_for_url
// match: c98080 _sentry__dsn_decref
// match: c980e0 _sentry__dsn_get_minidump_url
// match: c981a0 _sentry__dsn_new
// match: c98380 _sentry__iso8601_to_msec
// match: c984c0 _sentry__msec_time_to_iso8601
// match: c98630 _sentry__snprintf_c
// match: c98730 _sentry__stringbuilder_append
// match: c987a0 _sentry__strtod_c
// match: c987f0 _sentry__url_parse
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_utils.c"
