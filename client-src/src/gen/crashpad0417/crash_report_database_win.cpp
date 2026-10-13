// crashpad with mini_chromium (the copy inside sentry-native 0.4.17) and the sentry crashpad backend; C++17, frame pointers kept; prebuilt for the client with MSVC 14.31.31106: crash_report_database_win.cc, the functions of it that are in the client (tools/match_objs.py).
// tree: T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native = tools/third_party/sentry-native-0.4.17
// compiler: msvc-14.31.31106
// flags: -O2 -Oy- -EHsc -std:c++17 -Itools/third_party/sentry-native-0.4.17/external/crashpad -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium/mini_chromium -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/win -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_mac -Itools/third_party/sentry-native-0.4.17/external/crashpad/compat/non_elf -Itools/third_party/sentry-native-0.4.17/include -Itools/third_party/sentry-native-0.4.17/src -Itools/third_party/sentry-native-0.4.17/vendor -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/zlib/zlib -DNOMINMAX -DUNICODE -DWIN32_LEAN_AND_MEAN -D_CRT_SECURE_NO_WARNINGS -D_HAS_EXCEPTIONS=0 -D_UNICODE -DCRASHPAD_LSS_SOURCE_EMBEDDED -DNDEBUG -DSENTRY_BUILD_STATIC -DSENTRY_BACKEND_CRASHPAD -DSIZEOF_LONG=4 -DSENTRY_WITH_UNWINDER_DBGHELP -Itools/third_party/sentry-native-0.4.17/external/crashpad/third_party/mini_chromium -DCRASHPAD_ZLIB_SOURCE_EMBEDDED
// match: c9d9e0 ??$_Emplace_reallocate@ABUReport@CrashReportDatabase@crashpad@@@?$vector@UReport@CrashReportDatabase@crashpad@@V?$allocator@UReport@CrashReportDatabase@crashpad@@@std@@@std@@QAEPAUReport@CrashReportDatabase@crashpad@@QAU234@ABU234@@Z
// match: c9dc00 ??$_Emplace_reallocate@ABUReportDisk@?A0x83d91c9d@crashpad@@@?$vector@UReportDisk@?A0x83d91c9d@crashpad@@V?$allocator@UReportDisk@?A0x83d91c9d@crashpad@@@std@@@std@@QAEPAUReportDisk@?A0x83d91c9d@crashpad@@QAU234@ABU234@@Z
// match: c9deb0 ??$_Uninitialized_move@PAUReportDisk@?A0x83d91c9d@crashpad@@V?$allocator@UReportDisk@?A0x83d91c9d@crashpad@@@std@@@std@@YAPAUReportDisk@?A0x83d91c9d@crashpad@@QAU123@0PAU123@AAV?$allocator@UReportDisk@?A0x83d91c9d@crashpad@@@0@@Z
// match: c9e070 ??0ReportDisk@?A0x83d91c9d@crashpad@@QAE@ABUMetadataFileReportRecord@12@ABVFilePath@base@@ABV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z
// match: c9e2a0 ??1?$_Uninitialized_backout_al@V?$allocator@UReportDisk@?A0x83d91c9d@crashpad@@@std@@@std@@QAE@XZ
// match: c9e3f0 ??1?$unique_ptr@VNewReport@CrashReportDatabase@crashpad@@U?$default_delete@VNewReport@CrashReportDatabase@crashpad@@@std@@@std@@QAE@XZ
// match: c9e420 ?_Tidy@?$vector@UReportDisk@?A0x83d91c9d@crashpad@@V?$allocator@UReportDisk@?A0x83d91c9d@crashpad@@@std@@@std@@AAEXXZ
// match: c9e5d0 ??4Report@CrashReportDatabase@crashpad@@QAEAAU012@ABU012@@Z
// match: c9e790 ??_GCrashReportDatabaseWin@crashpad@@UAEPAXI@Z
// match: c9e7d0 ?AcquireMetadata@CrashReportDatabaseWin@crashpad@@AAE?AV?$unique_ptr@VMetadata@?A0x83d91c9d@crashpad@@U?$default_delete@VMetadata@?A0x83d91c9d@crashpad@@@std@@@std@@XZ
// match: c9e9d0 ?AddStringToTable@?A0x83d91c9d@crashpad@@YAIPAV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@ABV34@@Z
// match: c9eb00 ?CleanDatabase@CrashReportDatabaseWin@crashpad@@UAEH_J@Z
// match: c9ef90 ?CleanOrphanedAttachments@CrashReportDatabaseWin@crashpad@@AAEXXZ
// match: c9f3a0 ?Create@Metadata@?A0x83d91c9d@crashpad@@SA?AV?$unique_ptr@VMetadata@?A0x83d91c9d@crashpad@@U?$default_delete@VMetadata@?A0x83d91c9d@crashpad@@@std@@@std@@ABVFilePath@base@@00@Z
// match: c9f520 ?CreateDirectoryIfNecessary@?A0x83d91c9d@crashpad@@YA_NABVFilePath@base@@@Z
// match: c9f650 ?DatabasePath@CrashReportDatabaseWin@crashpad@@UAE?AVFilePath@base@@XZ
// match: c9f670 ?DeleteReport@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@ABUUUID@2@@Z
// match: c9f840 ?EnsureDirectory@?A0x83d91c9d@crashpad@@YA_NABVFilePath@base@@@Z
// match: c9fa00 ?FindReports@Metadata@?A0x83d91c9d@crashpad@@QBE?AW4OperationStatus@CrashReportDatabase@3@W4ReportState@23@PAV?$vector@UReport@CrashReportDatabase@crashpad@@V?$allocator@UReport@CrashReportDatabase@crashpad@@@std@@@std@@@Z
// match: c9fa70 ?FindSingleReport@Metadata@?A0x83d91c9d@crashpad@@QBE?AW4OperationStatus@CrashReportDatabase@3@ABUUUID@3@PAPBUReportDisk@23@@Z
// match: c9fb20 ?FindSingleReportAndMarkDirty@Metadata@?A0x83d91c9d@crashpad@@QAE?AW4OperationStatus@CrashReportDatabase@3@ABUUUID@3@W4ReportState@23@PAPAUReportDisk@23@@Z
// match: c9fbf0 ?FinishedWritingCrashReport@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@V?$unique_ptr@VNewReport@CrashReportDatabase@crashpad@@U?$default_delete@VNewReport@CrashReportDatabase@crashpad@@@std@@@std@@PAUUUID@2@@Z
// match: c9fe90 ?GetCompletedReports@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@PAV?$vector@UReport@CrashReportDatabase@crashpad@@V?$allocator@UReport@CrashReportDatabase@crashpad@@@std@@@std@@@Z
// match: c9ff00 ?GetPendingReports@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@PAV?$vector@UReport@CrashReportDatabase@crashpad@@V?$allocator@UReport@CrashReportDatabase@crashpad@@@std@@@std@@@Z
// match: c9ff70 ?GetReportForUploading@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@ABUUUID@2@PAV?$unique_ptr@$$CBVUploadReport@CrashReportDatabase@crashpad@@U?$default_delete@$$CBVUploadReport@CrashReportDatabase@crashpad@@@std@@@std@@_N@Z
// match: ca0080 ?Initialize@CrashReportDatabase@crashpad@@SA?AV?$unique_ptr@VCrashReportDatabase@crashpad@@U?$default_delete@VCrashReportDatabase@crashpad@@@std@@@std@@ABVFilePath@base@@@Z
// match: ca00a0 ?Initialize@CrashReportDatabaseWin@crashpad@@QAE_N_N@Z
// match: ca0250 ?InitializeInternal@crashpad@@YA?AV?$unique_ptr@VCrashReportDatabase@crashpad@@U?$default_delete@VCrashReportDatabase@crashpad@@@std@@@std@@ABVFilePath@base@@_N@Z
// match: ca0320 ?LookUpCrashReport@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@ABUUUID@2@PAUReport@42@@Z
// match: ca03a0 ?PrepareNewCrashReport@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@PAV?$unique_ptr@VNewReport@CrashReportDatabase@crashpad@@U?$default_delete@VNewReport@CrashReportDatabase@crashpad@@@std@@@std@@@Z
// match: ca0600 ?Read@Metadata@?A0x83d91c9d@crashpad@@AAEXXZ
// match: ca0eb0 ?RecordUploadAttempt@CrashReportDatabaseWin@crashpad@@EAE?AW4OperationStatus@CrashReportDatabase@2@PAVUploadReport@42@_NABV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z
// match: ca0fd0 ?RequestUpload@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@ABUUUID@2@@Z
// match: ca1090 ?SkipReportUpload@CrashReportDatabaseWin@crashpad@@UAE?AW4OperationStatus@CrashReportDatabase@2@ABUUUID@2@W4CrashSkippedReason@Metrics@2@@Z
// match: ca1120 ?Write@Metadata@?A0x83d91c9d@crashpad@@AAEXXZ
// match: ca18d0 ?allocate@?$allocator@UMetadataFileReportRecord@?A0x83d91c9d@crashpad@@@std@@QAEPAUMetadataFileReportRecord@?A0x83d91c9d@crashpad@@I@Z
// match: ca1940 ?erase@?$vector@UReportDisk@?A0x83d91c9d@crashpad@@V?$allocator@UReportDisk@?A0x83d91c9d@crashpad@@@std@@@std@@QAE?AV?$_Vector_iterator@V?$_Vector_val@U?$_Simple_types@UReportDisk@?A0x83d91c9d@crashpad@@@std@@@std@@@2@V?$_Vector_const_iterator@V?$_Vector_val@U?$_Simple_types@UReportDisk@?A0x83d91c9d@crashpad@@@std@@@std@@@2@@Z
#include "T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\external\crashpad\client\crash_report_database_win.cc"
