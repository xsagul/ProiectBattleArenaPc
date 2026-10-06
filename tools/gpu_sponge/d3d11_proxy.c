// The GPU sponge: a d3d11.dll for the 32-bit League client, placed next to its executable so Windows loads it instead
// of the system's. The client's import table is protected (stub.dll) and RenderDoc is not tolerated in the process, so
// the sponge does its own recording: it patches the method tables of the device, the immediate context and the swap
// chain the game creates, and writes what the game sends to the GPU.
//
// Always recorded (sponge/objects.bin): every shader's bytecode (sponge/shaders/<xxh64>.dxbc, matched later against
// ShaderCache.dx11.wad), every texture / buffer / state created and its description, the hash of each texture's initial
// data (matched later against the wad's textures).
// On request (a file sponge_capture.txt next to the game holding a frame count): for that many frames, every draw with
// the shaders, constant buffers, textures, samplers, states, vertex and index buffers bound at that moment, and the
// bytes written into every buffer (Map / Unmap, UpdateSubresource): sponge/frame_<n>.bin.
//
// File format (both files): records of [u32 type][u32 size][size bytes]; types in kRec*. Little endian, 32-bit pointers
// as object ids.
#define COBJMACROS
#define CINTERFACE
#include <windows.h>
#include <d3d11.h>
#include <dxgi.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum {
  kRecShader = 1,       // u32 object, u32 stage (0 vs, 1 ps, 2 gs, 3 hs, 4 ds, 5 cs), u64 hash, u32 size
  kRecTexture2D = 2,    // u32 object, D3D11_TEXTURE2D_DESC, u32 has_data, u64 hash of mip 0 rows (pitch-trimmed), u32 mip0 bytes
  kRecBuffer = 3,       // u32 object, D3D11_BUFFER_DESC, u32 has_data, u64 hash, then the initial bytes when small (<= 64 KiB)
  kRecBlend = 4,        // u32 object, D3D11_BLEND_DESC
  kRecDepth = 5,        // u32 object, D3D11_DEPTH_STENCIL_DESC
  kRecRaster = 6,       // u32 object, D3D11_RASTERIZER_DESC
  kRecSampler = 7,      // u32 object, D3D11_SAMPLER_DESC
  kRecInputLayout = 8,  // u32 object, u32 count, count x {char semantic[32], u32 index, u32 format, u32 slot, u32 offset, u32 class, u32 step}
  kRecSrv = 9,          // u32 view, u32 resource, D3D11_SHADER_RESOURCE_VIEW_DESC
  kRecFrame = 20,       // u32 frame number, u32 present count
  kRecWrite = 21,       // u32 resource, u32 offset, u32 size, bytes (Map/Unmap or UpdateSubresource)
  kRecDraw = 22,        // see write_draw
  kRecTopology = 23,    // u32 topology
  kRecTargets = 24,     // u32 count, u32 rtv[8], u32 dsv (OMSetRenderTargets)
  kRecClear = 25,       // u32 view, u32 kind (0 color, 1 depth), f32[4] color | f32 depth, u32 flags, u32 stencil
  kRecRtv = 10,         // u32 view, u32 resource (CreateRenderTargetView / CreateDepthStencilView: kind in high bit)
};

typedef HRESULT(WINAPI* CreateDeviceFn)(IDXGIAdapter*, D3D_DRIVER_TYPE, HMODULE, UINT, const D3D_FEATURE_LEVEL*, UINT, UINT, ID3D11Device**,
                                       D3D_FEATURE_LEVEL*, ID3D11DeviceContext**);
typedef HRESULT(WINAPI* CreateDeviceAndSwapChainFn)(IDXGIAdapter*, D3D_DRIVER_TYPE, HMODULE, UINT, const D3D_FEATURE_LEVEL*, UINT, UINT,
                                                     const DXGI_SWAP_CHAIN_DESC*, IDXGISwapChain**, ID3D11Device**, D3D_FEATURE_LEVEL*,
                                                     ID3D11DeviceContext**);

static HMODULE g_real;
static CreateDeviceFn g_create;
static CreateDeviceAndSwapChainFn g_create_sc;
static FILE* g_objects;   // always on
static FILE* g_frame;     // while capturing
static int g_capture_left, g_frame_no;
static unsigned g_presents;
static char g_dir[MAX_PATH];

static void say(const char* fmt, ...) {
  FILE* f = fopen("sponge_d3d11.log", "a");
  if (!f) return;
  va_list a;
  va_start(a, fmt);
  vfprintf(f, fmt, a);
  va_end(a);
  fputc('\n', f);
  fclose(f);
}

static uint64_t fnv64(const void* p, size_t n, uint64_t h) {
  const uint8_t* b = (const uint8_t*)p;
  for (size_t i = 0; i < n; ++i) h = (h ^ b[i]) * 0x100000001b3ull;
  return h;
}
#define FNV0 0xcbf29ce484222325ull

// XXH64 (xxHash, seed 0): the hash of shader bytecode and texture data, the same as Python's xxhash.xxh64
static const uint64_t P1 = 11400714785074694791ull, P2 = 14029467366897019727ull, P3 = 1609587929392839161ull, P4 = 9650029242287828579ull,
                      P5 = 2870177450012600261ull;
static uint64_t rotl(uint64_t x, int r) { return (x << r) | (x >> (64 - r)); }
static uint64_t rd64(const uint8_t* p) { uint64_t v; memcpy(&v, p, 8); return v; }
static uint32_t rd32(const uint8_t* p) { uint32_t v; memcpy(&v, p, 4); return v; }
static uint64_t round1(uint64_t acc, uint64_t in) { acc += in * P2; acc = rotl(acc, 31); return acc * P1; }
static uint64_t merge(uint64_t acc, uint64_t v) { acc ^= round1(0, v); return acc * P1 + P4; }
static uint64_t xxh64(const void* data, size_t len) {
  const uint8_t* p = (const uint8_t*)data;
  const uint8_t* end = p + len;
  uint64_t h;
  if (len >= 32) {
    uint64_t v1 = P1 + P2, v2 = P2, v3 = 0, v4 = 0 - P1;
    const uint8_t* limit = end - 32;
    do {
      v1 = round1(v1, rd64(p)), v2 = round1(v2, rd64(p + 8)), v3 = round1(v3, rd64(p + 16)), v4 = round1(v4, rd64(p + 24));
      p += 32;
    } while (p <= limit);
    h = rotl(v1, 1) + rotl(v2, 7) + rotl(v3, 12) + rotl(v4, 18);
    h = merge(h, v1), h = merge(h, v2), h = merge(h, v3), h = merge(h, v4);
  } else {
    h = P5;
  }
  h += (uint64_t)len;
  while (p + 8 <= end) h ^= round1(0, rd64(p)), h = rotl(h, 27) * P1 + P4, p += 8;
  if (p + 4 <= end) h ^= (uint64_t)rd32(p) * P1, h = rotl(h, 23) * P2 + P3, p += 4;
  while (p < end) h ^= (*p) * P5, h = rotl(h, 11) * P1, ++p;
  h ^= h >> 33, h *= P2, h ^= h >> 29, h *= P3, h ^= h >> 32;
  return h;
}

static void rec(FILE* f, uint32_t type, const void* a, uint32_t na, const void* b, uint32_t nb) {
  if (!f) return;
  uint32_t head[2] = {type, na + nb};
  fwrite(head, 4, 2, f);
  if (na) fwrite(a, 1, na, f);
  if (nb) fwrite(b, 1, nb, f);
}

// ---------------------------------------------------------------- the bound state the draws record
typedef struct {
  void *vs, *ps, *gs, *layout, *blend, *depth, *raster, *ib;
  uint32_t ib_format, ib_offset, topology, stencil_ref;
  void* vs_cb[14];
  void* ps_cb[14];
  void* ps_srv[16];
  void* vs_srv[8];
  void* ps_samp[16];
  void* vb[8];
  uint32_t vb_stride[8], vb_offset[8];
  float blend_factor[4];
  D3D11_VIEWPORT viewport;
} Bound;
static Bound g_bound;
static unsigned g_calls[64];  // context method calls by vtable index (diagnostics)

// buffers whose bytes this captured frame already holds (written while mapped, updated, or read back below)
static void* g_seen[8192];
static int g_seen_n;
static int seen(void* p) {
  for (int i = 0; i < g_seen_n; ++i)
    if (g_seen[i] == p) return 1;
  return 0;
}
static void mark(void* p) {
  if (g_seen_n < 8192 && !seen(p)) g_seen[g_seen_n++] = p;
}

static void write_draw(uint32_t kind, uint32_t count, uint32_t instances, uint32_t start, int32_t base_vertex, uint32_t start_instance) {
  uint32_t head[6] = {kind, count, instances, start, (uint32_t)base_vertex, start_instance};
  rec(g_frame, kRecDraw, head, sizeof head, &g_bound, sizeof g_bound);
}

// ---------------------------------------------------------------- method table patching
// every context method table we patched, with its own original entries: an interface's methods adjust `this` their
// own way, so a hook calls the original of the table it was called through
typedef HRESULT(STDMETHODCALLTYPE* QueryFn)(void*, REFIID, void**);
typedef struct { void** vt; void* orig[64]; } Table;
static Table g_tables[8];
static void* orig(void* self, int index) {
  void** vt = *(void***)self;
  for (int i = 0; i < 8; ++i)
    if (g_tables[i].vt == vt) return g_tables[i].orig[index];
  return g_tables[0].orig[index];
}
static void remember(void** vt) {
  for (int i = 0; i < 8; ++i) {
    if (g_tables[i].vt == vt) return;
    if (!g_tables[i].vt) {
      g_tables[i].vt = vt;
      memcpy(g_tables[i].orig, vt, sizeof g_tables[i].orig);
      return;
    }
  }
}

static void* patch(void** vtable, int index, void* fn) {
  DWORD old;
  void* prev = vtable[index];
  if (prev == fn) return NULL;
  VirtualProtect(&vtable[index], sizeof(void*), PAGE_EXECUTE_READWRITE, &old);
  vtable[index] = fn;
  VirtualProtect(&vtable[index], sizeof(void*), old, &old);
  return prev;
}

// --- device
typedef HRESULT(STDMETHODCALLTYPE* CreateBufferFn)(ID3D11Device*, const D3D11_BUFFER_DESC*, const D3D11_SUBRESOURCE_DATA*, ID3D11Buffer**);
typedef HRESULT(STDMETHODCALLTYPE* CreateTexture2DFn)(ID3D11Device*, const D3D11_TEXTURE2D_DESC*, const D3D11_SUBRESOURCE_DATA*, ID3D11Texture2D**);
typedef HRESULT(STDMETHODCALLTYPE* CreateSrvFn)(ID3D11Device*, ID3D11Resource*, const D3D11_SHADER_RESOURCE_VIEW_DESC*, ID3D11ShaderResourceView**);
typedef HRESULT(STDMETHODCALLTYPE* CreateLayoutFn)(ID3D11Device*, const D3D11_INPUT_ELEMENT_DESC*, UINT, const void*, SIZE_T, ID3D11InputLayout**);
typedef HRESULT(STDMETHODCALLTYPE* CreateShaderFn)(ID3D11Device*, const void*, SIZE_T, ID3D11ClassLinkage*, void**);
typedef HRESULT(STDMETHODCALLTYPE* CreateStateFn)(ID3D11Device*, const void*, void**);
static CreateBufferFn o_CreateBuffer;
static CreateTexture2DFn o_CreateTexture2D;
static CreateSrvFn o_CreateSrv;
typedef HRESULT(STDMETHODCALLTYPE* CreateViewFn)(ID3D11Device*, ID3D11Resource*, const void*, void**);
static CreateViewFn o_CreateRtv, o_CreateDsv;
static HRESULT STDMETHODCALLTYPE h_CreateRtv(ID3D11Device* d, ID3D11Resource* res, const void* desc, void** out) {
  HRESULT r = o_CreateRtv(d, res, desc, out);
  if (SUCCEEDED(r) && out) { uint32_t v[3] = {(uint32_t)(uintptr_t)*out, (uint32_t)(uintptr_t)res, 0}; rec(g_objects, kRecRtv, v, sizeof v, NULL, 0); }
  return r;
}
static HRESULT STDMETHODCALLTYPE h_CreateDsv(ID3D11Device* d, ID3D11Resource* res, const void* desc, void** out) {
  HRESULT r = o_CreateDsv(d, res, desc, out);
  if (SUCCEEDED(r) && out) { uint32_t v[3] = {(uint32_t)(uintptr_t)*out, (uint32_t)(uintptr_t)res, 1}; rec(g_objects, kRecRtv, v, sizeof v, NULL, 0); }
  return r;
}
static CreateLayoutFn o_CreateLayout;
static CreateShaderFn o_CreateVS, o_CreatePS, o_CreateGS;
static CreateStateFn o_CreateBlend, o_CreateDepth, o_CreateRaster, o_CreateSampler;

static void save_shader(void* obj, uint32_t stage, const void* code, SIZE_T size) {
  uint64_t h = xxh64(code, size);
  struct { uint32_t obj, stage; uint64_t hash; uint32_t size; } r = {(uint32_t)(uintptr_t)obj, stage, h, (uint32_t)size};
  rec(g_objects, kRecShader, &r, sizeof r, NULL, 0);
  char path[MAX_PATH];
  snprintf(path, sizeof path, "%s\\shaders\\%016llx.dxbc", g_dir, (unsigned long long)h);
  if (GetFileAttributesA(path) == INVALID_FILE_ATTRIBUTES) {
    FILE* f = fopen(path, "wb");
    if (f) fwrite(code, 1, size, f), fclose(f);
  }
}
static HRESULT STDMETHODCALLTYPE h_CreateVS(ID3D11Device* d, const void* c, SIZE_T n, ID3D11ClassLinkage* l, void** out) {
  HRESULT r = o_CreateVS(d, c, n, l, out);
  if (SUCCEEDED(r) && out) save_shader(*out, 0, c, n);
  return r;
}
static HRESULT STDMETHODCALLTYPE h_CreatePS(ID3D11Device* d, const void* c, SIZE_T n, ID3D11ClassLinkage* l, void** out) {
  HRESULT r = o_CreatePS(d, c, n, l, out);
  if (SUCCEEDED(r) && out) save_shader(*out, 1, c, n);
  return r;
}
static HRESULT STDMETHODCALLTYPE h_CreateGS(ID3D11Device* d, const void* c, SIZE_T n, ID3D11ClassLinkage* l, void** out) {
  HRESULT r = o_CreateGS(d, c, n, l, out);
  if (SUCCEEDED(r) && out) save_shader(*out, 2, c, n);
  return r;
}
static HRESULT STDMETHODCALLTYPE h_CreateBuffer(ID3D11Device* d, const D3D11_BUFFER_DESC* desc, const D3D11_SUBRESOURCE_DATA* init, ID3D11Buffer** out) {
  HRESULT r = o_CreateBuffer(d, desc, init, out);
  if (SUCCEEDED(r) && out && desc) {
    struct { uint32_t obj; D3D11_BUFFER_DESC desc; uint32_t has; uint64_t hash; } h = {(uint32_t)(uintptr_t)*out, *desc, init != NULL, 0};
    if (init && init->pSysMem) h.hash = xxh64(init->pSysMem, desc->ByteWidth);
    const uint32_t keep = init && init->pSysMem && desc->ByteWidth <= 65536 ? desc->ByteWidth : 0;
    rec(g_objects, kRecBuffer, &h, sizeof h, keep ? init->pSysMem : NULL, keep);
  }
  return r;
}
static uint32_t block_rows(DXGI_FORMAT f, uint32_t height) {
  // block-compressed formats store 4 rows of pixels per row of blocks
  if ((f >= DXGI_FORMAT_BC1_TYPELESS && f <= DXGI_FORMAT_BC5_SNORM) || (f >= DXGI_FORMAT_BC6H_TYPELESS && f <= DXGI_FORMAT_BC7_UNORM_SRGB))
    return (height + 3) / 4;
  return height;
}
static HRESULT STDMETHODCALLTYPE h_CreateTexture2D(ID3D11Device* d, const D3D11_TEXTURE2D_DESC* desc, const D3D11_SUBRESOURCE_DATA* init,
                                                   ID3D11Texture2D** out) {
  HRESULT r = o_CreateTexture2D(d, desc, init, out);
  if (SUCCEEDED(r) && out && desc) {
    struct { uint32_t obj; D3D11_TEXTURE2D_DESC desc; uint32_t has; uint64_t hash; uint32_t bytes; } h = {(uint32_t)(uintptr_t)*out, *desc, init != NULL, 0, 0};
    if (init && init->pSysMem) {
      const uint32_t rows = block_rows(desc->Format, desc->Height);
      h.bytes = init->SysMemPitch * rows;
      h.hash = xxh64(init->pSysMem, h.bytes);
    }
    rec(g_objects, kRecTexture2D, &h, sizeof h, NULL, 0);
  }
  return r;
}
static HRESULT STDMETHODCALLTYPE h_CreateSrv(ID3D11Device* d, ID3D11Resource* res, const D3D11_SHADER_RESOURCE_VIEW_DESC* desc, ID3D11ShaderResourceView** out) {
  HRESULT r = o_CreateSrv(d, res, desc, out);
  if (SUCCEEDED(r) && out) {
    struct { uint32_t view, res; D3D11_SHADER_RESOURCE_VIEW_DESC desc; } h = {(uint32_t)(uintptr_t)*out, (uint32_t)(uintptr_t)res, {0}};
    if (desc) h.desc = *desc;
    rec(g_objects, kRecSrv, &h, sizeof h, NULL, 0);
  }
  return r;
}
static HRESULT STDMETHODCALLTYPE h_CreateLayout(ID3D11Device* d, const D3D11_INPUT_ELEMENT_DESC* e, UINT n, const void* code, SIZE_T size, ID3D11InputLayout** out) {
  HRESULT r = o_CreateLayout(d, e, n, code, size, out);
  if (SUCCEEDED(r) && out && g_objects) {
    uint32_t head[2] = {(uint32_t)(uintptr_t)*out, n};
    uint32_t total = 8 + n * (32 + 24);
    uint32_t h2[2] = {kRecInputLayout, total};
    fwrite(h2, 4, 2, g_objects), fwrite(head, 4, 2, g_objects);
    for (UINT i = 0; i < n; ++i) {
      char sem[32] = {0};
      strncpy(sem, e[i].SemanticName ? e[i].SemanticName : "", 31);
      uint32_t v[6] = {e[i].SemanticIndex, (uint32_t)e[i].Format, e[i].InputSlot, e[i].AlignedByteOffset, (uint32_t)e[i].InputSlotClass, e[i].InstanceDataStepRate};
      fwrite(sem, 1, 32, g_objects), fwrite(v, 4, 6, g_objects);
    }
  }
  return r;
}
#define STATE_HOOK(NAME, DESC, TYPE)                                                              \
  static HRESULT STDMETHODCALLTYPE h_##NAME(ID3D11Device* d, const void* desc, void** out) {      \
    HRESULT r = o_##NAME(d, desc, out);                                                           \
    if (SUCCEEDED(r) && out && desc) {                                                            \
      uint32_t obj = (uint32_t)(uintptr_t)*out;                                                   \
      rec(g_objects, TYPE, &obj, 4, desc, sizeof(DESC));                                          \
    }                                                                                             \
    return r;                                                                                     \
  }
STATE_HOOK(CreateBlend, D3D11_BLEND_DESC, kRecBlend)
STATE_HOOK(CreateDepth, D3D11_DEPTH_STENCIL_DESC, kRecDepth)
STATE_HOOK(CreateRaster, D3D11_RASTERIZER_DESC, kRecRaster)
STATE_HOOK(CreateSampler, D3D11_SAMPLER_DESC, kRecSampler)

// --- immediate context

// The D3D11 runtime rewrites the draw entries of the context's own method table as its state changes (it keeps
// variants of each draw for the state it is in), overwriting our hooks. After every call we see, take whatever it
// wrote as the new original and put the hook back.
static void STDMETHODCALLTYPE h_DrawIndexed(ID3D11DeviceContext*, UINT, UINT, INT);
static void STDMETHODCALLTYPE h_Draw(ID3D11DeviceContext*, UINT, UINT);
static void STDMETHODCALLTYPE h_DrawIndexedInstanced(ID3D11DeviceContext*, UINT, UINT, UINT, INT, UINT);
static void STDMETHODCALLTYPE h_DrawInstanced(ID3D11DeviceContext*, UINT, UINT, UINT, UINT);
static unsigned g_rewrites;
static void refresh(void* self) {
  void** vt = *(void***)self;
  Table* t = NULL;
  for (int i = 0; i < 8; ++i)
    if (g_tables[i].vt == vt) t = &g_tables[i];
  if (!t) return;
  static const int idx[4] = {12, 13, 20, 21};
  void* hooks[4] = {(void*)h_DrawIndexed, (void*)h_Draw, (void*)h_DrawIndexedInstanced, (void*)h_DrawInstanced};
  for (int k = 0; k < 4; ++k)
    if (vt[idx[k]] != hooks[k]) {
      t->orig[idx[k]] = vt[idx[k]];
      DWORD old;
      VirtualProtect(&vt[idx[k]], sizeof(void*), PAGE_EXECUTE_READWRITE, &old);
      vt[idx[k]] = hooks[k];
      VirtualProtect(&vt[idx[k]], sizeof(void*), old, &old);
      ++g_rewrites;
    }
}
typedef void(STDMETHODCALLTYPE* SetBuffersFn)(ID3D11DeviceContext*, UINT, UINT, void* const*);
typedef void(STDMETHODCALLTYPE* SetShaderFn)(ID3D11DeviceContext*, void*, void* const*, UINT);
typedef void(STDMETHODCALLTYPE* DrawIndexedFn)(ID3D11DeviceContext*, UINT, UINT, INT);
typedef void(STDMETHODCALLTYPE* DrawFn)(ID3D11DeviceContext*, UINT, UINT);
typedef void(STDMETHODCALLTYPE* DrawIndexedInstancedFn)(ID3D11DeviceContext*, UINT, UINT, UINT, INT, UINT);
typedef void(STDMETHODCALLTYPE* DrawInstancedFn)(ID3D11DeviceContext*, UINT, UINT, UINT, UINT);
typedef HRESULT(STDMETHODCALLTYPE* MapFn)(ID3D11DeviceContext*, ID3D11Resource*, UINT, D3D11_MAP, UINT, D3D11_MAPPED_SUBRESOURCE*);
typedef void(STDMETHODCALLTYPE* UnmapFn)(ID3D11DeviceContext*, ID3D11Resource*, UINT);
typedef void(STDMETHODCALLTYPE* SetLayoutFn)(ID3D11DeviceContext*, void*);
typedef void(STDMETHODCALLTYPE* SetVbFn)(ID3D11DeviceContext*, UINT, UINT, void* const*, const UINT*, const UINT*);
typedef void(STDMETHODCALLTYPE* SetIbFn)(ID3D11DeviceContext*, void*, DXGI_FORMAT, UINT);
typedef void(STDMETHODCALLTYPE* SetTopologyFn)(ID3D11DeviceContext*, D3D11_PRIMITIVE_TOPOLOGY);
typedef void(STDMETHODCALLTYPE* SetBlendFn)(ID3D11DeviceContext*, void*, const FLOAT[4], UINT);
typedef void(STDMETHODCALLTYPE* SetDepthFn)(ID3D11DeviceContext*, void*, UINT);
typedef void(STDMETHODCALLTYPE* SetRasterFn)(ID3D11DeviceContext*, void*);
typedef void(STDMETHODCALLTYPE* SetViewportsFn)(ID3D11DeviceContext*, UINT, const D3D11_VIEWPORT*);
typedef void(STDMETHODCALLTYPE* UpdateSubresourceFn)(ID3D11DeviceContext*, ID3D11Resource*, UINT, const D3D11_BOX*, const void*, UINT, UINT);
static SetBuffersFn o_VSSetCB, o_PSSetCB, o_PSSetSRV, o_VSSetSRV, o_PSSetSamp;
static SetShaderFn o_PSSetShader, o_VSSetShader, o_GSSetShader;
static DrawIndexedFn o_DrawIndexed;
static DrawFn o_Draw;
static DrawIndexedInstancedFn o_DrawIndexedInstanced;
static DrawInstancedFn o_DrawInstanced;
static MapFn o_Map;
static UnmapFn o_Unmap;
static SetLayoutFn o_SetLayout;
static SetVbFn o_SetVb;
static SetIbFn o_SetIb;
static SetTopologyFn o_SetTopology;
static SetBlendFn o_SetBlend;
static SetDepthFn o_SetDepth;
static SetRasterFn o_SetRaster;
static void* o_SetTargets; static void* o_ClearRtv; static void* o_ClearDsv;
static SetViewportsFn o_SetViewports;
static UpdateSubresourceFn o_UpdateSubresource;

static void copy_slots(void** dst, UINT cap, UINT start, UINT n, void* const* src) {
  for (UINT i = 0; i < n && start + i < cap; ++i) dst[start + i] = src ? src[i] : NULL;
}
static void STDMETHODCALLTYPE h_VSSetCB(ID3D11DeviceContext* c, UINT s, UINT n, void* const* b) { ++g_calls[7]; copy_slots(g_bound.vs_cb, 14, s, n, b), ((SetBuffersFn)orig(c, 7))(c, s, n, b); refresh(c); }
static void STDMETHODCALLTYPE h_PSSetCB(ID3D11DeviceContext* c, UINT s, UINT n, void* const* b) { copy_slots(g_bound.ps_cb, 14, s, n, b), ((SetBuffersFn)orig(c, 16))(c, s, n, b); refresh(c); }
static void STDMETHODCALLTYPE h_PSSetSRV(ID3D11DeviceContext* c, UINT s, UINT n, void* const* b) { copy_slots(g_bound.ps_srv, 16, s, n, b), ((SetBuffersFn)orig(c, 8))(c, s, n, b); refresh(c); }
static void STDMETHODCALLTYPE h_VSSetSRV(ID3D11DeviceContext* c, UINT s, UINT n, void* const* b) { copy_slots(g_bound.vs_srv, 8, s, n, b), ((SetBuffersFn)orig(c, 25))(c, s, n, b); refresh(c); }
static void STDMETHODCALLTYPE h_PSSetSamp(ID3D11DeviceContext* c, UINT s, UINT n, void* const* b) { copy_slots(g_bound.ps_samp, 16, s, n, b), ((SetBuffersFn)orig(c, 10))(c, s, n, b); refresh(c); }
static void STDMETHODCALLTYPE h_PSSetShader(ID3D11DeviceContext* c, void* sh, void* const* ci, UINT n) { ++g_calls[9]; g_bound.ps = sh, ((SetShaderFn)orig(c, 9))(c, sh, ci, n); refresh(c); }
static void STDMETHODCALLTYPE h_VSSetShader(ID3D11DeviceContext* c, void* sh, void* const* ci, UINT n) { g_bound.vs = sh, ((SetShaderFn)orig(c, 11))(c, sh, ci, n); refresh(c); }
static void STDMETHODCALLTYPE h_GSSetShader(ID3D11DeviceContext* c, void* sh, void* const* ci, UINT n) { g_bound.gs = sh, ((SetShaderFn)orig(c, 23))(c, sh, ci, n); refresh(c); }
static void STDMETHODCALLTYPE h_SetLayout(ID3D11DeviceContext* c, void* l) { g_bound.layout = l, ((SetLayoutFn)orig(c, 17))(c, l); refresh(c); }
static void STDMETHODCALLTYPE h_SetVb(ID3D11DeviceContext* c, UINT s, UINT n, void* const* b, const UINT* st, const UINT* of) {
  for (UINT i = 0; i < n && s + i < 8; ++i) g_bound.vb[s + i] = b ? b[i] : NULL, g_bound.vb_stride[s + i] = st ? st[i] : 0, g_bound.vb_offset[s + i] = of ? of[i] : 0;
  ((SetVbFn)orig(c, 18))(c, s, n, b, st, of); refresh(c);
}
static void STDMETHODCALLTYPE h_SetIb(ID3D11DeviceContext* c, void* b, DXGI_FORMAT f, UINT o) { g_bound.ib = b, g_bound.ib_format = f, g_bound.ib_offset = o, ((SetIbFn)orig(c, 19))(c, b, f, o); refresh(c); }
static void STDMETHODCALLTYPE h_SetTopology(ID3D11DeviceContext* c, D3D11_PRIMITIVE_TOPOLOGY t) { g_bound.topology = t, ((SetTopologyFn)orig(c, 24))(c, t); refresh(c); }
static void STDMETHODCALLTYPE h_SetBlend(ID3D11DeviceContext* c, void* b, const FLOAT f[4], UINT m) {
  g_bound.blend = b;
  if (f) memcpy(g_bound.blend_factor, f, 16);
  ((SetBlendFn)orig(c, 35))(c, b, f, m); refresh(c);
}
static void STDMETHODCALLTYPE h_SetDepth(ID3D11DeviceContext* c, void* d, UINT ref) { g_bound.depth = d, g_bound.stencil_ref = ref, ((SetDepthFn)orig(c, 36))(c, d, ref); refresh(c); }
typedef void(STDMETHODCALLTYPE* SetTargetsFn)(ID3D11DeviceContext*, UINT, void* const*, void*);
typedef void(STDMETHODCALLTYPE* ClearRtvFn)(ID3D11DeviceContext*, void*, const FLOAT[4]);
typedef void(STDMETHODCALLTYPE* ClearDsvFn)(ID3D11DeviceContext*, void*, UINT, FLOAT, UINT8);
static void STDMETHODCALLTYPE h_SetTargets(ID3D11DeviceContext* c, UINT n, void* const* rtv, void* dsv) {
  uint32_t v[10] = {n};
  for (UINT i = 0; i < n && i < 8; ++i) v[1 + i] = rtv ? (uint32_t)(uintptr_t)rtv[i] : 0;
  v[9] = (uint32_t)(uintptr_t)dsv;
  rec(g_frame, kRecTargets, v, sizeof v, NULL, 0);
  ((SetTargetsFn)orig(c, 33))(c, n, rtv, dsv); refresh(c);
}
static void STDMETHODCALLTYPE h_ClearRtv(ID3D11DeviceContext* c, void* view, const FLOAT col[4]) {
  struct { uint32_t view, kind; float col[4]; } v = {(uint32_t)(uintptr_t)view, 0, {0}};
  if (col) memcpy(v.col, col, 16);
  rec(g_frame, kRecClear, &v, sizeof v, NULL, 0);
  ((ClearRtvFn)orig(c, 50))(c, view, col); refresh(c);
}
static void STDMETHODCALLTYPE h_ClearDsv(ID3D11DeviceContext* c, void* view, UINT flags, FLOAT depth, UINT8 stencil) {
  struct { uint32_t view, kind; float depth; uint32_t flags, stencil, pad; } v = {(uint32_t)(uintptr_t)view, 1, depth, flags, stencil, 0};
  rec(g_frame, kRecClear, &v, sizeof v, NULL, 0);
  ((ClearDsvFn)orig(c, 53))(c, view, flags, depth, stencil); refresh(c);
}
static void STDMETHODCALLTYPE h_SetRaster(ID3D11DeviceContext* c, void* r) { g_bound.raster = r, ((SetRasterFn)orig(c, 43))(c, r); refresh(c); }
static void STDMETHODCALLTYPE h_SetViewports(ID3D11DeviceContext* c, UINT n, const D3D11_VIEWPORT* v) {
  if (n && v) g_bound.viewport = v[0];
  ((SetViewportsFn)orig(c, 44))(c, n, v); refresh(c);
}
// A constant buffer bound to a draw but not written during the captured frame (a still effect's constants were set
// once, frames ago): its bytes are read back from the GPU through a staging copy and recorded like a write.
static ID3D11Device* g_device;
static void read_back(ID3D11DeviceContext* c, void* buf) {
  if (!buf || !g_device || seen(buf)) return;
  mark(buf);
  D3D11_BUFFER_DESC bd;
  ID3D11Buffer_GetDesc((ID3D11Buffer*)buf, &bd);
  if (bd.ByteWidth > 65536) return;
  D3D11_BUFFER_DESC sd = bd;
  sd.Usage = D3D11_USAGE_STAGING, sd.BindFlags = 0, sd.CPUAccessFlags = D3D11_CPU_ACCESS_READ, sd.MiscFlags = 0, sd.StructureByteStride = 0;
  ID3D11Buffer* staging = NULL;
  if (FAILED(o_CreateBuffer(g_device, &sd, NULL, &staging)) || !staging) return;
  ID3D11DeviceContext_CopyResource(c, (ID3D11Resource*)staging, (ID3D11Resource*)buf);
  D3D11_MAPPED_SUBRESOURCE m;
  if (SUCCEEDED(((MapFn)orig(c, 14))(c, (ID3D11Resource*)staging, 0, D3D11_MAP_READ, 0, &m))) {
    uint32_t head[3] = {(uint32_t)(uintptr_t)buf, 0, bd.ByteWidth};
    rec(g_frame, kRecWrite, head, sizeof head, m.pData, bd.ByteWidth);
    ((UnmapFn)orig(c, 15))(c, (ID3D11Resource*)staging, 0);
  }
  ID3D11Buffer_Release(staging);
  refresh(c);
}
static void read_back_bound(ID3D11DeviceContext* c) {
  if (!g_frame) return;
  for (int i = 0; i < 14; ++i) read_back(c, g_bound.vs_cb[i]), read_back(c, g_bound.ps_cb[i]);
}
static void STDMETHODCALLTYPE h_DrawIndexed(ID3D11DeviceContext* c, UINT n, UINT s, INT b) { ++g_calls[12]; read_back_bound(c), write_draw(0, n, 1, s, b, 0), ((DrawIndexedFn)orig(c, 12))(c, n, s, b); }
static void STDMETHODCALLTYPE h_Draw(ID3D11DeviceContext* c, UINT n, UINT s) { ++g_calls[13]; read_back_bound(c), write_draw(1, n, 1, s, 0, 0), ((DrawFn)orig(c, 13))(c, n, s); }
static void STDMETHODCALLTYPE h_DrawIndexedInstanced(ID3D11DeviceContext* c, UINT n, UINT in, UINT s, INT b, UINT si) { ++g_calls[20];
  read_back_bound(c), write_draw(2, n, in, s, b, si), ((DrawIndexedInstancedFn)orig(c, 20))(c, n, in, s, b, si);
}
static void STDMETHODCALLTYPE h_DrawInstanced(ID3D11DeviceContext* c, UINT n, UINT in, UINT s, UINT si) { ++g_calls[21]; read_back_bound(c), write_draw(3, n, in, s, 0, si), ((DrawInstancedFn)orig(c, 21))(c, n, in, s, si); }

// Map / Unmap: the bytes written into a buffer while it was mapped (constant buffers, dynamic vertex / index buffers)
static struct { ID3D11Resource* res; UINT sub; void* data; } g_maps[16];
static HRESULT STDMETHODCALLTYPE h_Map(ID3D11DeviceContext* c, ID3D11Resource* r, UINT sub, D3D11_MAP type, UINT flags, D3D11_MAPPED_SUBRESOURCE* m) { ++g_calls[14];
  HRESULT hr = ((MapFn)orig(c, 14))(c, r, sub, type, flags, m);
  refresh(c); refresh(c);
  if (SUCCEEDED(hr) && g_frame && m && type != D3D11_MAP_READ)
    for (int i = 0; i < 16; ++i)
      if (!g_maps[i].res) {
        g_maps[i].res = r, g_maps[i].sub = sub, g_maps[i].data = m->pData;
        break;
      }
  return hr;
}
static void STDMETHODCALLTYPE h_Unmap(ID3D11DeviceContext* c, ID3D11Resource* r, UINT sub) { ++g_calls[15];
  for (int i = 0; i < 16; ++i)
    if (g_maps[i].res == r && g_maps[i].sub == sub) {
      D3D11_RESOURCE_DIMENSION dim;
      ID3D11Resource_GetType(r, &dim);
      if (dim == D3D11_RESOURCE_DIMENSION_BUFFER && g_frame) {
        D3D11_BUFFER_DESC bd;
        ID3D11Buffer_GetDesc((ID3D11Buffer*)r, &bd);
        uint32_t head[3] = {(uint32_t)(uintptr_t)r, 0, bd.ByteWidth};
        rec(g_frame, kRecWrite, head, sizeof head, g_maps[i].data, bd.ByteWidth);
        mark(r);
      }
      g_maps[i].res = NULL;
      break;
    }
  ((UnmapFn)orig(c, 15))(c, r, sub); refresh(c);
}
static void STDMETHODCALLTYPE h_UpdateSubresource(ID3D11DeviceContext* c, ID3D11Resource* r, UINT sub, const D3D11_BOX* box, const void* data, UINT rp, UINT dp) { ++g_calls[48];
  if (g_frame && data) {
    D3D11_RESOURCE_DIMENSION dim;
    ID3D11Resource_GetType(r, &dim);
    if (dim == D3D11_RESOURCE_DIMENSION_BUFFER) {
      D3D11_BUFFER_DESC bd;
      ID3D11Buffer_GetDesc((ID3D11Buffer*)r, &bd);
      const uint32_t off = box ? box->left : 0, size = box ? box->right - box->left : bd.ByteWidth;
      uint32_t head[3] = {(uint32_t)(uintptr_t)r, off, size};
      rec(g_frame, kRecWrite, head, sizeof head, data, size);
      if (!box) mark(r);
    }
  }
  ((UpdateSubresourceFn)orig(c, 48))(c, r, sub, box, data, rp, dp); refresh(c);
}


// the picture the game shows: the back buffer copied to a staging texture, written as a 32-bit BMP next to the frame
static ID3D11Device* g_device;
static void save_backbuffer(IDXGISwapChain* sc, int frame_no) {
  ID3D11Texture2D* back = NULL;
  if (FAILED(IDXGISwapChain_GetBuffer(sc, 0, &IID_ID3D11Texture2D, (void**)&back)) || !back || !g_device) return;
  D3D11_TEXTURE2D_DESC d;
  ID3D11Texture2D_GetDesc(back, &d);
  d.Usage = D3D11_USAGE_STAGING, d.BindFlags = 0, d.CPUAccessFlags = D3D11_CPU_ACCESS_READ, d.MiscFlags = 0, d.SampleDesc.Count = 1;
  d.SampleDesc.Quality = 0, d.MipLevels = 1, d.ArraySize = 1;
  ID3D11Texture2D* staging = NULL;
  if (SUCCEEDED(((CreateTexture2DFn)o_CreateTexture2D)(g_device, &d, NULL, &staging)) && staging) {
    ID3D11DeviceContext* ctx = NULL;
    ID3D11Device_GetImmediateContext(g_device, &ctx);
    ID3D11DeviceContext_CopyResource(ctx, (ID3D11Resource*)staging, (ID3D11Resource*)back);
    D3D11_MAPPED_SUBRESOURCE m;
    if (SUCCEEDED(((MapFn)orig(ctx, 14))(ctx, (ID3D11Resource*)staging, 0, D3D11_MAP_READ, 0, &m))) {
      char path[MAX_PATH];
      snprintf(path, sizeof path, "%s/frame_%05d.bmp", g_dir, frame_no);
      FILE* f = fopen(path, "wb");
      if (f) {
        const uint32_t row = d.Width * 4, size = row * d.Height;
        uint8_t fh[14] = {'B', 'M'};
        uint32_t total = 54 + size, off = 54;
        memcpy(fh + 2, &total, 4), memcpy(fh + 10, &off, 4);
        int32_t ih[10] = {40, (int32_t)d.Width, -(int32_t)d.Height, 0, 0, (int32_t)size, 2835, 2835, 0, 0};
        uint16_t planes_bits[2] = {1, 32};
        fwrite(fh, 1, 14, f);
        fwrite(&ih[0], 4, 3, f), fwrite(planes_bits, 2, 2, f), fwrite(&ih[3], 4, 6, f);
        for (uint32_t y = 0; y < d.Height; ++y) fwrite((uint8_t*)m.pData + y * m.RowPitch, 1, row, f);
        fclose(f);
      }
      ((UnmapFn)orig(ctx, 15))(ctx, (ID3D11Resource*)staging, 0);
    }
    ID3D11DeviceContext_Release(ctx);
    ID3D11Texture2D_Release(staging);
  }
  ID3D11Texture2D_Release(back);
}
// --- the game's own code as it runs: the executable on disk is packed, in memory it is unpacked. On request (a file
// sponge_dump.txt next to the game) the main module's image is written page by page to sponge/exe_image.bin, with the
// address it is loaded at in the log. Pages that cannot be read are left as zeros. The dump changes nothing in the
// process.
static void dump_image(void) {
  const uint8_t* base = (const uint8_t*)GetModuleHandleA(NULL);
  if (!base) return;
  const IMAGE_DOS_HEADER* dos = (const IMAGE_DOS_HEADER*)base;
  const IMAGE_NT_HEADERS* nt = (const IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
  const size_t size = nt->OptionalHeader.SizeOfImage;
  char path[MAX_PATH];
  snprintf(path, sizeof path, "%s/exe_image.bin", g_dir);
  FILE* f = fopen(path, "wb");
  if (!f) return;
  static uint8_t zeros[4096];
  size_t readable = 0;
  for (size_t at = 0; at < size; at += 4096) {
    MEMORY_BASIC_INFORMATION mi;
    const size_t n = size - at < 4096 ? size - at : 4096;
    const int ok = VirtualQuery(base + at, &mi, sizeof mi) && mi.State == MEM_COMMIT && !(mi.Protect & (PAGE_NOACCESS | PAGE_GUARD));
    fwrite(ok ? base + at : zeros, 1, n, f);
    if (ok) readable += n;
  }
  fclose(f);
  say("image dumped: base %p, %u bytes (%u readable), entry rva %#lx", (void*)base, (unsigned)size, (unsigned)readable,
      (unsigned long)nt->OptionalHeader.AddressOfEntryPoint);
  // the image's regions as the system sees them (state, protection), next to the dump
  snprintf(path, sizeof path, "%s/exe_pages.txt", g_dir);
  f = fopen(path, "w");
  if (!f) return;
  for (size_t at = 0; at < size;) {
    MEMORY_BASIC_INFORMATION mi;
    if (!VirtualQuery(base + at, &mi, sizeof mi) || !mi.RegionSize) break;
    fprintf(f, "%08x %08x state %#lx protect %#lx type %#lx\n", (unsigned)at, (unsigned)mi.RegionSize, mi.State, mi.Protect, mi.Type);
    at = (size_t)((const uint8_t*)mi.BaseAddress - base) + mi.RegionSize;
  }
  fclose(f);
}

// --- the code pages still locked. The packer (stub.dll) keeps every code page without access until the game first
// needs it, then unlocks it. On request (a file sponge_touch.txt holding "mode first count") the sponge reads one byte
// from each locked page of .text, pages first .. first + count - 1, as the game would on first use, and logs what
// happened to the page. mode 1: the read is done by the sponge's own code; mode 2: by a `mov al, [ecx]; ret` that is
// part of the game's code (rva in kGadgetRva, checked before use). A read the packer does not serve comes back to
// touch_veh, which skips it: the page stays locked and the game goes on.
__asm__(".text\n"
        ".globl _touch_byte\n"
        "_touch_byte:\n"
        "  movl 4(%esp), %ecx\n"
        ".globl _touch_fault\n"
        "_touch_fault:\n"
        "  movzbl (%ecx), %eax\n"
        "  ret\n"
        ".globl _touch_fail\n"
        "_touch_fail:\n"
        "  movl $-1, %eax\n"
        "  ret\n");
int touch_byte(const void* p);
extern const char touch_fault[], touch_fail[];
enum { kGadgetRva = 0x243bdc };
typedef int(__fastcall* GadgetFn)(const void*);
static const uint8_t* volatile g_touch_at;
static const uint8_t* g_gadget;
static volatile int g_touch_skipped;
static DWORD g_touch_thread;

static LONG CALLBACK touch_veh(EXCEPTION_POINTERS* e) {
  if (!g_touch_at || GetCurrentThreadId() != g_touch_thread) return EXCEPTION_CONTINUE_SEARCH;
  if (e->ExceptionRecord->ExceptionCode != EXCEPTION_ACCESS_VIOLATION) return EXCEPTION_CONTINUE_SEARCH;
  if ((const uint8_t*)e->ExceptionRecord->ExceptionInformation[1] != g_touch_at) return EXCEPTION_CONTINUE_SEARCH;
  CONTEXT* c = e->ContextRecord;
  if ((const char*)c->Eip == touch_fault) c->Eip = (DWORD)touch_fail;
  else if (g_gadget && (const uint8_t*)c->Eip == g_gadget) c->Eip = *(DWORD*)c->Esp, c->Esp += 4, c->Eax = (DWORD)-1;
  else return EXCEPTION_CONTINUE_SEARCH;
  g_touch_skipped = 1;
  return EXCEPTION_CONTINUE_EXECUTION;
}

static DWORD protect_of(const uint8_t* p) {
  MEMORY_BASIC_INFORMATION mi;
  if (!VirtualQuery(p, &mi, sizeof mi)) return 0xffffffff;
  return mi.State == MEM_COMMIT ? mi.Protect : mi.State;
}

static void touch_pages(int mode, unsigned first, unsigned count) {
  const uint8_t* base = (const uint8_t*)GetModuleHandleA(NULL);
  if (!base) return;
  const IMAGE_DOS_HEADER* dos = (const IMAGE_DOS_HEADER*)base;
  const IMAGE_NT_HEADERS* nt = (const IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
  const IMAGE_SECTION_HEADER* text = IMAGE_FIRST_SECTION(nt);  // .text is the first section
  const unsigned pages = (text->Misc.VirtualSize + 4095) / 4096;
  const uint8_t* start = base + text->VirtualAddress;
  const uint8_t* kd = (const uint8_t*)GetProcAddress(GetModuleHandleA("ntdll.dll"), "KiUserExceptionDispatcher");
  if (kd) say("touch: KiUserExceptionDispatcher %p: %02x %02x %02x %02x %02x %02x %02x %02x", (void*)kd, kd[0], kd[1], kd[2], kd[3], kd[4], kd[5], kd[6], kd[7]);
  unsigned locked = 0;
  for (unsigned i = 0; i < pages; ++i) locked += (protect_of(start + i * 4096) & (PAGE_NOACCESS | PAGE_GUARD)) != 0;
  say("touch: mode %d, .text %u pages, %u locked before", mode, pages, locked);
  if (mode != 1 && mode != 2) return;
  g_gadget = NULL;
  if (mode == 2) {
    const uint8_t* g = base + kGadgetRva;
    if ((protect_of(g) & (PAGE_NOACCESS | PAGE_GUARD)) || g[0] != 0x8a || g[1] != 0x01 || g[2] != 0xc3) {
      say("touch: no `mov al, [ecx]; ret` at rva %#x, nothing done", kGadgetRva);
      return;
    }
    g_gadget = g;
  }
  g_touch_thread = GetCurrentThreadId();
  void* veh = AddVectoredExceptionHandler(0, touch_veh);  // last in line: the packer's own handling comes first
  unsigned tried = 0, opened = 0, skipped = 0;
  for (unsigned i = first; i < pages && i - first < count; ++i) {
    const uint8_t* p = start + i * 4096;
    const DWORD before = protect_of(p);
    if (!(before & (PAGE_NOACCESS | PAGE_GUARD))) continue;
    g_touch_skipped = 0;
    g_touch_at = p;
    const int v = mode == 2 ? ((GadgetFn)g_gadget)(p) & 0xff : touch_byte(p);
    g_touch_at = NULL;
    const DWORD after = protect_of(p);
    ++tried;
    if (g_touch_skipped) ++skipped;
    else if (!(after & (PAGE_NOACCESS | PAGE_GUARD))) ++opened;
    if (tried <= 16) say("touch: page %u (rva %#x): protect %#lx -> %#lx, %s, byte %#x", i, (unsigned)(p - base), before, after, g_touch_skipped ? "not served" : "served", (unsigned)v);
  }
  RemoveVectoredExceptionHandler(veh);
  locked = 0;
  for (unsigned i = 0; i < pages; ++i) locked += (protect_of(start + i * 4096) & (PAGE_NOACCESS | PAGE_GUARD)) != 0;
  say("touch: tried %u, opened %u, not served %u; %u locked after", tried, opened, skipped, locked);
}

// --- swap chain: frame boundaries and the capture switch

// --- the system functions the game uses. The executable on disk imports only stub.dll: the packer removed the list of
// Windows functions and fills the address slots itself when the game starts. On request (a file sponge_imports.txt)
// every pointer kept in the image's data that lands exactly on a function another loaded module exports is written
// to sponge/imports.txt: the slot's rva, the module, the function's name (or ordinal). Read-only: nothing in the
// process is changed.
#include <psapi.h>
static const char* export_at(const uint8_t* mod, size_t mod_size, const uint8_t* target, char* ordinal_buf) {
  const IMAGE_DOS_HEADER* dos = (const IMAGE_DOS_HEADER*)mod;
  if (dos->e_magic != IMAGE_DOS_SIGNATURE) return NULL;
  const IMAGE_NT_HEADERS* nt = (const IMAGE_NT_HEADERS*)(mod + dos->e_lfanew);
  const IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
  if (!dir.VirtualAddress || dir.VirtualAddress >= mod_size) return NULL;
  const IMAGE_EXPORT_DIRECTORY* ex = (const IMAGE_EXPORT_DIRECTORY*)(mod + dir.VirtualAddress);
  const DWORD* funcs = (const DWORD*)(mod + ex->AddressOfFunctions);
  const DWORD* names = (const DWORD*)(mod + ex->AddressOfNames);
  const WORD* ords = (const WORD*)(mod + ex->AddressOfNameOrdinals);
  const DWORD want = (DWORD)(target - mod);
  for (DWORD i = 0; i < ex->NumberOfNames; ++i)
    if (ords[i] < ex->NumberOfFunctions && funcs[ords[i]] == want) return (const char*)(mod + names[i]);
  for (DWORD i = 0; i < ex->NumberOfFunctions; ++i)
    if (funcs[i] == want) {
      snprintf(ordinal_buf, 24, "#%lu", (unsigned long)(ex->Base + i));
      return ordinal_buf;
    }
  return NULL;
}
static void dump_imports(void) {
  const uint8_t* base = (const uint8_t*)GetModuleHandleA(NULL);
  if (!base) return;
  const IMAGE_NT_HEADERS* nt = (const IMAGE_NT_HEADERS*)(base + ((const IMAGE_DOS_HEADER*)base)->e_lfanew);
  const size_t size = nt->OptionalHeader.SizeOfImage;
  static HMODULE mods[1024];
  DWORD need = 0;
  if (!K32EnumProcessModules(GetCurrentProcess(), mods, sizeof mods, &need)) return;
  const unsigned n_mods = need / sizeof(HMODULE) < 1024 ? need / sizeof(HMODULE) : 1024;
  static MODULEINFO info[1024];
  static char names[1024][64];
  char path[MAX_PATH];
  snprintf(path, sizeof path, "%s/imports.txt", g_dir);
  FILE* f = fopen(path, "w");
  if (!f) return;
  for (unsigned m = 0; m < n_mods; ++m) {
    K32GetModuleInformation(GetCurrentProcess(), mods[m], &info[m], sizeof info[m]);
    names[m][0] = 0;
    K32GetModuleBaseNameA(GetCurrentProcess(), mods[m], names[m], sizeof names[m]);
    fprintf(f, "module %s %p %#lx\n", names[m], info[m].lpBaseOfDll, (unsigned long)info[m].SizeOfImage);
  }
  const IMAGE_SECTION_HEADER* sec = IMAGE_FIRST_SECTION(nt);
  unsigned found = 0, loose = 0, outside = 0;
  for (unsigned s = 0; s < nt->FileHeader.NumberOfSections; ++s) {
    if (sec[s].Characteristics & IMAGE_SCN_CNT_CODE) continue;  // .text: the slots are in the data
    const size_t from = sec[s].VirtualAddress, to = from + sec[s].Misc.VirtualSize;
    for (size_t at = from; at + 4 <= to && at + 4 <= size;) {
      MEMORY_BASIC_INFORMATION mi;
      if (!VirtualQuery(base + at, &mi, sizeof mi) || mi.State != MEM_COMMIT || (mi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) {
        at = (at + 4096) & ~(size_t)4095;
        continue;
      }
      const size_t page_end = (at + 4096) & ~(size_t)4095;
      for (; at + 4 <= page_end && at + 4 <= to; at += 4) {
        const uint8_t* v = *(const uint8_t* const*)(base + at);
        if (v >= base && v < base + size) continue;
        if ((size_t)v < 0x10000) continue;
        int hit = 0;
        for (unsigned m = 1; m < n_mods && !hit; ++m) {
          const uint8_t* mb = (const uint8_t*)info[m].lpBaseOfDll;
          if (v < mb || v >= mb + info[m].SizeOfImage) continue;
          hit = 1;
          char ob[24];
          const char* name = export_at(mb, info[m].SizeOfImage, v, ob);
          if (name) fprintf(f, "slot %08x %s %s\n", (unsigned)at, names[m], name), ++found;
          else ++loose;
        }
        // the first pages of .rdata hold the import slots: one that points at no module at all is logged too (a
        // packer may put a stub of its own between the game and the system)
        if (!hit && s == 1 && at < from + 0x2000) {
          MEMORY_BASIC_INFORMATION ti;
          if (VirtualQuery(v, &ti, sizeof ti) && ti.State == MEM_COMMIT && (ti.Protect & (PAGE_EXECUTE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE))) {
            fprintf(f, "stub %08x -> %p protect %#lx:", (unsigned)at, (void*)v, ti.Protect);
            for (int k = 0; k < 16; ++k) fprintf(f, " %02x", v[k]);
            fprintf(f, "\n");
            ++outside;
          }
        }
      }
    }
  }
  fclose(f);
  say("imports: %u slots named, %u pointers into modules that are no export, %u slots to code outside every module; %u modules", found, loose, outside, n_mods);
}

typedef HRESULT(STDMETHODCALLTYPE* PresentFn)(IDXGISwapChain*, UINT, UINT);
static PresentFn o_Present;
static HRESULT STDMETHODCALLTYPE h_Present(IDXGISwapChain* s, UINT interval, UINT flags) {
  if (g_frame) save_backbuffer(s, g_frame_no);
  HRESULT r = o_Present(s, interval, flags);
  ++g_presents;
  if (g_frame) {
    fclose(g_frame), g_frame = NULL;
    if (--g_capture_left > 0) {
      char path[MAX_PATH];
      snprintf(path, sizeof path, "%s\\frame_%05d.bin", g_dir, ++g_frame_no);
      g_frame = fopen(path, "wb");
      g_seen_n = 0;
      uint32_t head[2] = {(uint32_t)g_frame_no, g_presents};
      rec(g_frame, kRecFrame, head, sizeof head, NULL, 0);
    }
  } else if ((g_presents & 7) == 0) {
    if (GetFileAttributesA("sponge_dump.txt") != INVALID_FILE_ATTRIBUTES) {
      DeleteFileA("sponge_dump.txt");
      dump_image();
    }
    if (GetFileAttributesA("sponge_imports.txt") != INVALID_FILE_ATTRIBUTES) {
      DeleteFileA("sponge_imports.txt");
      dump_imports();
    }
    FILE* touch = fopen("sponge_touch.txt", "r");
    if (touch) {
      int mode = 0;
      unsigned first = 0, count = 0;
      const int got = fscanf(touch, "%d %u %u", &mode, &first, &count);
      fclose(touch);
      DeleteFileA("sponge_touch.txt");
      touch_pages(got >= 1 ? mode : 0, first, got >= 3 ? count : 0);
    }
    FILE* req = fopen("sponge_capture.txt", "r");
    if (req) {
      int n = 1;
      if (fscanf(req, "%d", &n) != 1) n = 1;
      fclose(req);
      DeleteFileA("sponge_capture.txt");
      g_capture_left = n;
      char path[MAX_PATH];
      snprintf(path, sizeof path, "%s\\frame_%05d.bin", g_dir, ++g_frame_no);
      g_frame = fopen(path, "wb");
      g_seen_n = 0;
      uint32_t head[2] = {(uint32_t)g_frame_no, g_presents};
      rec(g_frame, kRecFrame, head, sizeof head, NULL, 0);
      say("capturing %d frames from present %u", n, g_presents);
    }
  }
  if (g_objects && (g_presents & 63) == 0) fflush(g_objects);
  if (g_presents == 300 || g_presents == 3000)
    say("present %u: calls draw-indexed %u draw %u dii %u di %u map %u unmap %u update %u ps-shader %u vs-cb %u, draw entries rewritten %u", g_presents,
        g_calls[12], g_calls[13], g_calls[20], g_calls[21], g_calls[14], g_calls[15], g_calls[48], g_calls[9], g_calls[7], g_rewrites);
  return r;
}

static void hook_context(void** cv);
static QueryFn o_CtxQuery;
static HRESULT STDMETHODCALLTYPE h_CtxQuery(void* self, REFIID riid, void** out) {
  HRESULT r = ((QueryFn)orig(self, 0))(self, riid, out);
  if (SUCCEEDED(r) && out && *out) {
    void** vt = *(void***)*out;
    static void* seen[8];
    int known = 0;
    for (int i = 0; i < 8; ++i)
      if (seen[i] == vt) known = 1;
    if (!known) {
      for (int i = 0; i < 8; ++i)
        if (!seen[i]) {
          seen[i] = vt;
          break;
        }
      say("context QueryInterface %08lx-%04x -> %p vtable %p: hooking it too", riid->Data1, riid->Data2, *out, (void*)vt);
      hook_context(vt);
    }
  }
  return r;
}

static void hook_all(ID3D11Device* dev, ID3D11DeviceContext* ctx, IDXGISwapChain* sc) {
  g_device = dev;
  void** dv = *(void***)dev;
  void* p;
#define HOOK(VT, I, NAME) \
  if ((p = patch(VT, I, (void*)h_##NAME)) != NULL) o_##NAME = p
  HOOK(dv, 3, CreateBuffer);
  HOOK(dv, 5, CreateTexture2D);
  HOOK(dv, 7, CreateSrv);
  HOOK(dv, 9, CreateRtv);
  HOOK(dv, 10, CreateDsv);
  HOOK(dv, 11, CreateLayout);
  HOOK(dv, 12, CreateVS);
  HOOK(dv, 13, CreateGS);
  HOOK(dv, 15, CreatePS);
  HOOK(dv, 20, CreateBlend);
  HOOK(dv, 21, CreateDepth);
  HOOK(dv, 22, CreateRaster);
  HOOK(dv, 23, CreateSampler);
  void** cv = *(void***)ctx;
  hook_context(cv);
  if (sc) {
    void** sv = *(void***)sc;
    HOOK(sv, 8, Present);
  }
#undef HOOK
  say("hooked device %p context %p swapchain %p; context vtable %p draw-indexed %p -> %p", (void*)dev, (void*)ctx, (void*)sc, (void*)cv,
      (void*)o_DrawIndexed, cv[12]);
}

static void hook_context(void** cv) {
  void* p;
  remember(cv);
#define HOOK(VT, I, NAME)   if ((p = patch(VT, I, (void*)h_##NAME)) != NULL && !o_##NAME) o_##NAME = p
  HOOK(cv, 0, CtxQuery);
  HOOK(cv, 7, VSSetCB);
  HOOK(cv, 8, PSSetSRV);
  HOOK(cv, 9, PSSetShader);
  HOOK(cv, 10, PSSetSamp);
  HOOK(cv, 11, VSSetShader);
  HOOK(cv, 12, DrawIndexed);
  HOOK(cv, 13, Draw);
  HOOK(cv, 14, Map);
  HOOK(cv, 15, Unmap);
  HOOK(cv, 16, PSSetCB);
  HOOK(cv, 17, SetLayout);
  HOOK(cv, 18, SetVb);
  HOOK(cv, 19, SetIb);
  HOOK(cv, 20, DrawIndexedInstanced);
  HOOK(cv, 21, DrawInstanced);
  HOOK(cv, 23, GSSetShader);
  HOOK(cv, 24, SetTopology);
  HOOK(cv, 25, VSSetSRV);
  HOOK(cv, 33, SetTargets);
  HOOK(cv, 35, SetBlend);
  HOOK(cv, 50, ClearRtv);
  HOOK(cv, 53, ClearDsv);
  HOOK(cv, 36, SetDepth);
  HOOK(cv, 43, SetRaster);
  HOOK(cv, 44, SetViewports);
  HOOK(cv, 48, UpdateSubresource);
#undef HOOK
}

static void init(void) {
  if (g_real) return;
  GetCurrentDirectoryA(sizeof g_dir, g_dir);
  strcat(g_dir, "\\sponge");
  CreateDirectoryA(g_dir, NULL);
  char shaders[MAX_PATH];
  snprintf(shaders, sizeof shaders, "%s\\shaders", g_dir);
  CreateDirectoryA(shaders, NULL);
  char path[MAX_PATH];
  snprintf(path, sizeof path, "%s\\objects.bin", g_dir);
  g_objects = fopen(path, "wb");
  char sys[MAX_PATH];
  GetSystemDirectoryA(sys, sizeof sys);  // SysWOW64 for this 32-bit process
  strcat(sys, "\\d3d11.dll");
  g_real = LoadLibraryA(sys);
  g_create = (CreateDeviceFn)GetProcAddress(g_real, "D3D11CreateDevice");
  g_create_sc = (CreateDeviceAndSwapChainFn)GetProcAddress(g_real, "D3D11CreateDeviceAndSwapChain");
  say("real %s -> %p, sponge in %s", sys, (void*)g_real, g_dir);
}

HRESULT WINAPI D3D11CreateDevice(IDXGIAdapter* adapter, D3D_DRIVER_TYPE driver, HMODULE software, UINT flags, const D3D_FEATURE_LEVEL* levels, UINT nlevels,
                                 UINT sdk, ID3D11Device** device, D3D_FEATURE_LEVEL* level, ID3D11DeviceContext** context) {
  init();
  HRESULT r = g_create(adapter, driver, software, flags, levels, nlevels, sdk, device, level, context);
  say("D3D11CreateDevice(driver %d, flags %#x) = %#lx", driver, flags, (unsigned long)r);
  if (SUCCEEDED(r) && device && *device && context && *context) hook_all(*device, *context, NULL);
  return r;
}

HRESULT WINAPI D3D11CreateDeviceAndSwapChain(IDXGIAdapter* adapter, D3D_DRIVER_TYPE driver, HMODULE software, UINT flags, const D3D_FEATURE_LEVEL* levels,
                                             UINT nlevels, UINT sdk, const DXGI_SWAP_CHAIN_DESC* desc, IDXGISwapChain** swapchain, ID3D11Device** device,
                                             D3D_FEATURE_LEVEL* level, ID3D11DeviceContext** context) {
  init();
  HRESULT r = g_create_sc(adapter, driver, software, flags, levels, nlevels, sdk, desc, swapchain, device, level, context);
  say("D3D11CreateDeviceAndSwapChain(driver %d, flags %#x) = %#lx", driver, flags, (unsigned long)r);
  say("  device %p context %p swapchain %p", device ? (void*)*device : NULL, context ? (void*)*context : NULL, swapchain ? (void*)*swapchain : NULL);
  if (SUCCEEDED(r) && device && *device) {
    // the game may not ask for the context here (it takes it later): take it ourselves to patch its methods
    ID3D11DeviceContext* ctx = NULL;
    ID3D11Device_GetImmediateContext(*device, &ctx);
    if (ctx) hook_all(*device, ctx, swapchain ? *swapchain : NULL), ID3D11DeviceContext_Release(ctx);
  }
  return r;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved) {
  (void)inst, (void)reserved;
  if (reason == DLL_PROCESS_ATTACH) say("sponge loaded into pid %lu", GetCurrentProcessId());
  if (reason == DLL_PROCESS_DETACH && g_objects) fclose(g_objects);
  return TRUE;
}
