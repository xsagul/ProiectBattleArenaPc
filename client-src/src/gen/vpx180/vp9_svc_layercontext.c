// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_svc_layercontext.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e8d430 _get_ref_frame_buffer
// match: eb93d0 _get_layer_context
// match: eb9450 _reset_fb_idx_unused
// match: eb9530 _set_flags_and_fb_idx_for_temporal_mode2
// match: eb96b0 _set_flags_and_fb_idx_for_temporal_mode3
// match: eb9900 _set_flags_and_fb_idx_for_temporal_mode_noLayering
// match: eb99d0 _vp9_free_svc_cyclic_refresh
// match: eb9a70 _vp9_inc_frame_in_layer
// match: eb9ab0 _vp9_init_layer_context
// match: eba0b0 _vp9_one_pass_cbr_svc_start_layer
// match: eba600 _vp9_restore_layer_context
// match: eba760 _vp9_save_layer_context
// match: eba850 _vp9_svc_adjust_frame_rate
// match: eba8b0 _vp9_svc_assert_constraints_pattern
// match: eba920 _vp9_svc_check_reset_layer_rc_flag
// match: eba9e0 _vp9_svc_check_spatial_layer_sync
// match: ebaa90 _vp9_svc_constrain_inter_layer_pred
// match: ebac50 _vp9_svc_lookahead_pop
// match: ebacb0 _vp9_svc_reset_temporal_layers
// match: ebaf50 _vp9_svc_update_ref_frame
// match: ebb210 _vp9_svc_update_ref_frame_bypass_mode
// match: ebb560 _vp9_update_layer_context_change_config
// match: ebb970 _vp9_update_temporal_layer_framerate
// match: f2f730 _vp9_is_scaled
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_svc_layercontext.c"
