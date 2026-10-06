#pragma once
// Little-endian reading over a byte buffer, with bounds checks: League's files are all little-endian binary.

#include <cstdint>
#include <cstring>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>

namespace ba {

class ByteReader {
 public:
  explicit ByteReader(std::span<const uint8_t> data) : data_(data) {}

  size_t pos() const { return pos_; }
  size_t size() const { return data_.size(); }
  size_t remaining() const { return data_.size() - pos_; }
  void seek(size_t p) {
    if (p > data_.size()) throw std::out_of_range("ByteReader: seek past end");
    pos_ = p;
  }
  void skip(size_t n) { seek(pos_ + n); }

  template <typename T>
  T read() {
    need(sizeof(T));
    T v;
    std::memcpy(&v, data_.data() + pos_, sizeof(T));
    pos_ += sizeof(T);
    return v;
  }

  void read_into(void* out, size_t n) {
    need(n);
    std::memcpy(out, data_.data() + pos_, n);
    pos_ += n;
  }

  std::span<const uint8_t> bytes(size_t n) {
    need(n);
    auto s = data_.subspan(pos_, n);
    pos_ += n;
    return s;
  }

  std::string string(size_t n) {
    auto s = bytes(n);
    return std::string(reinterpret_cast<const char*>(s.data()), s.size());
  }

  /** A string prefixed by its 16-bit length (League's .bin strings). */
  std::string string16() { return string(read<uint16_t>()); }

 private:
  void need(size_t n) const {
    if (pos_ + n > data_.size()) throw std::out_of_range("ByteReader: read past end");
  }

  std::span<const uint8_t> data_;
  size_t pos_ = 0;
};

}  // namespace ba
