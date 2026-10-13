// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_session.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c99c50 _sentry__end_current_session_with_status
// match: c99c90 _sentry__record_errors_on_current_session
// match: c99cc0 _sentry__session_free
// match: c99d00 _sentry__session_from_json
// match: c9a020 _sentry__session_from_path
// match: c9a060 _sentry__session_sync_user
// match: c9a0f0 _sentry__session_to_json
// match: c9a290 _sentry_end_session
// match: c9a320 _sentry_start_session
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_session.c"
