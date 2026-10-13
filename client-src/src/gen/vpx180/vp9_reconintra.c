// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_reconintra.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e9bab0 _build_intra_predictors
// match: e9bff0 _vp9_init_intra_predictors
// match: e9c250 _vp9_predict_intra_block
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_reconintra.c"
