// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_transport.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c94310 _sentry__transport_dump_queue
// match: c94350 _sentry__transport_send_envelope
// match: c943a0 _sentry__transport_shutdown
// match: c943e0 _sentry__transport_startup
// match: c94420 _sentry_transport_free
// match: c94450 _sentry_transport_new
// match: c94480 _sentry_transport_set_shutdown_func
// match: c94490 _sentry_transport_set_startup_func
// match: c944a0 _sentry_transport_set_state
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_transport.c"
