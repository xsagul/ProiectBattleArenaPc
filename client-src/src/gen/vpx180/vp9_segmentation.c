// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_segmentation.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ec42c0 _get_segment_id
// match: ecfdb0 _calc_segtree_probs
// match: ecffd0 _cost_segmap
// match: ed0170 _count_segs
// match: ed0330 _count_segs_sb
// match: ed04f0 _vp9_choose_segmap_coding_method
// match: ed0790 _vp9_disable_segfeature
// match: ed07b0 _vp9_disable_segmentation
// match: ed07d0 _vp9_enable_segmentation
// match: ed07f0 _vp9_psnr_aq_mode_setup
// match: ed0840 _vp9_reset_segment_features
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_segmentation.c"
