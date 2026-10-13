// crashpad with mini_chromium (the copy inside sentry-native 0.4.17) and the sentry crashpad backend; C++17, frame pointers kept; prebuilt for the client with MSVC 14.31.31106: utf_string_conversion_utils.cc, the functions of it that are in the client (tools/match_objs.py).
// tree: T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native = tools/third_party/sentry-native-0.4.17
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -EHsc -std:c++17 -Itools/third_party/sentry-native-0.4.17/external/crashpad -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium/mini_chromium -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/win -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_mac -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_elf -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/zlib/zlib -DNOMINMAX -DUNICODE -DWIN32_LEAN_AND_MEAN -D_CRT_SECURE_NO_WARNINGS -D_HAS_EXCEPTIONS=0 -D_UNICODE -DCRASHPAD_LSS_SOURCE_EMBEDDED -DNDEBUG -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium -DCRASHPAD_ZLIB_SOURCE_EMBEDDED
// match: cadc00 ?resize@?$basic_string@_SU?$char_traits@_S@std@@V?$allocator@_S@2@@std@@QAEXI_S@Z
// match: caf0c0 ??$PrepareForUTF16Or32Output@V?$basic_string@_SU?$char_traits@_S@std@@V?$allocator@_S@2@@std@@@base@@YAXPBDIPAV?$basic_string@_SU?$char_traits@_S@std@@V?$allocator@_S@2@@std@@@Z
// match: caf100 ??$PrepareForUTF8Output@_W@base@@YAXPB_WIPAV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z
// match: caf150 ??$WriteUTF16Character@V?$basic_string@_SU?$char_traits@_S@std@@V?$allocator@_S@2@@std@@@?A0x0f7e21a4@base@@YAIIPAV?$basic_string@_SU?$char_traits@_S@std@@V?$allocator@_S@2@@std@@@Z
// match: caf300 ?ReadUnicodeCharacter@base@@YA_NPBDHPAHPAI@Z
// match: caf410 ?ReadUnicodeCharacter@base@@YA_NPB_SHPAHPAI@Z
// match: caf4a0 ?WriteUnicodeCharacter@base@@YAIIPAV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z
// match: caf710 ?append@?$basic_string@_SU?$char_traits@_S@std@@V?$allocator@_S@2@@std@@QAEAAV12@I_S@Z
// match: caf8b0 ?reserve@?$basic_string@_SU?$char_traits@_S@std@@V?$allocator@_S@2@@std@@QAEXI@Z
#include "T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\external\crashpad\third_party\mini_chromium\mini_chromium\base\strings\utf_string_conversion_utils.cc"
