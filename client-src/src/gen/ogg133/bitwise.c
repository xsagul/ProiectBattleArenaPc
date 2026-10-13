// libogg (1.3.3 and 1.3.4 give the same functions; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): bitwise.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: f90d60 _oggpack_adv
// match: f90dc0 _oggpack_bytes
// match: f90df0 _oggpack_look
// match: f90eb0 _oggpack_read
// match: f90fa0 _oggpack_reset
// match: f90fd0 _oggpack_write
// match: f910f0 _oggpack_writeclear
// match: f91120 _oggpack_writeinit
// match: f91160 _oggpack_writetrunc
#include "../../../../tools/third_party/libogg-1.3.3/src/bitwise.c"
