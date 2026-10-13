// crashpad with mini_chromium (the copy inside sentry-native 0.4.17) and the sentry crashpad backend; C++17, frame pointers kept; prebuilt for the client with MSVC 14.31.31106: settings.cc, the functions of it that are in the client (tools/match_objs.py).
// tree: T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native = tools/third_party/sentry-native-0.4.17
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -EHsc -std:c++17 -Itools/third_party/sentry-native-0.4.17/external/crashpad -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium/mini_chromium -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/win -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_mac -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_elf -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/zlib/zlib -DNOMINMAX -DUNICODE -DWIN32_LEAN_AND_MEAN -D_CRT_SECURE_NO_WARNINGS -D_HAS_EXCEPTIONS=0 -D_UNICODE -DCRASHPAD_LSS_SOURCE_EMBEDDED -DNDEBUG -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium -DCRASHPAD_ZLIB_SOURCE_EMBEDDED
// match: ca6850 ??0Settings@crashpad@@QAE@XZ
// match: ca6870 ??1?$ScopedGeneric@PAXUScopedLockedFileHandleTraits@internal@crashpad@@@base@@QAE@XZ
// match: ca68e0 ?Initialize@Settings@crashpad@@QAE_NABVFilePath@base@@@Z
// match: ca69c0 ?MakeScopedLockedFileHandle@Settings@crashpad@@CA?AV?$ScopedGeneric@PAXUScopedLockedFileHandleTraits@internal@crashpad@@@base@@PAXW4FileLocking@2@ABVFilePath@4@@Z
// match: ca6a80 ?OpenForWritingAndReadSettings@Settings@crashpad@@AAE?AV?$ScopedGeneric@PAXUScopedLockedFileHandleTraits@internal@crashpad@@@base@@PAUData@12@@Z
// match: ca6c40 ?ReadSettings@Settings@crashpad@@AAE_NPAXPAUData@12@_N@Z
// match: ca6d80 ?RecoverSettings@Settings@crashpad@@AAE_NPAXPAUData@12@@Z
// match: ca6f30 ?SetLastUploadAttemptTime@Settings@crashpad@@QAE_N_J@Z
// match: ca7030 ?SetUploadsEnabled@Settings@crashpad@@QAE_N_N@Z
#include "T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\external\crashpad\client\settings.cc"
