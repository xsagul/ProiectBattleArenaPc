// sentry-native 0.4.17 (C part; frame pointers kept), prebuilt for the client with MSVC 14.31.31106: sentry_path_windows.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/curl-7.78.0/include -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS -DCURL_STATICLIB -DNDEBUG
// match: c98e30 _path_with_len
// match: c98e70 _sentry__filelock_try_lock
// match: c98ed0 _sentry__filelock_unlock
// match: c98f70 _sentry__path_absolute
// match: c98ff0 _sentry__path_append_str
// match: c990c0 _sentry__path_create_dir_all
// match: c991a0 _sentry__path_current_exe
// match: c99200 _sentry__path_dir
// match: c99240 _sentry__path_ends_with
// match: c992c0 _sentry__path_filename
// match: c99320 _sentry__path_filename_matches
// match: c99360 _sentry__path_from_str
// match: c993d0 _sentry__path_from_wstr
// match: c99430 _sentry__path_is_dir
// match: c99490 _sentry__path_is_file
// match: c994f0 _sentry__path_iter_directory
// match: c99520 _sentry__path_join_str
// match: c99560 _sentry__path_join_wstr
// match: c99710 _sentry__path_read_to_buffer
// match: c99840 _sentry__path_remove
// match: c998d0 _sentry__path_touch
// match: c99920 _sentry__pathiter_free
// match: c99950 _sentry__pathiter_next
// match: c99ad0 _write_buffer_with_mode
#include "../../../../tools/third_party/sentry-native-0.4.17/src/path/sentry_path_windows.c"
