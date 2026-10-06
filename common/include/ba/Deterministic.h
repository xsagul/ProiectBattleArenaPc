#pragma once
// The match server's notion of time and chance, kept deterministic the way League's server is (Riot's "Determinism in
// League of Legends" series): one clock counted in whole ticks, one pseudo-random generator (xorshift) seeded by the
// match id. The same recorded inputs then always give the same game.

#include <cstdint>

namespace ba {

/** League's server tick: 0.033 s, i.e. 30.3 updates per second. */
constexpr int64_t kTickMicros = 33'000;
constexpr double kTickSeconds = kTickMicros / 1'000'000.0;

/** Game time as a whole number of ticks; seconds only when read. */
struct GameClock {
  int64_t tick = 0;
  double seconds() const { return static_cast<double>(tick) * kTickSeconds; }
  /** League rounds every duration up to whole ticks (a 0.25 s cast ends on tick 8, after 0.264 s). */
  static int64_t ticks_for(double seconds) {
    const double t = seconds / kTickSeconds;
    const auto whole = static_cast<int64_t>(t);
    return t > static_cast<double>(whole) + 1e-9 ? whole + 1 : whole;
  }
};

/** xorshift64*: the single source of randomness of a match. */
class Random {
 public:
  explicit Random(uint64_t seed) : s_(seed ? seed : 0x9E3779B97F4A7C15ull) {}
  uint64_t next() {
    s_ ^= s_ >> 12;
    s_ ^= s_ << 25;
    s_ ^= s_ >> 27;
    return s_ * 0x2545F4914F6CDD1Dull;
  }
  /** Uniform in [0, 1). */
  double unit() { return static_cast<double>(next() >> 11) * (1.0 / 9007199254740992.0); }
  double range(double a, double b) { return a + (b - a) * unit(); }
  /** The generator's state (checksums of the match). */
  uint64_t state() const { return s_; }

 private:
  uint64_t s_;
};

}  // namespace ba
