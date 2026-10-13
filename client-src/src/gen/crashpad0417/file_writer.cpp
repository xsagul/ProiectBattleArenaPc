// crashpad with mini_chromium (the copy inside sentry-native 0.4.17) and the sentry crashpad backend; C++17, frame pointers kept; prebuilt for the client with MSVC 14.31.31106: file_writer.cc, the functions of it that are in the client (tools/match_objs.py).
// tree: T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native = tools/third_party/sentry-native-0.4.17
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -EHsc -std:c++17 -Itools/third_party/sentry-native-0.4.17/external/crashpad -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium/mini_chromium -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/win -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_mac -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_elf -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/zlib/zlib -DNOMINMAX -DUNICODE -DWIN32_LEAN_AND_MEAN -D_CRT_SECURE_NO_WARNINGS -D_HAS_EXCEPTIONS=0 -D_UNICODE -DCRASHPAD_LSS_SOURCE_EMBEDDED -DNDEBUG -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium -DCRASHPAD_ZLIB_SOURCE_EMBEDDED
// match: ca9a70 ?Close@FileWriter@crashpad@@QAEXXZ
// match: ca9b40 ?Open@FileWriter@crashpad@@QAE_NABVFilePath@base@@W4FileWriteMode@2@W4FilePermissions@2@@Z
// match: ca9c90 ?Write@FileWriter@crashpad@@UAE_NPBXI@Z
// match: ca9cb0 ?Write@WeakFileHandleFileWriter@crashpad@@UAE_NPBXI@Z
// match: ca9cd0 ?WriteIoVec@FileWriter@crashpad@@UAE_NPAV?$vector@UWritableIoVec@crashpad@@V?$allocator@UWritableIoVec@crashpad@@@std@@@std@@@Z
// match: ca9cf0 ?WriteIoVec@WeakFileHandleFileWriter@crashpad@@UAE_NPAV?$vector@UWritableIoVec@crashpad@@V?$allocator@UWritableIoVec@crashpad@@@std@@@std@@@Z
#include "T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\external\crashpad\util\file\file_writer.cc"
