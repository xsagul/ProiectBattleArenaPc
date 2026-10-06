#include "ba/MapGeometry.h"

#include <stdexcept>
#include <string>

#include "ba/ByteReader.h"

namespace ba {

namespace {

uint32_t format_size(GeoFormat f) {
  switch (f) {
    case GeoFormat::F1: return 4;
    case GeoFormat::F2: return 8;
    case GeoFormat::F3: return 12;
    case GeoFormat::F4: return 16;
    case GeoFormat::BGRA8:
    case GeoFormat::ZYXW8:
    case GeoFormat::RGBA8: return 4;
    case GeoFormat::H2: return 4;
    case GeoFormat::H3:
    case GeoFormat::H4: return 8;
  }
  return 0;
}

std::string string32(ByteReader& r) { return r.string(r.read<uint32_t>()); }

}  // namespace

uint32_t GeoVertexLayout::stride() const {
  uint32_t s = 0;
  for (const auto& [e, f] : elements) s += format_size(f);
  return s;
}

int GeoVertexLayout::offset_of(GeoElement e) const {
  int o = 0;
  for (const auto& [el, f] : elements) {
    if (el == e) return o;
    o += static_cast<int>(format_size(f));
  }
  return -1;
}

GeoFormat GeoVertexLayout::format_of(GeoElement e) const {
  for (const auto& [el, f] : elements)
    if (el == e) return f;
  return GeoFormat::F1;
}

MapGeometry read_mapgeo(std::span<const uint8_t> data) {
  ByteReader r(data);
  if (r.string(4) != "OEGM") throw std::runtime_error("mapgeo: bad signature");
  MapGeometry g;
  g.version = r.read<uint32_t>();
  // v13 = patch 12.23. Layout checked by walking all 960 models of 12.23's base_srx (research/mapgeo13_explore.py):
  // two sampler names, layer byte before each buffer, no visibility controller, no render flags, three texture channels
  if (g.version != 13) throw std::runtime_error("mapgeo: unsupported version " + std::to_string(g.version));

  string32(r);  // two fixed sampler names (empty on 12.23's Summoner's Rift)
  string32(r);
  const uint32_t nlayouts = r.read<uint32_t>();
  g.layouts.resize(nlayouts);
  for (GeoVertexLayout& l : g.layouts) {
    r.skip(4);  // usage
    const uint32_t n = r.read<uint32_t>();
    for (uint32_t i = 0; i < 15; ++i) {
      const auto e = static_cast<GeoElement>(r.read<uint32_t>());
      const auto f = static_cast<GeoFormat>(r.read<uint32_t>());
      if (i < n) l.elements.emplace_back(e, f);
    }
  }
  const uint32_t nvb = r.read<uint32_t>();
  for (uint32_t i = 0; i < nvb; ++i) {
    r.skip(1);  // layer
    g.vertex_buffers.push_back(r.bytes(r.read<uint32_t>()));
  }
  const uint32_t nib = r.read<uint32_t>();
  for (uint32_t i = 0; i < nib; ++i) {
    r.skip(1);
    g.index_buffers.push_back(r.bytes(r.read<uint32_t>()));
  }

  const uint32_t nmodels = r.read<uint32_t>();
  g.models.resize(nmodels);
  for (GeoModel& m : g.models) {
    m.vertex_count = r.read<uint32_t>();
    const uint32_t streams = r.read<uint32_t>();
    m.layout = r.read<uint32_t>();
    for (uint32_t i = 0; i < streams; ++i) m.vertex_buffers.push_back(r.read<int32_t>());
    m.index_count = r.read<uint32_t>();
    m.index_buffer = r.read<uint32_t>();
    m.layers = r.read<uint8_t>();  // the elemental-map layers the model shows on (bit per layer)
    const uint32_t nsub = r.read<uint32_t>();
    for (uint32_t i = 0; i < nsub; ++i) {
      GeoSubmesh s;
      r.skip(4);  // hash
      s.material = string32(r);
      s.index_start = r.read<uint32_t>();
      s.index_count = r.read<uint32_t>();
      s.min_vertex = r.read<uint32_t>();
      s.max_vertex = r.read<uint32_t>();
      m.submeshes.push_back(std::move(s));
    }
    m.no_backface_cull = r.read<uint8_t>() != 0;
    for (float& f : m.bbox) f = r.read<float>();
    for (float& f : m.matrix) f = r.read<float>();
    m.quality = r.read<uint8_t>();
    m.is_bush = r.read<uint8_t>() != 0;  // 0 on every 12.23 model: the brush is placed as characters (brush_sru_*)
    m.baked_light = string32(r);
    r.skip(16);
    string32(r);  // stationary light
    r.skip(16);
    string32(r);  // a third texture channel (string + scale / offset), empty on every 12.23 Summoner's Rift model
    r.skip(16);
  }
  return g;
}

}  // namespace ba
