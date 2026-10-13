// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_reconinter.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e9b230 _build_inter_predictors
// match: e9b630 _build_inter_predictors_for_planes
// match: e9b760 _mi_mv_pred_q2
// match: e9b7e0 _vp9_build_inter_predictor
// match: e9b890 _vp9_build_inter_predictors_sb
// match: e9b8b0 _vp9_build_inter_predictors_sbp
// match: e9b8d0 _vp9_build_inter_predictors_sbuv
// match: e9b8f0 _vp9_build_inter_predictors_sby
// match: e9b910 _vp9_setup_dst_planes
// match: e9b9c0 _vp9_setup_pre_planes
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_reconinter.c"
