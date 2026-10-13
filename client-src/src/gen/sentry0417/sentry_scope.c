// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_scope.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c9c810 _sentry__scope_apply_to_event
// match: c9d020 _sentry__scope_cleanup
// match: c9d100 _sentry__scope_flush_unlock
// match: c9d140 _sentry__scope_lock
// match: c9d340 _sentry__symbolize_frame
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_scope.c"
