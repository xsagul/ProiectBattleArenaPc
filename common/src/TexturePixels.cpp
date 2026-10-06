// Textures as plain pixels: BC1 / BC3 / BGRA8 mip 0 to RGBA8, and RGBA8 to a PNG (stored deflate blocks, no compressor).
// Used to show the game's own images (the lobby's champion icons) and to look at particle textures (bainfo tex).

#include <algorithm>
#include <cstring>
#include <string>
#include <vector>

#include "ba/Texture.h"

namespace ba {


namespace {

/** One 4x4 block: `kind` 1 = BC1, 2 = BC2 (explicit 4-bit alpha), 3 = BC3 (interpolated alpha). */
void decode_bc_block(const uint8_t* b, int kind, uint8_t out[16][4]) {
  uint8_t alpha[16];
  const bool bc3 = kind != 1;  // the colour part of BC2 and BC3 is always four-colour
  if (kind == 2) {
    for (int t = 0; t < 16; ++t) alpha[t] = static_cast<uint8_t>(((b[t / 2] >> ((t & 1) * 4)) & 15) * 17);
    b += 8;
  } else if (kind == 3) {
    const uint8_t a0 = b[0], a1 = b[1];
    uint8_t pal[8] = {a0, a1};
    if (a0 > a1)
      for (int i = 1; i < 7; ++i) pal[i + 1] = static_cast<uint8_t>(((7 - i) * a0 + i * a1) / 7);
    else {
      for (int i = 1; i < 5; ++i) pal[i + 1] = static_cast<uint8_t>(((5 - i) * a0 + i * a1) / 5);
      pal[6] = 0, pal[7] = 255;
    }
    uint64_t bits = 0;
    for (int i = 0; i < 6; ++i) bits |= static_cast<uint64_t>(b[2 + i]) << (8 * i);
    for (int t = 0; t < 16; ++t) alpha[t] = pal[(bits >> (3 * t)) & 7];
    b += 8;
  }
  uint16_t c[2];
  std::memcpy(c, b, 4);
  int pal[4][4];
  for (int i = 0; i < 2; ++i) pal[i][0] = ((c[i] >> 11) & 31) * 255 / 31, pal[i][1] = ((c[i] >> 5) & 63) * 255 / 63, pal[i][2] = (c[i] & 31) * 255 / 31, pal[i][3] = 255;
  for (int k = 0; k < 3; ++k) {
    if (c[0] > c[1] || bc3) {
      pal[2][k] = (2 * pal[0][k] + pal[1][k]) / 3, pal[3][k] = (pal[0][k] + 2 * pal[1][k]) / 3;
    } else {
      pal[2][k] = (pal[0][k] + pal[1][k]) / 2, pal[3][k] = 0;
    }
  }
  pal[2][3] = 255, pal[3][3] = (c[0] > c[1] || bc3) ? 255 : 0;
  uint32_t idx;
  std::memcpy(&idx, b + 4, 4);
  for (int t = 0; t < 16; ++t) {
    const int* p = pal[(idx >> (2 * t)) & 3];
    out[t][0] = static_cast<uint8_t>(p[0]), out[t][1] = static_cast<uint8_t>(p[1]), out[t][2] = static_cast<uint8_t>(p[2]);
    out[t][3] = bc3 ? alpha[t] : static_cast<uint8_t>(p[3]);
  }
}

}  // namespace

std::vector<uint8_t> texture_rgba(const Texture& t) {
  std::vector<uint8_t> px(static_cast<size_t>(t.width) * t.height * 4);
  const auto& m = t.mips[0];
  if (t.format == TexFormat::BGRA8) {
    for (size_t i = 0; i < px.size() / 4; ++i) px[i * 4] = m[i * 4 + 2], px[i * 4 + 1] = m[i * 4 + 1], px[i * 4 + 2] = m[i * 4], px[i * 4 + 3] = m[i * 4 + 3];
    return px;
  }
  const int kind = t.format == TexFormat::BC1 ? 1 : t.format == TexFormat::BC2 ? 2 : 3;
  const uint32_t bw = (t.width + 3) / 4, bh = (t.height + 3) / 4;
  for (uint32_t by = 0; by < bh; ++by)
    for (uint32_t bx = 0; bx < bw; ++bx) {
      uint8_t blk[16][4];
      decode_bc_block(m.data() + (static_cast<size_t>(by) * bw + bx) * (kind == 1 ? 8 : 16), kind, blk);
      for (int t2 = 0; t2 < 16; ++t2) {
        const uint32_t x = bx * 4 + static_cast<uint32_t>(t2 % 4), y = by * 4 + static_cast<uint32_t>(t2 / 4);
        if (x < t.width && y < t.height) std::memcpy(&px[(static_cast<size_t>(y) * t.width + x) * 4], blk[t2], 4);
      }
    }
  return px;
}

namespace {
uint32_t crc32(const uint8_t* d, size_t n, uint32_t c = 0xFFFFFFFFu) {
  static uint32_t table[256];
  static bool ready = false;
  if (!ready) {
    for (uint32_t i = 0; i < 256; ++i) {
      uint32_t r = i;
      for (int k = 0; k < 8; ++k) r = (r & 1) ? 0xEDB88320u ^ (r >> 1) : r >> 1;
      table[i] = r;
    }
    ready = true;
  }
  for (size_t i = 0; i < n; ++i) c = table[(c ^ d[i]) & 255] ^ (c >> 8);
  return c;
}

}  // namespace

std::string encode_png(uint32_t w, uint32_t h, const std::vector<uint8_t>& rgba) {
  std::string raw;
  for (uint32_t y = 0; y < h; ++y) {
    raw.push_back('\0');
    raw.append(reinterpret_cast<const char*>(&rgba[static_cast<size_t>(y) * w * 4]), w * 4);
  }
  std::string z = "\x78\x01";
  uint32_t a = 1, b = 0;
  for (unsigned char ch : raw) a = (a + ch) % 65521, b = (b + a) % 65521;
  for (size_t at = 0; at < raw.size(); at += 65535) {
    const size_t n = std::min<size_t>(65535, raw.size() - at);
    z.push_back(at + n >= raw.size() ? 1 : 0);
    z.push_back(static_cast<char>(n & 255)), z.push_back(static_cast<char>(n >> 8));
    z.push_back(static_cast<char>(~n & 255)), z.push_back(static_cast<char>((~n >> 8) & 255));
    z.append(raw, at, n);
  }
  const uint32_t adler = (b << 16) | a;
  for (int s = 24; s >= 0; s -= 8) z.push_back(static_cast<char>((adler >> s) & 255));
  std::string out = "\x89PNG\r\n\x1a\n";
  auto chunk = [&out](const char* type, const std::string& data) {
    for (int s = 24; s >= 0; s -= 8) out.push_back(static_cast<char>((data.size() >> s) & 255));
    std::string body = std::string(type, 4) + data;
    out += body;
    const uint32_t c = ~crc32(reinterpret_cast<const uint8_t*>(body.data()), body.size());
    for (int s = 24; s >= 0; s -= 8) out.push_back(static_cast<char>((c >> s) & 255));
  };
  std::string ihdr;
  for (uint32_t v : {w, h})
    for (int s = 24; s >= 0; s -= 8) ihdr.push_back(static_cast<char>((v >> s) & 255));
  ihdr += std::string("\x08\x06\x00\x00\x00", 5);  // 8-bit RGBA
  chunk("IHDR", ihdr);
  chunk("IDAT", z);
  chunk("IEND", "");
  return out;
}

}  // namespace ba
