#pragma once
// League's textures: .tex ("TEX\0", 12-byte header) and .dds. The block-compressed formats (DXT1 = BC1, DXT3 = BC2 in a few of patch
// 14.1's .dds, DXT5 = BC3) go to
// the graphics card as they are, mip by mip, without ever being decompressed.

#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace ba {

enum class TexFormat : uint8_t { BC1, BC2, BC3, BGRA8 };

struct Texture {
  TexFormat format = TexFormat::BGRA8;
  uint32_t width = 0;
  uint32_t height = 0;
  /** Mip levels, largest first. */
  std::vector<std::vector<uint8_t>> mips;

  /** Bytes per row of blocks (or pixels) of a mip level of the given width. */
  uint32_t row_pitch(uint32_t mip_width) const;
};

/** Reads a .tex or .dds file (detected from its signature). */
Texture read_texture(std::span<const uint8_t> data);

/** Mip 0 as RGBA8 rows (BC1, BC2, BC3 and BGRA8). */
std::vector<uint8_t> texture_rgba(const Texture& t);
/** RGBA8 pixels as a PNG file's bytes. */
std::string encode_png(uint32_t w, uint32_t h, const std::vector<uint8_t>& rgba);

}  // namespace ba
