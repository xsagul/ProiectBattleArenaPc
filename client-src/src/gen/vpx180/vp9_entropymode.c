// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_entropymode.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e976a0 _tx_counts_to_branch_counts_16x16
// match: e976d0 _tx_counts_to_branch_counts_32x32
// match: e97710 _tx_counts_to_branch_counts_8x8
// match: e97730 _vp9_adapt_mode_probs
// match: e98700 _vp9_setup_past_independence
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_entropymode.c"
