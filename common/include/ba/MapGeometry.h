#pragma once
// League's map geometry (.mapgeo, "OEGM", version 13 for patch 12.23's Summoner's Rift): vertex and index buffers shared by
// many models; each model has its vertex layout, a world matrix, the visibility layers it belongs to (layer 1 = the
// base Rift) and submeshes that name their material (a StaticMaterialDef in <map>.materials.bin). The map's lighting is
// baked into its textures.

#include <array>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace ba {

/** Vertex element usages and formats, as League numbers them. */
enum class GeoElement : uint32_t { Position = 0, BlendWeight = 1, Normal = 2, Fog = 3, Color0 = 4, Color1 = 5, BlendIndex = 6, Uv0 = 7, Uv1 = 8 };
enum class GeoFormat : uint32_t { F1 = 0, F2 = 1, F3 = 2, F4 = 3, BGRA8 = 4, ZYXW8 = 5, RGBA8 = 6, H2 = 7, H3 = 8, H4 = 9 };

struct GeoVertexLayout {
  std::vector<std::pair<GeoElement, GeoFormat>> elements;
  uint32_t stride() const;
  /** Byte offset of an element, or -1. */
  int offset_of(GeoElement e) const;
  GeoFormat format_of(GeoElement e) const;
};

struct GeoSubmesh {
  std::string material;
  uint32_t index_start = 0, index_count = 0, min_vertex = 0, max_vertex = 0;
};

struct GeoModel {
  uint32_t vertex_count = 0;
  uint32_t layout = 0;                 // first layout; one per vertex buffer
  std::vector<int32_t> vertex_buffers; // one per stream
  uint32_t index_count = 0;
  uint32_t index_buffer = 0;
  uint8_t layers = 0;                  // visibility layer bits
  std::vector<GeoSubmesh> submeshes;
  bool no_backface_cull = false;
  std::array<float, 6> bbox{};
  std::array<float, 16> matrix{};      // row-major, row vectors (translation in the last row)
  uint8_t quality = 0;
  bool is_bush = false;
  std::string baked_light;             // empty on today's Rift: the light is in the textures
};

struct MapGeometry {
  uint32_t version = 0;
  std::vector<GeoVertexLayout> layouts;
  std::vector<std::span<const uint8_t>> vertex_buffers;  // views into the file's bytes
  std::vector<std::span<const uint8_t>> index_buffers;   // u16 indices
  std::vector<GeoModel> models;
};

/** Parses a .mapgeo; the buffers point into `data`, which must outlive the result. */
MapGeometry read_mapgeo(std::span<const uint8_t> data);

}  // namespace ba
