// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_mcomp.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ea4810 _accurate_sub_pel_search
// match: ea4930 _calc_int_cost_list
// match: ea4c70 _divide_and_round
// match: ea4d00 _exhuastive_mesh_search
// match: ea51d0 _full_pixel_diamond
// match: ea53e0 _full_pixel_exhaustive
// match: ea55a0 _get_cost_surf_min
// match: ea5670 _is_cost_list_wellbehaved
// match: ea5710 _mv_err_cost
// match: ea5780 _setup_center_error
// match: eb2310 _vp9_full_pixel_search
// match: eb2550 _vp9_get_mvpred_av_var
// match: eb25f0 _vp9_get_mvpred_var
// match: eb2690 _vp9_init3smotion_compensation
// match: eb2830 _vp9_init_dsmotion_compensation
// match: eb2940 _vp9_init_search_range
// match: eb2980 _vp9_int_pro_motion_estimation
// match: eb30f0 _vp9_mv_bit_cost
// match: eb3150 _vp9_pattern_search
// match: eb3c10 _vp9_pattern_search_sad
// match: eb4fb0 _vp9_refining_search_8p_c
// match: eb5240 _vp9_refining_search_sad
// match: eb5870 _vp9_set_mv_search_range
// match: eb5910 _vp9_set_subpel_mv_search_range
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_mcomp.c"
