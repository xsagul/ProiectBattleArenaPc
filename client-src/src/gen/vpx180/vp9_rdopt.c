// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_rdopt.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ecac90 _set_ref_ptrs
// match: ed0920 _block_rd_txfm
// match: ed0fb0 _check_best_zero_mv
// match: ed10c0 _choose_intra_uv_mode
// match: ed11a0 _choose_tx_size_from_rd
// match: ed1980 _cost_coeffs
// match: ed1dc0 _discount_newmv_test
// match: ed1e10 _dist_block
// match: ed2180 _encode_inter_mb_segment
// match: ed2670 _estimate_ref_frame_costs
// match: ed28b0 _handle_inter_mode
// match: ed3e20 _joint_motion_search
// match: ed43d0 _model_rd_for_sb
// match: ed49d0 _pixel_sse
// match: ed4b50 _rd_pick_best_sub8x8_mode
// match: ed5f10 _rd_pick_intra4x4block
// match: ed6720 _rd_pick_intra_sbuv_mode
// match: ed68a0 _rd_pick_intra_sby_mode
// match: ed6dc0 _set_and_cost_bmi_mvs
// match: ed6f50 _setup_buffer_inter
// match: ed70a0 _single_motion_search
// match: ed75e0 _store_coding_context
// match: ed7690 _super_block_uvrd
// match: ed7810 _super_block_yrd
// match: ed78c0 _swap_block_ptr
// match: ed7990 _txfm_rd_in_plane
// match: ed7b30 _vp9_active_edge_sb
// match: ed7bf0 _vp9_active_h_edge
// match: ed7c60 _vp9_active_v_edge
// match: ed8090 _vp9_get_skip_prob
// match: ed80d0 _vp9_get_token_cost
// match: ed8130 _vp9_internal_image_edge
// match: ed8170 _vp9_rd_pick_inter_mode_sb
// match: eda200 _vp9_rd_pick_inter_mode_sb_seg_skip
// match: eda450 _vp9_rd_pick_inter_mode_sub8x8
// match: edc6f0 _vp9_rd_pick_intra_mode_sb
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_rdopt.c"
