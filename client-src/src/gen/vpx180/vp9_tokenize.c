// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_tokenize.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f28160 _has_high_freq_coeff
// match: f28190 _is_skippable
// match: f281b0 _set_entropy_context_b
// match: f28200 _tokenize_b
// match: f286d0 _vp9_has_high_freq_in_plane
// match: f28720 _vp9_is_skippable_in_plane
// match: f28770 _vp9_tokenize_sb
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_tokenize.c"
