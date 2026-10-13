// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_core.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c94940 _sentry__capture_envelope
// match: c949d0 _sentry__capture_event
// match: c94ca0 _sentry__ensure_event_id
// match: c94d40 _sentry__new_event_id
// match: c94d60 _sentry__options_getref
// match: c94df0 _sentry__prepare_event
// match: c95030 _sentry__should_skip_upload
// match: c950c0 _sentry_capture_event
// match: c95150 _sentry_close
// match: c95240 _sentry_handle_exception
// match: c952c0 _sentry_init
// match: c95580 _sentry_remove_extra
// match: c955b0 _sentry_remove_tag
// match: c955e0 _sentry_set_context
// match: c95610 _sentry_set_extra
// match: c95640 _sentry_set_tag
// match: c95680 _sentry_set_user
// match: c95750 _set_user_consent
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_core.c"
