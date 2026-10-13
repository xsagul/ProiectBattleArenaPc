// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_options.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c944b0 _sentry__options_incref
// match: c94520 _sentry_options_free
// match: c945e0 _sentry_options_get_dsn
// match: c94600 _sentry_options_get_environment
// match: c94610 _sentry_options_get_release
// match: c94780 _sentry_options_set_auto_session_tracking
// match: c947c0 _sentry_options_set_debug
// match: c947e0 _sentry_options_set_dsn
// match: c94800 _sentry_options_set_environment
// match: c94880 _sentry_options_set_logger
// match: c948a0 _sentry_options_set_release
// match: c94900 _sentry_options_set_require_user_consent
// match: c94920 _sentry_options_set_transport
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_options.c"
