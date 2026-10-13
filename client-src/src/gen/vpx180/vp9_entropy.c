// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_entropy.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e96920 _adapt_coef_probs
// match: e96bd0 _vp9_adapt_coef_probs
// match: e96c30 _vp9_default_coef_probs
// match: e96ca0 _vp9_model_to_full_probs
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_entropy.c"
