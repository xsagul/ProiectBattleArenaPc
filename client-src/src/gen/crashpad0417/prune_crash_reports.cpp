// crashpad with mini_chromium (the copy inside sentry-native 0.4.17) and the sentry crashpad backend; C++17, frame pointers kept; prebuilt for the client with MSVC 14.31.31106: prune_crash_reports.cc, the functions of it that are in the client (tools/match_objs.py).
// tree: T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native = tools/third_party/sentry-native-0.4.17
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -EHsc -std:c++17 -Itools/third_party/sentry-native-0.4.17/external/crashpad -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium/mini_chromium -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/win -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_mac -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_elf -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/zlib/zlib -DNOMINMAX -DUNICODE -DWIN32_LEAN_AND_MEAN -D_CRT_SECURE_NO_WARNINGS -D_HAS_EXCEPTIONS=0 -D_UNICODE -DCRASHPAD_LSS_SOURCE_EMBEDDED -DNDEBUG -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium -DCRASHPAD_ZLIB_SOURCE_EMBEDDED
// match: c9de30 ??$_Uninitialized_move@PAUReport@CrashReportDatabase@crashpad@@V?$allocator@UReport@CrashReportDatabase@crashpad@@@std@@@std@@YAPAUReport@CrashReportDatabase@crashpad@@QAU123@0PAU123@AAV?$allocator@UReport@CrashReportDatabase@crashpad@@@0@@Z
// match: c9df30 ??0Report@CrashReportDatabase@crashpad@@QAE@$$QAU012@@Z
// match: c9dfd0 ??0Report@CrashReportDatabase@crashpad@@QAE@ABU012@@Z
// match: c9e270 ??1?$_Uninitialized_backout_al@V?$allocator@UReport@CrashReportDatabase@crashpad@@@std@@@std@@QAE@XZ
// match: ca4980 ??$_Insert_range@PAUReport@CrashReportDatabase@crashpad@@@?$vector@UReport@CrashReportDatabase@crashpad@@V?$allocator@UReport@CrashReportDatabase@crashpad@@@std@@@std@@AAEXV?$_Vector_const_iterator@V?$_Vector_val@U?$_Simple_types@UReport@CrashReportDatabase@crashpad@@@std@@@std@@@1@PAUReport@CrashReportDatabase@crashpad@@1Uforward_iterator_tag@1@@Z
// match: ca4c50 ??$_Insertion_sort_unchecked@PAUReport@CrashReportDatabase@crashpad@@V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@std@@YAPAUReport@CrashReportDatabase@crashpad@@QAU123@0V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@Z
// match: ca50d0 ??$_Med3_unchecked@PAUReport@CrashReportDatabase@crashpad@@V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@std@@YAXPAUReport@CrashReportDatabase@crashpad@@00V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@Z
// match: ca5140 ??$_Move_backward_unchecked@PAUReport@CrashReportDatabase@crashpad@@PAU123@@std@@YAPAUReport@CrashReportDatabase@crashpad@@PAU123@00@Z
// match: ca5240 ??$_Partition_by_median_guess_unchecked@PAUReport@CrashReportDatabase@crashpad@@V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@std@@YA?AU?$pair@PAUReport@CrashReportDatabase@crashpad@@PAU123@@0@PAUReport@CrashReportDatabase@crashpad@@0V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@Z
// match: ca5960 ??$_Pop_heap_hole_by_index@PAUReport@CrashReportDatabase@crashpad@@U123@V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@std@@YAXPAUReport@CrashReportDatabase@crashpad@@HH$$QAU123@V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@Z
// match: ca5c00 ??$_Sort_unchecked@PAUReport@CrashReportDatabase@crashpad@@V<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@std@@YAXPAUReport@CrashReportDatabase@crashpad@@0HV<lambda_bc9818bb182e8eeaa4516ffb74b7f28c>@@@Z
// match: ca5f80 ??$_Uninitialized_copy@PAUReport@CrashReportDatabase@crashpad@@V?$allocator@UReport@CrashReportDatabase@crashpad@@@std@@@std@@YAPAUReport@CrashReportDatabase@crashpad@@QAU123@0PAU123@AAV?$allocator@UReport@CrashReportDatabase@crashpad@@@0@@Z
// match: ca6060 ??$swap@UReport@CrashReportDatabase@crashpad@@$0A@@std@@YAXAAUReport@CrashReportDatabase@crashpad@@0@Z
// match: ca6120 ??0AgePruneCondition@crashpad@@QAE@H@Z
// match: ca6180 ??0BinaryPruneCondition@crashpad@@QAE@W4Operator@01@PAVPruneCondition@1@1@Z
// match: ca61b0 ??0DatabaseSizePruneCondition@crashpad@@QAE@I@Z
// match: ca6260 ??1BinaryPruneCondition@crashpad@@UAE@XZ
// match: ca6290 ??4Report@CrashReportDatabase@crashpad@@QAEAAU012@$$QAU012@@Z
// match: ca6360 ??_GBinaryPruneCondition@crashpad@@UAEPAXI@Z
// match: ca6410 ?PruneCrashReportDatabase@crashpad@@YAIPAVCrashReportDatabase@1@PAVPruneCondition@1@@Z
// match: ca6780 ?ShouldPruneReport@AgePruneCondition@crashpad@@UAE_NABUReport@CrashReportDatabase@2@@Z
// match: ca67b0 ?ShouldPruneReport@BinaryPruneCondition@crashpad@@UAE_NABUReport@CrashReportDatabase@2@@Z
// match: ca6820 ?ShouldPruneReport@DatabaseSizePruneCondition@crashpad@@UAE_NABUReport@CrashReportDatabase@2@@Z
#include "T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\external\crashpad\client\prune_crash_reports.cc"
