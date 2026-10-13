// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_speed_features.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e8d370 _frame_is_intra_only
// match: eb76b0 _set_good_speed_feature_framesize_dependent
// match: eb7a70 _set_good_speed_feature_framesize_independent
// match: eb8080 _set_rt_speed_feature_framesize_independent
// match: eb8c50 _vp9_set_speed_features_framesize_dependent
// match: eb8e90 _vp9_set_speed_features_framesize_independent
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_speed_features.c"
