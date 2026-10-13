// crashpad with mini_chromium (the copy inside sentry-native 0.4.17) and the sentry crashpad backend; C++17, frame pointers kept; prebuilt for the client with MSVC 14.31.31106: filesystem_win.cc, the functions of it that are in the client (tools/match_objs.py).
// tree: T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native = tools/third_party/sentry-native-0.4.17
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -EHsc -std:c++17 -Itools/third_party/sentry-native-0.4.17/external/crashpad -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium/mini_chromium -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/win -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_mac -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_elf -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/zlib/zlib -DNOMINMAX -DUNICODE -DWIN32_LEAN_AND_MEAN -D_CRT_SECURE_NO_WARNINGS -D_HAS_EXCEPTIONS=0 -D_UNICODE -DCRASHPAD_LSS_SOURCE_EMBEDDED -DNDEBUG -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium -DCRASHPAD_ZLIB_SOURCE_EMBEDDED
// match: caa540 ?FileModificationTime@crashpad@@YA_NABVFilePath@base@@PAUtimespec@@@Z
// match: caa730 ?GetDirectorySize@crashpad@@YA_KABVFilePath@base@@@Z
// match: caa880 ?GetFileSize@crashpad@@YA_KABVFilePath@base@@@Z
// match: caaae0 ?IsDirectory@crashpad@@YA_NABVFilePath@base@@_N@Z
// match: caac00 ?IsRegularFile@crashpad@@YA_NABVFilePath@base@@@Z
// match: caad10 ?LoggingRemoveDirectory@crashpad@@YA_NABVFilePath@base@@@Z
// match: caaf30 ?LoggingRemoveDirectoryImpl@?A0xc72a3301@crashpad@@YA_NABVFilePath@base@@@Z
// match: cab040 ?LoggingRemoveFile@crashpad@@YA_NABVFilePath@base@@@Z
#include "T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\external\crashpad\util\file\filesystem_win.cc"
