// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_pickmode.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ec19b0 _cyclic_refresh_segment_id_boosted
// match: f2cca0 _block_yrd
// match: f2d0f0 _calculate_tx_size
// match: f2d1d0 _calculate_variance
// match: f2d350 _combined_motion_search
// match: f2d750 _encode_breakout_test
// match: f2d980 _estimate_block_intra
// match: f2dae0 _find_predictors
// match: f2dd00 _get_force_skip_low_temp_var
// match: f2de90 _model_rd_for_sb_uv
// match: f2e010 _model_rd_for_sb_y
// match: f2e210 _model_rd_for_sb_y_large
// match: f2eaa0 _mv_refs_rt
// match: f2ef60 _scale_mv
// match: f2efa0 _search_filter_ref
// match: f2f270 _search_new_mv
// match: f2f5c0 _vp9_NEWMV_diff_bias
// match: f2f760 _vp9_pick_inter_mode
// match: f32270 _vp9_pick_inter_mode_sub8x8
// match: f32ea0 _vp9_pick_intra_mode
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_pickmode.c"
