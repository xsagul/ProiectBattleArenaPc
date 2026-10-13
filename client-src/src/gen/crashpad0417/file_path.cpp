// crashpad with mini_chromium (the copy inside sentry-native 0.4.17) and the sentry crashpad backend; C++17, frame pointers kept; prebuilt for the client with MSVC 14.31.31106: file_path.cc, the functions of it that are in the client (tools/match_objs.py).
// tree: T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native = tools/third_party/sentry-native-0.4.17
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -EHsc -std:c++17 -Itools/third_party/sentry-native-0.4.17/external/crashpad -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium/mini_chromium -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/win -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_mac -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_elf -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/zlib/zlib -DNOMINMAX -DUNICODE -DWIN32_LEAN_AND_MEAN -D_CRT_SECURE_NO_WARNINGS -D_HAS_EXCEPTIONS=0 -D_UNICODE -DCRASHPAD_LSS_SOURCE_EMBEDDED -DNDEBUG -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium -DCRASHPAD_ZLIB_SOURCE_EMBEDDED
// match: caccc0 ??$?8_WU?$char_traits@_W@std@@V?$allocator@_W@1@@std@@YA_NABV?$basic_string@_WU?$char_traits@_W@std@@V?$allocator@_W@2@@0@0@Z
// match: cacd00 ??0FilePath@base@@QAE@ABV01@@Z
// match: cacd20 ??0FilePath@base@@QAE@ABV?$basic_string@_WU?$char_traits@_W@std@@V?$allocator@_W@2@@std@@@Z
// match: cacdd0 ??0FilePath@base@@QAE@XZ
// match: cace60 ??9FilePath@base@@QBE_NABV01@@Z
// match: cace80 ?Append@FilePath@base@@QBE?AV12@ABV12@@Z
// match: cacea0 ?Append@FilePath@base@@QBE?AV12@ABV?$basic_string@_WU?$char_traits@_W@std@@V?$allocator@_W@2@@std@@@Z
// match: cad0b0 ?BaseName@FilePath@base@@QBE?AV12@XZ
// match: cad180 ?DirName@FilePath@base@@QBE?AV12@XZ
// match: cad2e0 ?EqualDriveLetterCaseInsensitive@?A0xc6f3bbd8@base@@YA_NABV?$basic_string@_WU?$char_traits@_W@std@@V?$allocator@_W@2@@std@@0@Z
// match: cad410 ?FinalExtension@FilePath@base@@QBE?AV?$basic_string@_WU?$char_traits@_W@std@@V?$allocator@_W@2@@std@@XZ
// match: cad7b0 ?FindDriveLetter@?A0xc6f3bbd8@base@@YAIABV?$basic_string@_WU?$char_traits@_W@std@@V?$allocator@_W@2@@std@@@Z
// match: cad820 ?IsSeparator@FilePath@base@@SA_N_W@Z
// match: cad850 ?RemoveFinalExtension@FilePath@base@@QBE?AV12@XZ
// match: cad940 ?StripTrailingSeparatorsInternal@FilePath@base@@AAEXXZ
// match: cada20 ?erase@?$basic_string@_WU?$char_traits@_W@std@@V?$allocator@_W@2@@std@@QAEAAV12@II@Z
// match: cada80 ?find_last_of@?$basic_string@_WU?$char_traits@_W@std@@V?$allocator@_W@2@@std@@QBEIQB_WII@Z
#include "T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\external\crashpad\third_party\mini_chromium\mini_chromium\base\files\file_path.cc"
