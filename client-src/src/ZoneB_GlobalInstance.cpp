// The deleting destructors of the "global instance" base class (ZoneB_GlobalInstance.h), one per class that has such
// a base: each stores the base's table pointer, clears the class's global pointer and, when asked to, frees the 4
// bytes. What the classes are is not known; they are named after the rva of this destructor. Listed per function:
// the base's table (one entry) and the global pointer it clears.
//   rva 0x2da7c0  table 0x157931c  pointer 0x316fda8      rva 0x2da7f0  table 0x1579324  pointer 0x31767e0
//   rva 0x2da820  table 0x1579314  pointer 0x18d9ac8      rva 0x2da850  table 0x1579c48  pointer 0x3176864
//   rva 0x2da880  table 0x15795c0  pointer 0x2527284      rva 0x2da8b0  table 0x157a6c4  pointer 0x3172a60
//   rva 0x2da8e0  table 0x157966c  pointer 0x2527414      rva 0x2da910  table 0x15796b0  pointer 0x25272b8
//   rva 0x2da940  table 0x1579568  pointer 0x18d9ad0      rva 0x2da970  table 0x157a6cc  pointer 0x31768ac
//   rva 0x2da9a0  table 0x1579208  pointer 0x3171894      rva 0x2da9d0  table 0x1579b0c  pointer 0x317685c
//   rva 0x2daa00  table 0x157970c  pointer 0x3176834      rva 0x2daa30  table 0x15795d0  pointer 0x316f340
//   rva 0x2daa60  table 0x1579674  pointer 0x18d9b70      rva 0x2daa90  table 0x15796c4  pointer 0x3174648
//   rva 0x2daac0  table 0x15795c8  pointer 0x31731bc      rva 0x2daaf0  table 0x157a6c0  pointer 0x18d9b94
//   rva 0x2dab20  table 0x157a6d4  pointer 0x18d9b98      rva 0x2dab50  table 0x1579c20  pointer 0x3176860
// match: 2da7c0 ??_G?$GlobalInstance@UObject2da7c0@
// match: 2da7f0 ??_G?$GlobalInstance@UObject2da7f0@
// match: 2da820 ??_G?$GlobalInstance@UObject2da820@
// match: 2da850 ??_G?$GlobalInstance@UObject2da850@
// match: 2da880 ??_G?$GlobalInstance@UObject2da880@
// match: 2da8b0 ??_G?$GlobalInstance@UObject2da8b0@
// match: 2da8e0 ??_G?$GlobalInstance@UObject2da8e0@
// match: 2da910 ??_G?$GlobalInstance@UObject2da910@
// match: 2da940 ??_G?$GlobalInstance@UObject2da940@
// match: 2da970 ??_G?$GlobalInstance@UObject2da970@
// match: 2da9a0 ??_G?$GlobalInstance@UObject2da9a0@
// match: 2da9d0 ??_G?$GlobalInstance@UObject2da9d0@
// match: 2daa00 ??_G?$GlobalInstance@UObject2daa00@
// match: 2daa30 ??_G?$GlobalInstance@UObject2daa30@
// match: 2daa60 ??_G?$GlobalInstance@UObject2daa60@
// match: 2daa90 ??_G?$GlobalInstance@UObject2daa90@
// match: 2daac0 ??_G?$GlobalInstance@UObject2daac0@
// match: 2daaf0 ??_G?$GlobalInstance@UObject2daaf0@
// match: 2dab20 ??_G?$GlobalInstance@UObject2dab20@
// match: 2dab50 ??_G?$GlobalInstance@UObject2dab50@
#include "ZoneB_GlobalInstance.h"

struct Object2da7c0;
struct Object2da7f0;
struct Object2da820;
struct Object2da850;
struct Object2da880;
struct Object2da8b0;
struct Object2da8e0;
struct Object2da910;
struct Object2da940;
struct Object2da970;
struct Object2da9a0;
struct Object2da9d0;
struct Object2daa00;
struct Object2daa30;
struct Object2daa60;
struct Object2daa90;
struct Object2daac0;
struct Object2daaf0;
struct Object2dab20;
struct Object2dab50;

// Written out in full so that each base's table and deleting destructor exist in this file.
template struct GlobalInstance<Object2da7c0>;
template struct GlobalInstance<Object2da7f0>;
template struct GlobalInstance<Object2da820>;
template struct GlobalInstance<Object2da850>;
template struct GlobalInstance<Object2da880>;
template struct GlobalInstance<Object2da8b0>;
template struct GlobalInstance<Object2da8e0>;
template struct GlobalInstance<Object2da910>;
template struct GlobalInstance<Object2da940>;
template struct GlobalInstance<Object2da970>;
template struct GlobalInstance<Object2da9a0>;
template struct GlobalInstance<Object2da9d0>;
template struct GlobalInstance<Object2daa00>;
template struct GlobalInstance<Object2daa30>;
template struct GlobalInstance<Object2daa60>;
template struct GlobalInstance<Object2daa90>;
template struct GlobalInstance<Object2daac0>;
template struct GlobalInstance<Object2daaf0>;
template struct GlobalInstance<Object2dab20>;
template struct GlobalInstance<Object2dab50>;
