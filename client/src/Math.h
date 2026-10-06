#pragma once
// Small vector / matrix helpers. League's world is already left-handed with Y up (x to the east, z to the north, blue
// base in the low corner), the same handedness as Direct3D, so it is drawn as it is: no mirroring anywhere.
// Matrices are row-major and used with row vectors (v * M), like League's own (translation in the last row).

#include <cmath>

namespace ba {

struct float3 {
  float x = 0, y = 0, z = 0;
};

inline float3 operator-(float3 a, float3 b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
inline float3 operator+(float3 a, float3 b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
inline float3 operator*(float3 a, float s) { return {a.x * s, a.y * s, a.z * s}; }
inline float dot(float3 a, float3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline float3 cross(float3 a, float3 b) { return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x}; }
inline float3 normalize(float3 a) {
  const float l = std::sqrt(dot(a, a));
  return l > 0 ? a * (1.f / l) : a;
}

struct float4x4 {
  float m[4][4] = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}, {0, 0, 0, 1}};
};

inline float4x4 operator*(const float4x4& a, const float4x4& b) {
  float4x4 r;
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j) {
      r.m[i][j] = 0;
      for (int k = 0; k < 4; ++k) r.m[i][j] += a.m[i][k] * b.m[k][j];
    }
  return r;
}

inline float4x4 look_at_lh(float3 eye, float3 at, float3 up) {
  const float3 z = normalize(at - eye);
  const float3 x = normalize(cross(up, z));
  const float3 y = cross(z, x);
  float4x4 r;
  r.m[0][0] = x.x, r.m[0][1] = y.x, r.m[0][2] = z.x, r.m[0][3] = 0;
  r.m[1][0] = x.y, r.m[1][1] = y.y, r.m[1][2] = z.y, r.m[1][3] = 0;
  r.m[2][0] = x.z, r.m[2][1] = y.z, r.m[2][2] = z.z, r.m[2][3] = 0;
  r.m[3][0] = -dot(x, eye), r.m[3][1] = -dot(y, eye), r.m[3][2] = -dot(z, eye), r.m[3][3] = 1;
  return r;
}

inline float4x4 perspective_lh(float fov_y, float aspect, float zn, float zf) {
  const float h = 1.f / std::tan(fov_y * 0.5f);
  float4x4 r;
  r.m[0][0] = h / aspect;
  r.m[1][1] = h;
  r.m[2][2] = zf / (zf - zn);
  r.m[2][3] = 1;
  r.m[3][2] = -zn * zf / (zf - zn);
  r.m[3][3] = 0;
  return r;
}

inline float3 transform_point(float3 p, const float4x4& m) {
  return {p.x * m.m[0][0] + p.y * m.m[1][0] + p.z * m.m[2][0] + m.m[3][0], p.x * m.m[0][1] + p.y * m.m[1][1] + p.z * m.m[2][1] + m.m[3][1],
          p.x * m.m[0][2] + p.y * m.m[1][2] + p.z * m.m[2][2] + m.m[3][2]};
}

}  // namespace ba
