// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_context_tree.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e9e460 _alloc_mode_context
// match: e9e5a0 _alloc_tree_contexts
// match: e9e640 _free_mode_context
// match: e9e6d0 _vp9_free_pc_tree
// match: e9e7b0 _vp9_setup_pc_tree
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_context_tree.c"
