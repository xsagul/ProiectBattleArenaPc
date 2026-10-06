#include "ba/Model.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <string>

#include "ba/ByteReader.h"

namespace ba {

namespace {

Vec3 vec3(ByteReader& r) { return {r.read<float>(), r.read<float>(), r.read<float>()}; }
Quat quat(ByteReader& r) { return {r.read<float>(), r.read<float>(), r.read<float>(), r.read<float>()}; }

std::string padded(ByteReader& r, size_t n) {
  std::string s = r.string(n);
  s.resize(std::strlen(s.c_str()));
  return s;
}

std::string cstring_at(std::span<const uint8_t> data, size_t at) {
  std::string s;
  while (at < data.size() && data[at]) s.push_back(static_cast<char>(data[at++]));
  return s;
}

/** League's 48-bit quaternion: the largest component is dropped, the other three stored in 15 bits each. */
Quat decompress_quat(std::span<const uint8_t> b) {
  const uint64_t bits = static_cast<uint64_t>(b[0] | b[1] << 8) | static_cast<uint64_t>(b[2] | b[3] << 8) << 16 |
                        static_cast<uint64_t>(b[4] | b[5] << 8) << 32;
  const uint32_t max_index = static_cast<uint32_t>((bits >> 45) & 3);
  constexpr float kInvSqrt2 = 0.70710678118f;
  constexpr float kScale = 0.00004315969f;  // sqrt(2) / 32767
  const float a = static_cast<float>((bits >> 30) & 32767) * kScale - kInvSqrt2;
  const float c1 = static_cast<float>((bits >> 15) & 32767) * kScale - kInvSqrt2;
  const float c2 = static_cast<float>(bits & 32767) * kScale - kInvSqrt2;
  const float d = std::sqrt(std::max(0.f, 1.f - (a * a + c1 * c1 + c2 * c2)));
  switch (max_index) {
    case 0: return {d, a, c1, c2};
    case 1: return {a, d, c1, c2};
    case 2: return {a, c1, d, c2};
    default: return {a, c1, c2, d};
  }
}

Vec3 decompress_vec3(const Vec3& lo, const Vec3& hi, std::span<const uint8_t> b) {
  Vec3 v;
  for (int i = 0; i < 3; ++i) {
    const auto q = static_cast<float>(b[static_cast<size_t>(i * 2)] | b[static_cast<size_t>(i * 2 + 1)] << 8);
    v[static_cast<size_t>(i)] = (hi[static_cast<size_t>(i)] - lo[static_cast<size_t>(i)]) / 65535.f * q + lo[static_cast<size_t>(i)];
  }
  return v;
}

/** The ELF hash of a joint name, lower-cased: what skeletons and animations name joints by. */
uint32_t elf_hash(const std::string& name) {
  uint32_t h = 0;
  for (char ch : name) {
    h = (h << 4) + static_cast<uint8_t>(ch >= 'A' && ch <= 'Z' ? ch - 'A' + 'a' : ch);
    const uint32_t high = h & 0xF0000000u;
    if (high) h ^= high >> 24;
    h &= ~high;
  }
  return h;
}

template <typename T>
void sort_keys(std::vector<Key<T>>& keys) {
  std::stable_sort(keys.begin(), keys.end(), [](const Key<T>& a, const Key<T>& b) { return a.frame < b.frame; });
}

}  // namespace

// ---------------------------------------------------------------- .skn
SkinMesh read_skn(std::span<const uint8_t> data) {
  ByteReader r(data);
  if (r.read<uint32_t>() != 0x00112233) throw std::runtime_error("skn: bad signature");
  const uint16_t major = r.read<uint16_t>();
  r.read<uint16_t>();  // minor
  SkinMesh m;
  uint32_t index_count = 0, vertex_count = 0, vertex_type = 0;
  if (major == 0) {
    index_count = r.read<uint32_t>();
    vertex_count = r.read<uint32_t>();
    m.ranges.push_back({"Base", 0, vertex_count, 0, index_count});
  } else {
    const uint32_t n = r.read<uint32_t>();
    for (uint32_t i = 0; i < n; ++i) {
      SkinRange s;
      s.material = padded(r, 64);
      s.vertex_start = r.read<uint32_t>();
      s.vertex_count = r.read<uint32_t>();
      s.index_start = r.read<uint32_t>();
      s.index_count = r.read<uint32_t>();
      m.ranges.push_back(s);
    }
    if (major == 4) r.skip(4);  // flags
    index_count = r.read<uint32_t>();
    vertex_count = r.read<uint32_t>();
    if (major == 4) {
      r.skip(4);  // vertex size
      vertex_type = r.read<uint32_t>();
      r.skip(24 + 16);  // bounding box, bounding sphere
    }
  }
  m.indices.resize(index_count);
  for (uint16_t& i : m.indices) i = r.read<uint16_t>();
  m.vertices.resize(vertex_count);
  for (SkinVertex& v : m.vertices) {
    v.position = vec3(r);
    for (uint8_t& b : v.bones) b = r.read<uint8_t>();
    for (float& w : v.weights) w = r.read<float>();
    v.normal = vec3(r);
    v.uv = {r.read<float>(), r.read<float>()};
    if (vertex_type >= 1) r.skip(4);       // color
    if (vertex_type == 2) r.skip(16);      // tangent
  }
  return m;
}

// ---------------------------------------------------------------- .skl
int Skeleton::joint_by_hash(uint32_t hash) const {
  for (size_t i = 0; i < joints.size(); ++i)
    if (joints[i].hash == hash) return static_cast<int>(i);
  return -1;
}

Skeleton read_skl(std::span<const uint8_t> data) {
  ByteReader r(data);
  r.skip(4);
  if (r.read<uint32_t>() != 0x22FD4FC3) throw std::runtime_error("skl: legacy (r3d2sklt) skeletons are not supported yet");
  r.skip(4);  // version 0
  r.skip(2);  // flags
  const uint16_t joint_count = r.read<uint16_t>();
  const uint32_t influence_count = r.read<uint32_t>();
  const int32_t joints_offset = r.read<int32_t>();
  r.skip(4);
  const int32_t influences_offset = r.read<int32_t>();
  Skeleton s;
  if (joints_offset > 0) {
    r.seek(static_cast<size_t>(joints_offset));
    s.joints.resize(joint_count);
    for (Joint& j : s.joints) {
      r.skip(2);  // flags
      r.skip(2);  // id
      j.parent = r.read<int16_t>();
      r.skip(2);
      j.hash = r.read<uint32_t>();
      r.skip(4);  // radius
      j.translate = vec3(r);
      j.scale = vec3(r);
      j.rotate = quat(r);
      j.ibind_translate = vec3(r);
      j.ibind_scale = vec3(r);
      j.ibind_rotate = quat(r);
      const int32_t name_rel = r.read<int32_t>();
      j.name = cstring_at(data, r.pos() - 4 + static_cast<size_t>(name_rel));
    }
  }
  if (influences_offset > 0) {
    r.seek(static_cast<size_t>(influences_offset));
    s.influences.resize(influence_count);
    for (uint16_t& i : s.influences) i = r.read<uint16_t>();
  }
  return s;
}

// ---------------------------------------------------------------- .anm
Animation read_anm(std::span<const uint8_t> data) {
  ByteReader r(data);
  const std::string sig = r.string(8);
  const uint32_t version = r.read<uint32_t>();
  Animation a;
  // Every track of the file stays its own, in the file's order. Two tracks may carry the same joint hash: a skeleton
  // can hold two joints whose names differ only in case ("root" and "Root" of SRUAP_MageCrystal: the hash ignores
  // case), each with its own track. Sharing one mixed their keys and sank the fountain's crystal 1750 units.
  auto new_track = [&a](uint32_t hash) -> Track& {
    a.tracks.push_back(Track{hash, {}, {}, {}});
    return a.tracks.back();
  };
  // a file's track number -> its track here
  auto track_slots = [&](const std::vector<uint32_t>& hashes) {
    std::vector<size_t> slots;
    for (uint32_t h : hashes) {
      new_track(h);
      slots.push_back(a.tracks.size() - 1);
    }
    return slots;
  };

  if (sig == "r3d2canm") {
    a.compressed = true;
    r.skip(12);  // file size, format token, flags
    const uint32_t track_count = r.read<uint32_t>();
    const uint32_t frame_count = r.read<uint32_t>();
    r.skip(4);  // jump cache count
    const float max_time = r.read<float>();
    a.fps = r.read<float>();
    a.frames = max_time * a.fps;
    r.skip(24);  // error metrics
    const Vec3 tmin = vec3(r), tmax = vec3(r), smin = vec3(r), smax = vec3(r);
    const int32_t frames_offset = r.read<int32_t>();
    r.skip(4);
    const int32_t hashes_offset = r.read<int32_t>();
    r.seek(static_cast<size_t>(hashes_offset) + 12);
    std::vector<uint32_t> hashes(track_count);
    for (uint32_t& h : hashes) h = r.read<uint32_t>();
    const std::vector<size_t> slots = track_slots(hashes);
    r.seek(static_cast<size_t>(frames_offset) + 12);
    for (uint32_t i = 0; i < frame_count; ++i) {
      const uint16_t time = r.read<uint16_t>();
      const uint16_t bits = r.read<uint16_t>();
      const auto payload = r.bytes(6);
      const uint32_t joint = bits & 0x3FFF;
      if (joint >= slots.size()) continue;
      Track& t = a.tracks[slots[joint]];
      const float frame = static_cast<float>(time) / 65535.f * max_time * a.fps;
      switch (bits >> 14) {
        case 0: t.rotate.push_back({frame, decompress_quat(payload)}); break;
        case 1: t.translate.push_back({frame, decompress_vec3(tmin, tmax, payload)}); break;
        case 2: t.scale.push_back({frame, decompress_vec3(smin, smax, payload)}); break;
        default: break;
      }
    }
  } else if (sig == "r3d2anmd" && version <= 3) {
    // the legacy layout (Lux's idle, older clips): u32 skeleton id, u32 tracks, u32 frames, u32 fps; per track a
    // 32-byte joint name and u32 flags, then per frame a quaternion (x, y, z, w) and a translation; no scale
    r.skip(4);
    const uint32_t track_count = r.read<uint32_t>();
    const uint32_t frame_count = r.read<uint32_t>();
    a.fps = static_cast<float>(r.read<uint32_t>());
    if (a.fps <= 0) a.fps = 30;
    a.frames = static_cast<float>(frame_count > 0 ? frame_count - 1 : 0);
    for (uint32_t t = 0; t < track_count; ++t) {
      Track& tr = new_track(elf_hash(padded(r, 32)));
      r.skip(4);  // flags
      for (uint32_t f = 0; f < frame_count; ++f) {
        const Quat q = quat(r);
        const Vec3 v = vec3(r);
        tr.rotate.push_back({static_cast<float>(f), q});
        tr.translate.push_back({static_cast<float>(f), v});
      }
    }
  } else if (sig == "r3d2anmd" && (version == 4 || version == 5)) {
    r.skip(version == 5 ? 16 : 16);  // file size, format token, flags, flags
    const uint32_t track_count = r.read<uint32_t>();
    const uint32_t frame_count = r.read<uint32_t>();
    a.fps = 1.f / r.read<float>();
    a.frames = static_cast<float>(frame_count > 0 ? frame_count - 1 : 0);
    const int32_t hashes_offset = r.read<int32_t>();
    r.skip(8);
    const int32_t vecs_offset = r.read<int32_t>();
    const int32_t quats_offset = r.read<int32_t>();
    const int32_t frames_offset = r.read<int32_t>();
    std::vector<Vec3> vecs;
    std::vector<Quat> quats;
    if (version == 5) {
      const size_t nvec = static_cast<size_t>(quats_offset - vecs_offset) / 12;
      const size_t nquat = static_cast<size_t>(hashes_offset - quats_offset) / 6;
      const size_t nhash = static_cast<size_t>(frames_offset - hashes_offset) / 4;
      r.seek(static_cast<size_t>(hashes_offset) + 12);
      std::vector<uint32_t> hashes(nhash);
      for (uint32_t& h : hashes) h = r.read<uint32_t>();
      r.seek(static_cast<size_t>(vecs_offset) + 12);
      for (size_t i = 0; i < nvec; ++i) vecs.push_back(vec3(r));
      r.seek(static_cast<size_t>(quats_offset) + 12);
      for (size_t i = 0; i < nquat; ++i) quats.push_back(decompress_quat(r.bytes(6)));
      if (hashes.size() < track_count) throw std::runtime_error("anm: fewer joint hashes than tracks");
      hashes.resize(track_count);
      const std::vector<size_t> slots = track_slots(hashes);
      r.seek(static_cast<size_t>(frames_offset) + 12);
      for (uint32_t f = 0; f < frame_count; ++f)
        for (uint32_t t = 0; t < track_count; ++t) {
          const uint16_t ti = r.read<uint16_t>(), si = r.read<uint16_t>(), ri = r.read<uint16_t>();
          Track& tr = a.tracks[slots[t]];
          tr.translate.push_back({static_cast<float>(f), vecs.at(ti)});
          tr.scale.push_back({static_cast<float>(f), vecs.at(si)});
          tr.rotate.push_back({static_cast<float>(f), quats.at(ri)});
        }
    } else {
      const size_t nvec = static_cast<size_t>(quats_offset - vecs_offset) / 12;
      const size_t nquat = static_cast<size_t>(frames_offset - quats_offset) / 16;
      r.seek(static_cast<size_t>(vecs_offset) + 12);
      for (size_t i = 0; i < nvec; ++i) vecs.push_back(vec3(r));
      r.seek(static_cast<size_t>(quats_offset) + 12);
      for (size_t i = 0; i < nquat; ++i) quats.push_back(quat(r));
      r.seek(static_cast<size_t>(frames_offset) + 12);
      for (uint32_t f = 0; f < frame_count; ++f)
        for (uint32_t t = 0; t < track_count; ++t) {
          const uint32_t hash = r.read<uint32_t>();
          const uint16_t ti = r.read<uint16_t>(), si = r.read<uint16_t>(), ri = r.read<uint16_t>();
          r.skip(2);
          if (f == 0) new_track(hash);  // each frame lists the tracks in the same order
          Track& tr = a.tracks.at(t);
          tr.translate.push_back({static_cast<float>(f), vecs.at(ti)});
          tr.scale.push_back({static_cast<float>(f), vecs.at(si)});
          tr.rotate.push_back({static_cast<float>(f), quats.at(ri)});
        }
    }
  } else {
    throw std::runtime_error("anm: unsupported format " + sig + " v" + std::to_string(version));
  }
  for (Track& t : a.tracks) {
    sort_keys(t.translate);
    sort_keys(t.rotate);
    sort_keys(t.scale);
    // keep consecutive rotations on the same hemisphere so interpolation takes the short way
    for (size_t i = 1; i < t.rotate.size(); ++i) {
      const Quat& p = t.rotate[i - 1].value;
      Quat& q = t.rotate[i].value;
      if (p[0] * q[0] + p[1] * q[1] + p[2] * q[2] + p[3] * q[3] < 0)
        for (float& c : q) c = -c;
    }
  }
  return a;
}

// ---------------------------------------------------------------- .scb
StaticMesh read_scb(std::span<const uint8_t> data) {
  ByteReader r(data);
  if (r.string(8) != "r3d2Mesh") throw std::runtime_error("scb: bad signature");
  const uint16_t major = r.read<uint16_t>(), minor = r.read<uint16_t>();
  r.skip(128);  // name
  const uint32_t vertex_count = r.read<uint32_t>(), face_count = r.read<uint32_t>();
  r.skip(4 + 24);  // flags, bounding box
  uint32_t vertex_type = 0;
  if (major == 3 && minor == 2) vertex_type = r.read<uint32_t>();
  std::vector<Vec3> verts(vertex_count);
  for (Vec3& v : verts) v = vec3(r);
  std::vector<std::array<uint8_t, 4>> colors;
  if (vertex_type == 1) {
    colors.resize(vertex_count);
    for (auto& c : colors) r.read_into(c.data(), 4);
  }
  r.skip(12);  // central point
  StaticMesh m;
  m.has_colors = !colors.empty();
  for (uint32_t f = 0; f < face_count; ++f) {
    uint32_t idx[3];
    for (uint32_t& i : idx) i = r.read<uint32_t>();
    r.skip(64);  // material name
    float uv[6];
    for (float& u : uv) u = r.read<float>();
    for (int c = 0; c < 3; ++c) {
      m.positions.push_back(verts.at(idx[c]));
      m.uvs.push_back({uv[c], uv[c + 3]});
      m.colors.push_back(m.has_colors ? colors.at(idx[c]) : std::array<uint8_t, 4>{255, 255, 255, 255});
    }
    const Vec3& a = verts.at(idx[0]);
    const Vec3& b = verts.at(idx[1]);
    const Vec3& c = verts.at(idx[2]);
    const float e1[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]}, e2[3] = {c[0] - a[0], c[1] - a[1], c[2] - a[2]};
    Vec3 n{e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]};
    const float l = std::sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
    if (l > 0) n = {n[0] / l, n[1] / l, n[2] / l};
    for (int k = 0; k < 3; ++k) m.normals.push_back(n);
  }
  return m;
}

// ---------------------------------------------------------------- sampling
namespace {

template <size_t N>
std::array<float, N> eval(const std::vector<Key<std::array<float, N>>>& keys, float f, bool catmull) {
  const size_t n = keys.size();
  if (n == 1 || f <= keys[0].frame) return keys[0].value;
  if (f >= keys[n - 1].frame) return keys[n - 1].value;
  size_t i = 0;
  while (i + 1 < n && keys[i + 1].frame <= f) ++i;
  const size_t i2 = i + 1;
  const float t1 = keys[i].frame, t2 = keys[i2].frame;
  const float h = t2 - t1;
  const float u = h > 0 ? (f - t1) / h : 0.f;
  std::array<float, N> out{};
  if (!catmull) {
    for (size_t c = 0; c < N; ++c) out[c] = keys[i].value[c] + (keys[i2].value[c] - keys[i].value[c]) * u;
    return out;
  }
  // Catmull-Rom through the keys with non-uniform spacing (what the game does with compressed clips)
  const size_t i0 = i > 0 ? i - 1 : 0;
  const size_t i3 = std::min(i + 2, n - 1);
  const float u2 = u * u, u3 = u2 * u;
  for (size_t c = 0; c < N; ++c) {
    const float p0 = keys[i0].value[c], p1 = keys[i].value[c], p2 = keys[i2].value[c], p3 = keys[i3].value[c];
    const float m1 = (p2 - p0) / std::max(t2 - keys[i0].frame, 1e-6f) * h;
    const float m2 = (p3 - p1) / std::max(keys[i3].frame - t1, 1e-6f) * h;
    out[c] = (2 * u3 - 3 * u2 + 1) * p1 + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * p2 + (u3 - u2) * m2;
  }
  return out;
}

}  // namespace

void sample(const Animation& a, const Track& t, float frame, Vec3& tr, Quat& rot, Vec3& sc) {
  if (!t.translate.empty()) tr = eval(t.translate, frame, a.compressed);
  if (!t.scale.empty()) sc = eval(t.scale, frame, a.compressed);
  if (!t.rotate.empty()) {
    rot = eval(t.rotate, frame, a.compressed);
    const float l = std::sqrt(rot[0] * rot[0] + rot[1] * rot[1] + rot[2] * rot[2] + rot[3] * rot[3]);
    if (l > 1e-9f)
      for (float& c : rot) c /= l;
  }
}

}  // namespace ba
