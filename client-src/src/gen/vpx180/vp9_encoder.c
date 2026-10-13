// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_encoder.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e8b1c0 _dealloc_compressor_data
// match: e8b530 _encode_frame_to_data_rate
// match: e8c0a0 _encode_with_recode_loop
// match: e8c960 _encode_without_recode_loop
// match: e8d3a0 _get_free_fb
// match: e8d490 _init_gop_frames
// match: e8d890 _is_psnr_calc_enabled
// match: e8d8c0 _mc_flow_dispenser
// match: e8dc70 _mode_estimation
// match: e8e4b0 _realloc_segmentation_maps
// match: e8e5c0 _recode_loop_test
// match: e8e770 _release_scaled_references
// match: e8e8f0 _restore_coding_context
// match: e8e9d0 _save_coding_context
// match: e8ed60 _set_mv_search_params
// match: e8ee90 _set_tile_limits
// match: e8ef60 _setup_frame
// match: e8f050 _stack_push
// match: e8f080 _suppress_active_map
// match: e8f0d0 _tpl_model_update
// match: e8f430 _update_frame_size
// match: e8f5b0 _update_level_info
// match: e8fc30 _update_ref_frames
// match: e8fef0 _vp9_apply_encoding_flags
// match: e8ffc0 _vp9_change_config
// match: e90610 _vp9_copy_reference_enc
// match: e917b0 _vp9_get_active_map
// match: e92620 _vp9_get_level
// match: e926e0 _vp9_get_preview_raw_frame
// match: e92760 _vp9_get_quantizer
// match: e927b0 _vp9_new_framerate
// match: e927f0 _vp9_receive_raw_frame
// match: e92940 _vp9_remove_compressor
// match: e92aa0 _vp9_scale_if_required
// match: e92c00 _vp9_scale_references
// match: e92e80 _vp9_set_active_map
// match: e92f40 _vp9_set_internal_size
// match: e92fe0 _vp9_set_reference_enc
// match: e93030 _vp9_set_roi_map
// match: e93240 _vp9_set_row_mt
// match: e93310 _vp9_set_size_literal
// match: e93390 _vp9_set_svc
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_encoder.c"
