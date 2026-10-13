// libwebm (the copy inside libvpx 1.8.0, GetVersion 0.2.1.0; frame pointers kept, C++ exceptions on), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): mkvmuxerutil.cc, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -EHsc -Itools/third_party/libvpx-1.8.0/third_party/libwebm -Itools/third_party/libvpx-1.8.0 -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f3c660 ?EbmlDateElementSize@mkvmuxer@@YA_K_K@Z
// match: f3c680 ?EbmlElementSize@mkvmuxer@@YA_K_K00@Z
// match: f3c6d0 ?EbmlElementSize@mkvmuxer@@YA_K_K0@Z
// match: f3c710 ?EbmlElementSize@mkvmuxer@@YA_K_KM@Z
// match: f3c730 ?EbmlElementSize@mkvmuxer@@YA_K_KPBD@Z
// match: f3c790 ?EbmlElementSize@mkvmuxer@@YA_K_KPBE0@Z
// match: f3c7d0 ?EbmlMasterElementSize@mkvmuxer@@YA_K_K0@Z
// match: f3c800 ?GetCodedUIntSize@mkvmuxer@@YAH_K@Z
// match: f3c8a0 ?GetUIntSize@mkvmuxer@@YAH_K@Z
// match: f3c940 ?GetVersion@mkvmuxer@@YAXPAH000@Z
// match: f3c970 ?IsChromaSitingVertValueValid@mkvmuxer@@YA_N_K@Z
// match: f3c990 ?IsColourRangeValueValid@mkvmuxer@@YA_N_K@Z
// match: f3c9b0 ?IsMatrixCoefficientsValueValid@mkvmuxer@@YA_N_K@Z
// match: f3c9d0 ?IsPrimariesValueValid@mkvmuxer@@YA_N_K@Z
// match: f3ca00 ?IsTransferCharacteristicsValueValid@mkvmuxer@@YA_N_K@Z
// match: f3ca30 ?MakeUID@mkvmuxer@@YA_KPAI@Z
// match: f3ca80 ?SerializeInt@mkvmuxer@@YAHPAVIMkvWriter@1@_JH@Z
// match: f3caf0 ?WriteBlock@?A0xaa5bdd0a@mkvmuxer@@YA_KPAVIMkvWriter@2@QBVFrame@2@_J_K@Z
// match: f3cf80 ?WriteEbmlDateElement@mkvmuxer@@YA_NPAVIMkvWriter@1@_K_J@Z
// match: f3d000 ?WriteEbmlElement@mkvmuxer@@YA_NPAVIMkvWriter@1@_K11@Z
// match: f3d0b0 ?WriteEbmlElement@mkvmuxer@@YA_NPAVIMkvWriter@1@_K1@Z
// match: f3d140 ?WriteEbmlElement@mkvmuxer@@YA_NPAVIMkvWriter@1@_KM@Z
// match: f3d1e0 ?WriteEbmlElement@mkvmuxer@@YA_NPAVIMkvWriter@1@_KPBD@Z
// match: f3d250 ?WriteEbmlElement@mkvmuxer@@YA_NPAVIMkvWriter@1@_KPBE1@Z
// match: f3d2b0 ?WriteEbmlMasterElement@mkvmuxer@@YA_NPAVIMkvWriter@1@_K1@Z
// match: f3d310 ?WriteFrame@mkvmuxer@@YA_KPAVIMkvWriter@1@QBVFrame@1@PAVCluster@1@@Z
// match: f3d4f0 ?WriteID@mkvmuxer@@YAHPAVIMkvWriter@1@_K@Z
// match: f3d540 ?WriteUInt@mkvmuxer@@YAHPAVIMkvWriter@1@_K@Z
// match: f3d620 ?WriteUIntSize@mkvmuxer@@YAHPAVIMkvWriter@1@_KH@Z
// match: f3d700 ?WriteVoidElement@mkvmuxer@@YA_KPAVIMkvWriter@1@_K@Z
#include "../../../../tools/third_party/libvpx-1.8.0/third_party/libwebm/mkvmuxer/mkvmuxerutil.cc"
