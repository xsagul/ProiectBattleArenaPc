#include "Recorder.h"

#include <stdexcept>
#include <string>

namespace ba {

namespace {
template <typename T>
void put(std::ofstream& o, const T& v) {
  o.write(reinterpret_cast<const char*>(&v), sizeof v);
}
template <typename T>
T get(std::ifstream& in) {
  T v{};
  if (!in.read(reinterpret_cast<char*>(&v), sizeof v)) throw std::runtime_error("recording: cut short");
  return v;
}
}  // namespace

Recorder::Recorder(const std::filesystem::path& file, uint64_t match_id) : out_(file, std::ios::binary) {
  out_.write("BASR", 4);
  put(out_, uint32_t{5});
  put(out_, match_id);
}

void Recorder::events(int64_t tick, const std::vector<SpawnRequest>& spawns, const std::vector<Order>& orders) {
  if (spawns.empty() && orders.empty()) return;
  put(out_, uint8_t{1});
  put(out_, tick);
  put(out_, static_cast<uint32_t>(spawns.size()));
  for (const SpawnRequest& s : spawns) {
    put(out_, s.team);
    put(out_, static_cast<uint16_t>(s.character.size()));
    out_.write(s.character.data(), static_cast<std::streamsize>(s.character.size()));
    put(out_, s.x), put(out_, s.z), put(out_, s.move_speed), put(out_, s.pathfinding_radius), put(out_, s.facing);
  }
  put(out_, static_cast<uint32_t>(orders.size()));
  for (const Order& o : orders)
    put(out_, o.unit), put(out_, o.x), put(out_, o.z), put(out_, static_cast<uint8_t>(o.type)), put(out_, o.target), put(out_, o.slot);
  out_.flush();
}

void Recorder::checkpoint(int64_t tick, uint64_t checksum) {
  put(out_, uint8_t{2});
  put(out_, tick);
  put(out_, checksum);
  out_.flush();
}

Recording read_recording(const std::filesystem::path& file) {
  std::ifstream in(file, std::ios::binary);
  char magic[4];
  if (!in.read(magic, 4) || std::string(magic, 4) != "BASR") throw std::runtime_error("recording: not a BASR file");
  if (get<uint32_t>(in) != 5) throw std::runtime_error("recording: unsupported version");
  Recording r;
  r.match_id = get<uint64_t>(in);
  for (;;) {
    const int type = in.get();
    if (type == EOF) break;
    if (type == 1) {
      Recording::Events ev;
      ev.tick = get<int64_t>(in);
      const uint32_t ns = get<uint32_t>(in);
      for (uint32_t i = 0; i < ns; ++i) {
        SpawnRequest s;
        s.team = get<uint8_t>(in);
        s.character.resize(get<uint16_t>(in));
        in.read(s.character.data(), static_cast<std::streamsize>(s.character.size()));
        s.x = get<float>(in), s.z = get<float>(in), s.move_speed = get<float>(in), s.pathfinding_radius = get<float>(in), s.facing = get<float>(in);
        ev.spawns.push_back(s);
      }
      const uint32_t no = get<uint32_t>(in);
      for (uint32_t i = 0; i < no; ++i) {
        Order o;
        o.tick = ev.tick;
        o.unit = get<uint32_t>(in), o.x = get<float>(in), o.z = get<float>(in);
        o.type = static_cast<Order::Type>(get<uint8_t>(in));
        o.target = get<uint32_t>(in);
        o.slot = get<uint8_t>(in);
        ev.orders.push_back(o);
      }
      r.events.push_back(std::move(ev));
    } else if (type == 2) {
      const int64_t tick = get<int64_t>(in);
      r.checkpoints.emplace_back(tick, get<uint64_t>(in));
    } else {
      throw std::runtime_error("recording: unknown record " + std::to_string(type));
    }
  }
  return r;
}

}  // namespace ba
