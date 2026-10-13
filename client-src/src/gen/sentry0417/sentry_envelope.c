// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_envelope.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c939c0 _envelope_add_from_owned_buffer
// match: c93a40 _envelope_add_item
// match: c93aa0 _sentry__envelope_add_event
// match: c93bd0 _sentry__envelope_add_from_path
// match: c93c30 _sentry__envelope_add_session
// match: c93c90 _sentry__envelope_add_transaction
// match: c93e90 _sentry__envelope_from_path
// match: c93f00 _sentry__envelope_get_event_id
// match: c93f80 _sentry__envelope_new
// match: c94000 _sentry__envelope_serialize_item_into_stringbuilder
// match: c94120 _sentry_envelope_free
// match: c941a0 _sentry_envelope_serialize
// match: c94250 _sentry_envelope_write_to_path
#include "../../../../tools/third_party/sentry-native-0.4.17/src/sentry_envelope.c"
