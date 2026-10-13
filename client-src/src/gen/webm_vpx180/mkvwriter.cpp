// libwebm (the copy inside libvpx 1.8.0, GetVersion 0.2.1.0; frame pointers kept, C++ exceptions on), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): mkvwriter.cc, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -EHsc -Itools/third_party/libvpx-1.8.0/third_party/libwebm -Itools/third_party/libvpx-1.8.0 -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f3c2a0 ??0MkvWriter@mkvmuxer@@QAE@PAU_iobuf@@@Z
// match: f3c2d0 ??1MkvWriter@mkvmuxer@@UAE@XZ
// match: f3c300 ??_GMkvWriter@mkvmuxer@@UAEPAXI@Z
// match: f3c350 ?Close@MkvWriter@mkvmuxer@@QAEXXZ
// match: f3c380 ?Open@MkvWriter@mkvmuxer@@QAE_NPBD@Z
// match: f3c3c0 ?Position@MkvWriter@mkvmuxer@@UAEH_J@Z
// match: f3c3f0 ?Position@MkvWriter@mkvmuxer@@UBE_JXZ
// match: f3c410 ?Write@MkvWriter@mkvmuxer@@UAEHPBXI@Z
#include "../../../../tools/third_party/libvpx-1.8.0/third_party/libwebm/mkvmuxer/mkvwriter.cc"
