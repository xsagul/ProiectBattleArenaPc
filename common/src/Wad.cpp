#include "ba/Wad.h"

#include <cstring>
#include <stdexcept>
#include <string>

#include "ba/ByteReader.h"
#include "ba/Hash.h"
#include "zstd.h"

namespace ba {

namespace {

constexpr uint32_t kZstdMagic = 0xFD2FB528u;  // 28 B5 2F FD

std::vector<uint8_t> zstd_frames(std::span<const uint8_t> src, size_t expected) {
  // Type 4 entries are split into sub-chunks: some are zstd frames, some are stored raw. Frames are found by their
  // magic; anything between frames is copied as it is.
  std::vector<uint8_t> out;
  out.reserve(expected);
  size_t p = 0;
  while (p < src.size()) {
    uint32_t magic = 0;
    if (src.size() - p >= 4) std::memcpy(&magic, src.data() + p, 4);
    if (magic == kZstdMagic) {
      const size_t frame = ZSTD_findFrameCompressedSize(src.data() + p, src.size() - p);
      if (ZSTD_isError(frame)) throw std::runtime_error("wad: bad zstd frame");
      unsigned long long size = ZSTD_getFrameContentSize(src.data() + p, frame);
      if (size == ZSTD_CONTENTSIZE_UNKNOWN || size == ZSTD_CONTENTSIZE_ERROR) size = expected > out.size() ? expected - out.size() : 0;
      const size_t at = out.size();
      out.resize(at + static_cast<size_t>(size));
      const size_t got = ZSTD_decompress(out.data() + at, static_cast<size_t>(size), src.data() + p, frame);
      if (ZSTD_isError(got)) throw std::runtime_error(std::string("wad: zstd: ") + ZSTD_getErrorName(got));
      out.resize(at + got);
      p += frame;
    } else {
      // raw bytes up to the next frame (or the end)
      size_t q = p + 1;
      while (q + 4 <= src.size()) {
        uint32_t m = 0;
        std::memcpy(&m, src.data() + q, 4);
        if (m == kZstdMagic) break;
        ++q;
      }
      if (q + 4 > src.size()) q = src.size();
      out.insert(out.end(), src.begin() + static_cast<std::ptrdiff_t>(p), src.begin() + static_cast<std::ptrdiff_t>(q));
      p = q;
    }
  }
  return out;
}

}  // namespace

Wad::Wad(const std::filesystem::path& file) : file_(file), in_(file, std::ios::binary) {
  if (!in_) throw std::runtime_error("wad: cannot open " + file.string());
  std::vector<uint8_t> head(272);
  in_.read(reinterpret_cast<char*>(head.data()), static_cast<std::streamsize>(head.size()));
  if (head[0] != 'R' || head[1] != 'W') throw std::runtime_error("wad: not a WAD file: " + file.string());
  major_ = head[2];
  if (major_ != 3) throw std::runtime_error("wad: unsupported version " + std::to_string(major_));
  uint32_t count = 0;
  std::memcpy(&count, head.data() + 268, 4);
  std::vector<uint8_t> toc(static_cast<size_t>(count) * 32);
  in_.read(reinterpret_cast<char*>(toc.data()), static_cast<std::streamsize>(toc.size()));
  ByteReader r(toc);
  entries_.reserve(count);
  for (uint32_t i = 0; i < count; ++i) {
    WadEntry e;
    e.hash = r.read<uint64_t>();
    e.offset = r.read<uint32_t>();
    e.compressed = r.read<uint32_t>();
    e.size = r.read<uint32_t>();
    e.type = r.read<uint8_t>() & 0x0F;
    r.skip(1 + 2 + 8);  // duplicate, first sub-chunk, checksum
    entries_[e.hash] = e;
  }
}

bool Wad::has(std::string_view path) const { return entries_.count(wad_hash(path)) != 0; }

std::optional<std::vector<uint8_t>> Wad::read(std::string_view path) const { return read_hash(wad_hash(path)); }

std::optional<std::vector<uint8_t>> Wad::read_hash(uint64_t hash) const {
  auto it = entries_.find(hash);
  if (it == entries_.end()) return std::nullopt;
  const WadEntry& e = it->second;
  std::vector<uint8_t> raw(e.compressed);
  in_.clear();
  in_.seekg(e.offset);
  in_.read(reinterpret_cast<char*>(raw.data()), static_cast<std::streamsize>(raw.size()));
  switch (e.type) {
    case 0:
      return raw;
    case 3:
    case 4:
      return zstd_frames(raw, e.size);
    default:
      // 1 (gzip) and 2 (link to another file) do not occur in the archives this game reads.
      throw std::runtime_error("wad: unsupported entry type " + std::to_string(e.type));
  }
}

}  // namespace ba
