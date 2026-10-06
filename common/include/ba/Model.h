#pragma once
// League's animated characters: .skn (the skinned mesh), .skl (the skeleton) and .anm (animations), kept in League's own
// space and units.

#include <array>
#include <cstdint>
#include <span>
#include <string>
#include <unordered_map>
#include <vector>

namespace ba {

using Vec3 = std::array<float, 3>;
using Quat = std::array<float, 4>;  // x, y, z, w

// ---------------------------------------------------------------- .skn
struct SkinVertex {
  Vec3 position{};
  std::array<uint8_t, 4> bones{};  // indices into the skeleton's influence list
  std::array<float, 4> weights{};
  Vec3 normal{};
  std::array<float, 2> uv{};
};

struct SkinRange {
  std::string material;  // the submesh name; the skin's .bin maps it to a texture
  uint32_t vertex_start = 0, vertex_count = 0, index_start = 0, index_count = 0;
};

struct SkinMesh {
  std::vector<SkinRange> ranges;
  std::vector<uint16_t> indices;
  std::vector<SkinVertex> vertices;
};

SkinMesh read_skn(std::span<const uint8_t> data);

// ---------------------------------------------------------------- .skl
struct Joint {
  std::string name;
  uint32_t hash = 0;  // ELF hash of the name, what .anm tracks point at
  int16_t parent = -1;
  Vec3 translate{};
  Quat rotate{0, 0, 0, 1};
  Vec3 scale{1, 1, 1};
  Vec3 ibind_translate{};
  Quat ibind_rotate{0, 0, 0, 1};
  Vec3 ibind_scale{1, 1, 1};
};

struct Skeleton {
  std::vector<Joint> joints;
  /** Skin bone index -> joint index (.skn bone indices go through this list). */
  std::vector<uint16_t> influences;
  int joint_by_hash(uint32_t hash) const;
};

Skeleton read_skl(std::span<const uint8_t> data);

// ---------------------------------------------------------------- .anm
template <typename T>
struct Key {
  float frame = 0;
  T value{};
};

struct Track {
  uint32_t joint_hash = 0;
  std::vector<Key<Vec3>> translate;
  std::vector<Key<Quat>> rotate;
  std::vector<Key<Vec3>> scale;
};

struct Animation {
  float fps = 30;
  float frames = 0;  // length in frames
  /** Compressed files (r3d2canm) keep only the keys their error metric needs; the game evaluates them with
   *  Catmull-Rom curves. Uncompressed ones are sampled every frame and interpolated linearly. */
  bool compressed = false;
  std::vector<Track> tracks;

  float seconds() const { return frames / fps; }
};

Animation read_anm(std::span<const uint8_t> data);

// ---------------------------------------------------------------- .scb
/** A static mesh ("r3d2Mesh": waterfalls, river shores, god rays, base-door domes in effects), one vertex per face corner
 *  (its uvs are per face), in League units and axes, League's winding. Colours are white unless the file has them. */
struct StaticMesh {
  std::vector<Vec3> positions;
  std::vector<std::array<float, 2>> uvs;
  std::vector<std::array<uint8_t, 4>> colors;
  bool has_colors = false;
  /** The file has no normals: each corner gets its face's (our choice, for mesh_vs's Fresnel term). */
  std::vector<Vec3> normals;
};

StaticMesh read_scb(std::span<const uint8_t> data);

/** Translate / rotate / scale of a track at `frame` (falls back to `bind` for properties the track does not key). */
void sample(const Animation& a, const Track& t, float frame, Vec3& tr, Quat& rot, Vec3& sc);

}  // namespace ba
