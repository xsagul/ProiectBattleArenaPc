// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: mpack.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c95c00 _mpack_start_array
// match: c95ca0 _mpack_start_map
// match: c95d40 _mpack_write_bool
// match: c95d80 _mpack_write_cstr
// match: c95db0 _mpack_write_cstr_or_nil
// match: c95e10 _mpack_write_double
// match: c95e60 _mpack_write_i32
// match: c95fc0 _mpack_write_object_bytes
// match: c96000 _mpack_write_native_straddle
// match: c96080 _mpack_write_nil
// match: c960b0 _mpack_write_str
// match: c961f0 _mpack_writer_destroy
// match: c96240 _mpack_writer_ensure
// match: c962a0 _mpack_writer_flag_error
// match: c962d0 _mpack_writer_flush_unchecked
// match: c962f0 _mpack_writer_init_error
// match: c96330 _mpack_writer_init_growable
#include "../../../../tools/third_party/sentry-native-0.4.17/vendor/mpack.c"
