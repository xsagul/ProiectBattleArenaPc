// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_rd.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: eb6160 _fill_mode_costs
// match: eb6340 _modulate_rdmult
// match: eb63f0 _set_block_thresholds
// match: eb65d0 _vp9_compute_rd_mult
// match: eb65f0 _vp9_compute_rd_mult_based_on_qindex
// match: eb66b0 _vp9_get_adaptive_rdmult
// match: eb66f0 _vp9_get_entropy_contexts
// match: eb6880 _vp9_get_intra_cost_penalty
// match: eb68e0 _vp9_get_scaled_ref_frame
// match: eb6950 _vp9_get_switchable_rate
// match: eb69c0 _vp9_init_me_luts
// match: eb6a30 _vp9_initialize_me_consts
// match: eb6a60 _vp9_initialize_rd_consts
// match: eb6d80 _vp9_model_rd_from_var_lapndz
// match: eb6e90 _vp9_model_rd_from_var_lapndz_vec
// match: eb70f0 _vp9_mv_pred
// match: eb72c0 _vp9_raster_block_offset
// match: eb72f0 _vp9_raster_block_offset_int16
// match: eb7330 _vp9_rd_cost_init
// match: eb7360 _vp9_rd_cost_reset
// match: eb7390 _vp9_set_rd_speed_thresholds
// match: eb74f0 _vp9_set_rd_speed_thresholds_sub8x8
// match: eb7530 _vp9_setup_pred_block
// match: eb7600 _vp9_update_rd_thresh_fact
// match: ec41e0 _get_pred_context_switchable_interp
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_rd.c"
