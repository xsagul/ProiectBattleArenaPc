// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_string.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c97cc0 _sentry__string_from_wstr
// match: c97d20 _sentry__stringbuilder_cleanup
// match: c97d40 _sentry__stringbuilder_init
// match: c97d60 _sentry__stringbuilder_into_string
// match: c97dc0 _sentry__stringbuilder_reserve
// match: c97e40 _sentry__unichar_to_utf8
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_string.c"
