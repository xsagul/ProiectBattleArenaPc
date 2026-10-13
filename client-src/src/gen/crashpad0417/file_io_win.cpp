// crashpad with mini_chromium (the copy inside sentry-native 0.4.17) and the sentry crashpad backend; C++17, frame pointers kept; prebuilt for the client with MSVC 14.31.31106: file_io_win.cc, the functions of it that are in the client (tools/match_objs.py).
// tree: T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native = tools/third_party/sentry-native-0.4.17
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -EHsc -std:c++17 -Itools/third_party/sentry-native-0.4.17/external/crashpad -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium/mini_chromium -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/win -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_mac -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_elf -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/zlib/zlib -DNOMINMAX -DUNICODE -DWIN32_LEAN_AND_MEAN -D_CRT_SECURE_NO_WARNINGS -D_HAS_EXCEPTIONS=0 -D_UNICODE -DCRASHPAD_LSS_SOURCE_EMBEDDED -DNDEBUG -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium -DCRASHPAD_ZLIB_SOURCE_EMBEDDED
// match: ca8d70 ?LoggingCloseFile@crashpad@@YA_NPAX@Z
// match: ca8e10 ?LoggingLockFile@crashpad@@YA?AW4FileLockingResult@1@PAXW4FileLocking@1@W4FileLockingBlocking@1@@Z
// match: ca8f10 ?LoggingOpenFileForRead@crashpad@@YAPAXABVFilePath@base@@@Z
// match: ca9070 ?LoggingOpenFileForReadAndWrite@crashpad@@YAPAXABVFilePath@base@@W4FileWriteMode@1@W4FilePermissions@1@@Z
// match: ca91c0 ?LoggingOpenFileForWrite@crashpad@@YAPAXABVFilePath@base@@W4FileWriteMode@1@W4FilePermissions@1@@Z
// match: ca9310 ?LoggingSeekFile@crashpad@@YA_JPAX_JH@Z
// match: ca9400 ?LoggingTruncateFile@crashpad@@YA_NPAX@Z
// match: ca9530 ?LoggingUnlockFile@crashpad@@YA_NPAX@Z
// match: ca95f0 ?NativeWriteFile@internal@crashpad@@YAJPAXPBXI@Z
// match: ca96b0 ?OpenFileForOutput@?A0x9565add9@crashpad@@YAPAXKABVFilePath@base@@W4FileWriteMode@2@W4FilePermissions@2@@Z
// match: ca9750 ?OpenFileForReadAndWrite@crashpad@@YAPAXABVFilePath@base@@W4FileWriteMode@1@W4FilePermissions@1@@Z
// match: ca9770 ?ReadFile@crashpad@@YAJPAX0I@Z
#include "T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\external\crashpad\util\file\file_io_win.cc"
