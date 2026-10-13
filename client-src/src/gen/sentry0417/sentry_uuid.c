// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_uuid.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c95850 _sentry__uuid_from_native
// match: c958e0 _sentry_uuid_as_string
// match: c95950 _sentry_uuid_from_string
// match: c95a00 _sentry_uuid_is_nil
// match: c95a20 _sentry_uuid_new_v4
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_uuid.c"
