// ba_host.dll: what starts the unpacked 13.3 client in place of the packer (stub.dll).
//
// The unpacked executable (tools/sponge/build_unpacked.py) imports one function, ba_start, and calls it before its
// own entry point. ba_start fills the game's import slots: the packer had removed the import list, so each slot's
// module and function come from the table read off the live process (ba_host_imports.h).
//
// Not filled: the 25 slots at rva 0xfb2808..0xfb2884 through which the game calls services of the packer itself.
// The game's wrappers test each for null and report "not available"; they stay null.
//
//   i686-w64-mingw32-clang -O2 -shared -o ba_host.dll ba_host.c
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ba_host_imports.h"

// --- the network sponge inside the client: the game's sendto / recvfrom slots get these in place of the system's.
// Each call is logged to ba_net.log: the bytes, and the return addresses found on the stack that point into the
// game's code right after a call instruction (the chain of game functions that led to the send).
#include <winsock2.h>
static int (WSAAPI* real_sendto)(SOCKET, const char*, int, int, const struct sockaddr*, int);
static int (WSAAPI* real_recvfrom)(SOCKET, char*, int, int, struct sockaddr*, int*);
static FILE* g_net;
static CRITICAL_SECTION g_net_lock;
static unsigned char* g_base;
static void net_log(const char* what, const unsigned char* buf, int len, const unsigned* stack) {
  if (!g_net) return;
  EnterCriticalSection(&g_net_lock);
  fprintf(g_net, "%lu %s thread %lu len %d:", (unsigned long)GetTickCount(), what, (unsigned long)GetCurrentThreadId(), len);
  for (int i = 0; i < len && i < 96; ++i) fprintf(g_net, " %02x", buf[i]);
  fprintf(g_net, "\n  from:");
  int found = 0;
  for (int i = 0; i < 700 && found < 14; ++i) {
    if (IsBadReadPtr(stack + i, 4)) break;
    const unsigned v = stack[i];
    const unsigned lo = (unsigned)(size_t)g_base + 0x1000, hi = (unsigned)(size_t)g_base + 0xfaa6ec;
    if (v < lo + 8 || v >= hi) continue;
    const unsigned char* r = (const unsigned char*)(size_t)v;
    // a return address: the instruction before it is a call (E8 rel32, or FF /2 in its 2, 3 and 6 byte forms)
    if (r[-5] == 0xe8 || (r[-2] == 0xff && (r[-1] & 0x38) == 0x10) || (r[-3] == 0xff && (r[-2] & 0x38) == 0x10) || (r[-6] == 0xff && (r[-5] & 0x38) == 0x10))
      fprintf(g_net, " %x", v - (unsigned)(size_t)g_base), ++found;
  }
  fprintf(g_net, "\n");
  fflush(g_net);
  LeaveCriticalSection(&g_net_lock);
}
static int WSAAPI my_sendto(SOCKET s, const char* buf, int len, int flags, const struct sockaddr* to, int tolen) {
  net_log("sendto", (const unsigned char*)buf, len, (const unsigned*)__builtin_frame_address(0));
  return real_sendto(s, buf, len, flags, to, tolen);
}
static int WSAAPI my_recvfrom(SOCKET s, char* buf, int len, int flags, struct sockaddr* from, int* fromlen) {
  const int n = real_recvfrom(s, buf, len, flags, from, fromlen);
  if (n > 0) net_log("recvfrom", (const unsigned char*)buf, n, (const unsigned*)__builtin_frame_address(0));
  return n;
}

// --- probes: a look at a game function's arguments each time it runs. The first bytes of the function (whole
// instructions, at least 5 bytes, none of them a relative jump or call) are moved to a trampoline that saves the
// registers, calls probe_hit, restores them, runs the moved instructions and jumps back. Nothing else changes.
// The list comes from ba_probes.txt next to the exe (written by tools/sponge/probe.py): "<rva hex> <len> <hits> <name>".
// Each hit logs the registers, the first stack words (return address, then arguments), the chain of game return
// addresses on the stack, and the memory at ecx and at each stack argument that is a readable pointer.
typedef struct { unsigned edi, esi, ebp, esp, ebx, edx, ecx, eax; } Regs;  // pushad's order, lowest address first
typedef struct { unsigned rva; int len; char name[64]; int left; } Probe;
static Probe g_probes[64];
static int g_probe_count;
static void dump(const char* what, const unsigned char* p, int n) {
  if (!p || IsBadReadPtr(p, (UINT_PTR)n)) return;
  fprintf(g_net, "  %s %p:", what, (void*)p);
  for (int i = 0; i < n; ++i) fprintf(g_net, " %02x", p[i]);
  fprintf(g_net, "\n");
}
static void __cdecl probe_hit(int index, const Regs* r) {
  Probe* p = &g_probes[index];
  if (!g_net || p->left <= 0) return;
  --p->left;
  EnterCriticalSection(&g_net_lock);
  fprintf(g_net, "%lu probe %x %s thread %lu eax %08x ecx %08x edx %08x ebx %08x esi %08x edi %08x ebp %08x\n", (unsigned long)GetTickCount(), p->rva,
          p->name, (unsigned long)GetCurrentThreadId(), r->eax, r->ecx, r->edx, r->ebx, r->esi, r->edi, r->ebp);
  const unsigned* stack = (const unsigned*)(size_t)r->esp;
  fprintf(g_net, "  stack:");
  for (int i = 0; i < 8; ++i) fprintf(g_net, " %08x", stack[i]);
  fprintf(g_net, "\n  from:");
  int found = 0;
  const unsigned lo = (unsigned)(size_t)g_base + 0x1000, hi = (unsigned)(size_t)g_base + 0xfaa6ec;
  for (int i = 0; i < 900 && found < 16; ++i) {
    if (IsBadReadPtr(stack + i, 4)) break;
    const unsigned v = stack[i];
    if (v < lo + 8 || v >= hi) continue;
    const unsigned char* c = (const unsigned char*)(size_t)v;
    if (c[-5] == 0xe8 || (c[-2] == 0xff && (c[-1] & 0x38) == 0x10) || (c[-3] == 0xff && (c[-2] & 0x38) == 0x10) || (c[-6] == 0xff && (c[-5] & 0x38) == 0x10))
      fprintf(g_net, " %x", v - (unsigned)(size_t)g_base), ++found;
  }
  fprintf(g_net, "\n");
  dump("ecx ->", (const unsigned char*)(size_t)r->ecx, 0x60);
  const char* chain = strchr(p->name, '@');  // "name@44,0": follow ecx -> [+0x44] -> [+0] and dump what it reaches
  if (chain) {
    unsigned v = r->ecx;
    const char* c = chain + 1;
    if (*c == 's') v = stack[c[1] - '0'], c += 2 + (c[2] == ',');  // "name@s1,0": start from stack word 1 instead
    for (; *c && v > 0x10000;) {
      unsigned off = (unsigned)strtoul(c, (char**)&c, 16);
      if (IsBadReadPtr((void*)(size_t)(v + off), 4)) { v = 0; break; }
      v = *(const unsigned*)(size_t)(v + off);
      fprintf(g_net, "  chain +%x -> %08x (rva %x)\n", off, v, v - (unsigned)(size_t)g_base);
      if (*c == ',') ++c;
    }
    if (v > 0x10000 && !IsBadReadPtr((void*)(size_t)v, 0x40)) {
      fprintf(g_net, "  chain end as rvas:");
      for (int i = 0; i < 16; ++i) fprintf(g_net, " %x", ((const unsigned*)(size_t)v)[i] - (unsigned)(size_t)g_base);
      fprintf(g_net, "\n");
    }
  }
  for (int i = 1; i <= 4; ++i) {
    char what[16];
    sprintf(what, "arg%d ->", i);
    if (stack[i] > 0x10000) dump(what, (const unsigned char*)(size_t)stack[i], 0x60);
  }
  fflush(g_net);
  LeaveCriticalSection(&g_net_lock);
}
static void install_probes(unsigned char* base) {
  FILE* f = fopen("ba_probes.txt", "r");
  if (!f) return;
  char line[256];
  while (g_probe_count < 64 && fgets(line, sizeof line, f)) {
    Probe* p = &g_probes[g_probe_count];
    if (sscanf(line, "%x %d %d %63[^\r\n]", &p->rva, &p->len, &p->left, p->name) == 4 && p->len >= 5 && p->len <= 24) ++g_probe_count;
  }
  fclose(f);
  const int n = g_probe_count;
  unsigned char* t = VirtualAlloc(NULL, 64 * (SIZE_T)(n + 1), MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  for (int i = 0; i < n && t; ++i, t += 64) {
    unsigned char* f = base + g_probes[i].rva;
    unsigned char* c = t;
    *c++ = 0x60;                                              // pushad
    *c++ = 0x9c;                                              // pushfd
    *c++ = 0x8d, *c++ = 0x44, *c++ = 0x24, *c++ = 0x04;       // lea eax, [esp + 4]: the saved registers
    *c++ = 0x50;                                              // push eax
    *c++ = 0x68, memcpy(c, &i, 4), c += 4;                    // push index
    *c++ = 0xe8;                                              // call probe_hit
    int rel = (int)((unsigned char*)probe_hit - (c + 4));
    memcpy(c, &rel, 4), c += 4;
    *c++ = 0x83, *c++ = 0xc4, *c++ = 0x08;                    // add esp, 8
    *c++ = 0x9d;                                              // popfd
    *c++ = 0x61;                                              // popad
    memcpy(c, f, (size_t)g_probes[i].len), c += g_probes[i].len;  // the moved instructions
    *c++ = 0xe9;                                              // jmp back
    rel = (int)((f + g_probes[i].len) - (c + 4));
    memcpy(c, &rel, 4);
    DWORD old = 0;
    VirtualProtect(f, 32, PAGE_EXECUTE_READWRITE, &old);
    f[0] = 0xe9;
    rel = (int)(t - (f + 5));
    memcpy(f + 1, &rel, 4);
    for (int k = 5; k < g_probes[i].len; ++k) f[k] = 0x90;
    VirtualProtect(f, 32, old, &old);
    FlushInstructionCache(GetCurrentProcess(), f, 32);
  }
}

__declspec(dllexport) void ba_start(void) {
  unsigned char* base = (unsigned char*)GetModuleHandleA(NULL);
  FILE* log = fopen("ba_host.log", "w");
  g_base = base;
  InitializeCriticalSection(&g_net_lock);
  g_net = fopen("ba_net.log", "w");
  const unsigned n = sizeof kImports / sizeof kImports[0];
  unsigned lo = ~0u, hi = 0, failed = 0;
  for (unsigned i = 0; i < n; ++i) {
    if (kImports[i].rva < lo) lo = kImports[i].rva;
    if (kImports[i].rva > hi) hi = kImports[i].rva;
  }
  DWORD old = 0;
  VirtualProtect(base + lo, hi + 4 - lo, PAGE_READWRITE, &old);
  for (unsigned i = 0; i < n; ++i) {
    HMODULE m = LoadLibraryA(kImports[i].dll);
    const char* name = kImports[i].name;
    FARPROC f = m ? GetProcAddress(m, name[0] == '#' ? (const char*)(size_t)atoi(name + 1) : name) : NULL;
    if (!f) {
      ++failed;
      if (log) fprintf(log, "not found: %s!%s (slot %08x)\n", kImports[i].dll, name, kImports[i].rva);
      continue;
    }
    if (!strcmp(name, "sendto")) real_sendto = (void*)f, f = (FARPROC)my_sendto;
    if (!strcmp(name, "recvfrom")) real_recvfrom = (void*)f, f = (FARPROC)my_recvfrom;
    *(FARPROC*)(base + kImports[i].rva) = f;
  }
  VirtualProtect(base + lo, hi + 4 - lo, old, &old);
  install_probes(base);
  if (log) {
    fprintf(log, "ba_host: base %p, %u import slots filled, %u not found\n", (void*)base, n - failed, failed);
    fclose(log);
  }
}
