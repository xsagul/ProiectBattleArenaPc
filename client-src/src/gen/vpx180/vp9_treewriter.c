// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_treewriter.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f295f0 _convert_distribution
// match: f29670 _tree2tok
// match: f296d0 _vp9_tokens_from_tree
// match: f296f0 _vp9_tree_probs_from_distribution
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_treewriter.c"
