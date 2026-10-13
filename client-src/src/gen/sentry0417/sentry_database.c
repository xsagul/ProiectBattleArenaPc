// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_database.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c9ba90 _sentry__has_crash_marker
// match: c9bad0 _sentry__process_old_runs
// match: c9bd50 _sentry__run_clean
// match: c9bd70 _sentry__run_clear_session
// match: c9bd90 _sentry__run_free
// match: c9bdc0 _sentry__run_new
// match: c9bf60 _sentry__run_write_envelope
// match: c9c020 _sentry__run_write_session
// match: c9c0a0 _sentry__write_crash_marker
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_database.c"
