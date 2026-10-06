#include "ba/Texture.h"

#include <algorithm>
#include <stdexcept>
#include <string>

#include "ba/ByteReader.h"

namespace ba {

namespace {

uint32_t block_bytes(TexFormat f) { return f == TexFormat::BC1 ? 8 : f == TexFormat::BC2 || f == TexFormat::BC3 ? 16 : 4; }
bool compressed(TexFormat f) { return f != TexFormat::BGRA8; }

size_t mip_size(TexFormat f, uint32_t w, uint32_t h) {
  if (!compressed(f)) return static_cast<size_t>(w) * h * 4;
  return static_cast<size_t>((w + 3) / 4) * ((h + 3) / 4) * block_bytes(f);
}

uint32_t mip_count(uint32_t w, uint32_t h) {
  uint32_t n = 1;
  for (uint32_t m = std::max(w, h); m > 1; m >>= 1) ++n;
  return n;
}

Texture read_tex(ByteReader& r) {
  // "TEX\0", u16 width, u16 height, u8 ?, u8 format, u8 ?, u8 has mipmaps
  Texture t;
  r.skip(4);
  t.width = r.read<uint16_t>();
  t.height = r.read<uint16_t>();
  r.skip(1);
  const uint8_t fmt = r.read<uint8_t>();
  r.skip(1);
  const bool mipmaps = r.read<uint8_t>() != 0;
  switch (fmt) {
    case 10:
    case 11: t.format = TexFormat::BC1; break;
    case 12: t.format = TexFormat::BC3; break;
    case 20: t.format = TexFormat::BGRA8; break;
    default: throw std::runtime_error("tex: unsupported format " + std::to_string(fmt));
  }
  if (!mipmaps) {
    const size_t n = mip_size(t.format, t.width, t.height);
    auto b = r.bytes(n);
    t.mips.emplace_back(b.begin(), b.end());
    return t;
  }
  // Mips are stored smallest first.
  const uint32_t count = mip_count(t.width, t.height);
  t.mips.resize(count);
  for (uint32_t i = count; i-- > 0;) {
    const uint32_t w = std::max(t.width >> i, 1u);
    const uint32_t h = std::max(t.height >> i, 1u);
    auto b = r.bytes(mip_size(t.format, w, h));
    t.mips[i].assign(b.begin(), b.end());
  }
  return t;
}

Texture read_dds(ByteReader& r) {
  // "DDS ", then a 124-byte DDS_HEADER: size, flags, height, width, pitch, depth, mip count, 11 reserved, then the
  // 32-byte pixel format at byte 72 (size, flags, fourCC, ...)
  r.skip(4);
  const size_t header = r.pos();
  r.skip(8);  // size, flags
  Texture t;
  t.height = r.read<uint32_t>();
  t.width = r.read<uint32_t>();
  r.skip(8);  // pitch, depth
  uint32_t mips = r.read<uint32_t>();
  r.seek(header + 72 + 4);  // pixel format: skip its size, read its flags and fourCC
  const uint32_t pf_flags = r.read<uint32_t>();
  const uint32_t fourcc = r.read<uint32_t>();
  if (pf_flags & 0x4) {  // DDPF_FOURCC
    if (fourcc == 0x31545844) t.format = TexFormat::BC1;       // "DXT1"
    else if (fourcc == 0x33545844) t.format = TexFormat::BC2;  // "DXT3"
    else if (fourcc == 0x35545844) t.format = TexFormat::BC3;  // "DXT5"
    else throw std::runtime_error("dds: unsupported fourcc");
  } else {
    t.format = TexFormat::BGRA8;  // 32-bit BGRA, the uncompressed layout League uses
  }
  r.seek(header + 124);
  mips = std::max(mips, 1u);
  for (uint32_t i = 0; i < mips && r.remaining() > 0; ++i) {
    const uint32_t w = std::max(t.width >> i, 1u);
    const uint32_t h = std::max(t.height >> i, 1u);
    auto b = r.bytes(mip_size(t.format, w, h));
    t.mips.emplace_back(b.begin(), b.end());
  }
  return t;
}

}  // namespace

uint32_t Texture::row_pitch(uint32_t mip_width) const {
  if (!compressed(format)) return mip_width * 4;
  return ((mip_width + 3) / 4) * block_bytes(format);
}

Texture read_texture(std::span<const uint8_t> data) {
  ByteReader r(data);
  if (data.size() >= 4 && data[0] == 'T' && data[1] == 'E' && data[2] == 'X') return read_tex(r);
  if (data.size() >= 4 && data[0] == 'D' && data[1] == 'D' && data[2] == 'S') return read_dds(r);
  throw std::runtime_error("texture: unknown format");
}

}  // namespace ba
