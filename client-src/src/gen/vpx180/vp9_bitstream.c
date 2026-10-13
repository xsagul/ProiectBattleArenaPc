// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_bitstream.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ebc400 _build_tree_distribution
// match: ebc620 _encode_segmentation
// match: ebc880 _encode_tiles_mt
// match: ebcbb0 _pack_inter_mode_mvs
// match: ebd230 _pack_mb_tokens
// match: ebd640 _update_coef_probs
// match: ebd710 _update_coef_probs_common
// match: ebddd0 _vp9_bitstream_encode_tiles_buffer_dealloc
// match: ebde40 _vp9_get_refresh_mask
// match: ebdf40 _vp9_pack_bitstream
// match: ebe320 _write_bitdepth_colorspace_sampling
// match: ebe3c0 _write_compressed_header
// match: ebea90 _write_frame_size
// match: ebead0 _write_mb_modes_kf
// match: ebecc0 _write_modes
// match: ebeda0 _write_modes_b
// match: ebeef0 _write_modes_sb
// match: ebf1d0 _write_render_size
// match: ebf240 _write_selected_tx_size
// match: ebf340 _write_skip
// match: ebf3c0 _write_uncompressed_header
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_bitstream.c"
