// Evidence inventory, NOT a visual-parity test. Uses the same WAD/BIN/SKL/SKN/ANM readers as client.exe.
// Scans base skins for every installed champion; reports missing data and renderer features still approximated.
// animation_audit --data <patch root> --out <report.json> [--hashes research/hashes] [--scripts server/scripts]
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>
#include "ba/GameData.h"
#include "ba/Hash.h"
#include "ba/HashNames.h"
#include "ba/Model.h"
#include "ba/PropertyBin.h"
#include "ba/Wad.h"

namespace fs = std::filesystem;
using namespace ba;

namespace {
std::string json(const std::string& s) {
  std::ostringstream o;
  o << '"';
  for (unsigned char c : s) {
    if (c == '"' || c == '\\') o << '\\' << c;
    else if (c < 32) o << "\\u" << std::hex << std::setw(4) << std::setfill('0') << unsigned(c);
    else o << c;
  }
  return o.str() + '"';
}
std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return s;
}
uint64_t file_hash(const BinValue& v) { return v.type == BinType::String ? wad_hash(v.str) : v.u; }
std::string file_name(const BinValue& v, const HashNames& names) { return v.type == BinType::String ? v.str : names.name64(v.u); }
struct Finding { std::string code, clip, detail; };
struct Audit {
  std::string champion, wad, graph;
  bool playable = false;
  size_t atomic = 0, decoded = 0, joints = 0, vertices = 0;
  std::map<std::string, size_t> classes, events, updaters;
  std::vector<Finding> errors, gaps;
  void error(std::string code, std::string clip, std::string detail) { errors.push_back({code, clip, detail}); }
  void gap(std::string code, std::string clip, std::string detail) { gaps.push_back({code, clip, detail}); }
};
void counts(std::ostream& o, const std::map<std::string, size_t>& values) {
  o << '{'; bool comma = false;
  for (auto& [k,v] : values) { if (comma) o << ','; comma = true; o << json(k) << ':' << v; }
  o << '}';
}
void findings(std::ostream& o, const std::vector<Finding>& values) {
  o << '['; bool comma = false;
  for (auto& v : values) {
    if (comma) o << ','; comma = true;
    o << "{\"code\":" << json(v.code) << ",\"clip\":" << json(v.clip) << ",\"detail\":" << json(v.detail) << '}';
  }
  o << ']';
}
Audit audit(const fs::path& path, const fs::path& scripts, const HashNames& names) {
  Audit a;
  a.champion = path.filename().string().substr(0, path.filename().string().size() - 11);
  a.wad = path.generic_string();
  a.playable = fs::is_regular_file(scripts / (a.champion + ".lua"));
  const std::string base = "data/characters/" + lower(a.champion);
  try {
    Wad wad(path);
    auto bytes = wad.read(base + "/skins/skin0.bin");
    if (!bytes) { a.error("missing_skin", "", base + "/skins/skin0.bin"); return a; }
    PropertyBin skin(*bytes);
    const BinEntry* props = nullptr;
    for (const auto& e : skin.entries()) if (e.cls == fnv1a("SkinCharacterDataProperties")) props = &e;
    if (!props) { a.error("missing_skin_properties", "", "SkinCharacterDataProperties"); return a; }
    const BinValue* mesh = props->field("skinMeshProperties");
    Skeleton skeleton;
    if (mesh) {
      for (const char* field : {"skeleton", "simpleSkin"}) {
        const auto* v = mesh->field(field);
        const auto data = v ? wad.read_hash(file_hash(*v)) : std::nullopt;
        if (!data) { a.error("missing_model_resource", "", field); continue; }
        if (std::string(field) == "skeleton") { skeleton = read_skl(*data); a.joints = skeleton.joints.size(); }
        else a.vertices = read_skn(*data).vertices.size();
      }
    } else a.error("missing_mesh_properties", "", "skinMeshProperties");
    a.graph = base + "/animations/skin0.bin";
    for (const auto& link : skin.links()) if (lower(link).find("/animations/") != std::string::npos) a.graph = lower(link);
    auto graph_bytes = wad.read(a.graph);
    if (!graph_bytes) { a.error("missing_graph", "", a.graph); return a; }
    const PropertyBin graph(*graph_bytes);
    std::map<uint32_t, const BinValue*> clips;
    for (const auto& e : graph.entries()) {
      if (const auto* m = e.field("mClipDataMap")) for (const auto& [key,value] : m->pairs) clips[static_cast<uint32_t>(key.u)] = &value;
      if (const auto* b = e.field("mBlendDataTable")) for (const auto& [key,value] : b->pairs) {
        if (value.cls != fnv1a("TimeBlendData")) a.gap("blend_type", names.name64(key.u), names.name32(value.cls));
      }
    }
    if (clips.empty()) a.error("empty_graph", "", a.graph);
    const std::set<uint32_t> supported = {fnv1a("AtomicClipData"), fnv1a("SequencerClipData"), fnv1a("ParallelClipData"),
      fnv1a("SelectorClipData"), fnv1a("ConditionBoolClipData"), fnv1a("ConditionFloatClipData"), fnv1a("ParametricClipData")};
    for (const auto& [key,ptr] : clips) {
      const BinValue& c = *ptr;
      const std::string name = names.name32(key);
      ++a.classes[names.name32(c.cls)];
      if (!supported.count(c.cls)) a.gap("unknown_clip_type", name, names.name32(c.cls));
      if (c.cls == fnv1a("SelectorClipData")) a.gap("selector_first_child", name, "mProbability is not used by the renderer");
      if (c.cls == fnv1a("ParametricClipData")) a.gap("parametric_nearest_zero", name, "No interpolation or updater value in renderer");
      if (c.cls == fnv1a("ConditionBoolClipData")) a.gap("bool_driver_not_evaluated", name, "Renderer uses one shared boolean instead of evaluating this driver");
      if (c.cls == fnv1a("ParallelClipData")) a.gap("parallel_semantics_unverified", name, "Missing-track fill is not a verified implementation of graph track weights");
      if (const auto* u = c.field("Updater")) {
        ++a.updaters[names.name32(u->cls)];
        if (c.cls == fnv1a("ConditionFloatClipData") && u->cls != fnv1a("MoveSpeedParametricUpdater"))
          a.gap("float_updater_zero", name, names.name32(u->cls));
      }
      auto child = [&](uint32_t hash) { if (hash && !clips.count(hash)) a.error("missing_child_clip", name, names.name32(hash)); };
      for (const char* f : {"mTrueConditionClipName", "mFalseConditionClipName"}) if (const auto* v = c.field(f)) child(static_cast<uint32_t>(v->u));
      if (const auto* list = c.field("mClipNameList")) for (const auto& v : list->items) child(static_cast<uint32_t>(v.u));
      for (const char* f : {"mSelectorPairDataList", "mParametricPairDataList", "mConditionFloatPairDataList"})
        if (const auto* list = c.field(f)) for (const auto& v : list->items) if (const auto* n = v.field("mClipName")) child(static_cast<uint32_t>(n->u));
      if (c.cls != fnv1a("AtomicClipData")) continue;
      ++a.atomic;
      const auto* res = c.field("mAnimationResourceData");
      const auto* file = res ? res->field("mAnimationFilePath") : nullptr;
      auto animation = file ? wad.read_hash(file_hash(*file)) : std::nullopt;
      if (!animation) { a.error("missing_animation", name, file ? file_name(*file, names) : "no mAnimationFilePath"); continue; }
      try {
        const Animation anm = read_anm(*animation);
        if (!(anm.fps > 0) || !std::isfinite(anm.fps) || !std::isfinite(anm.frames) || anm.frames < 0)
          a.error("invalid_animation_time", name, file_name(*file, names));
        else ++a.decoded;
      } catch (const std::exception& e) { a.error("animation_decode_failed", name, file_name(*file, names) + ": " + e.what()); }
      if (const auto* evs = c.field("mEventDataMap")) for (const auto& [ek,ev] : evs->pairs) {
        (void)ek;
        ++a.events[names.name32(ev.cls)];
        if (ev.cls != fnv1a("ParticleEventData") && ev.cls != fnv1a("SubmeshVisibilityEventData"))
          a.gap("event_not_implemented", name, names.name32(ev.cls));
        if (ev.cls == fnv1a("ParticleEventData")) {
          if (const auto* list = ev.field("mParticleEventDataPairList")) {
            if (list->items.size() > 1) a.gap("particle_first_attachment", name, std::to_string(list->items.size()) + " attachment pairs, renderer takes only first");
            for (const auto& pair : list->items) if (const auto* target = pair.field("mTargetBoneName"); target && target->u)
              a.gap("particle_target_bone_ignored", name, names.name32(static_cast<uint32_t>(target->u)));
          }
          for (const char* f : {"mEnemyEffectKey", "mScalePlaySpeedWithAnimation", "SkipIfPastEndFrame"})
            if (const auto* v = ev.field(f); v && (v->u || v->number())) a.gap("particle_field_ignored", name, f);
        }
      }
    }
  } catch (const std::exception& e) { a.error("archive_or_model_decode_failed", "", e.what()); }
  return a;
}
}

int main(int argc, char** argv) {
  std::string data_arg, output = "animation-audit.json", hashes = "research/hashes", scripts = "server/scripts";
  for (int i = 1; i + 1 < argc; i += 2) {
    std::string k = argv[i], v = argv[i+1];
    if (k == "--data") data_arg = v;
    else if (k == "--out") output = v;
    else if (k == "--hashes") hashes = v;
    else if (k == "--scripts") scripts = v;
    else { std::cerr << "unknown option: " << k << '\n'; return 1; }
  }
  try {
    HashNames names;
    for (const auto& f : fs::directory_iterator(hashes)) if (f.is_regular_file() && f.path().extension() == ".txt") names.load(f.path());
    const auto data = find_game_data(data_arg, fs::current_path());
    std::vector<fs::path> wads;
    for (const auto& f : fs::directory_iterator(data / "DATA/FINAL/Champions")) {
      const auto n = f.path().filename().string();
      if (f.is_regular_file() && n.ends_with(".wad.client") && n.substr(0,n.size()-11).find('.') == std::string::npos) wads.push_back(f.path());
    }
    std::sort(wads.begin(), wads.end());
    if (wads.empty()) throw std::runtime_error("no champion archives found");
    std::ofstream o(output);
    if (!o) throw std::runtime_error("cannot write report");
    o << "{\"schema\":1,\"scope\":\"installed champion base skins; data integrity and known renderer gaps, NOT visual parity\",\"data_root\":" << json(data.generic_string()) << ",\"champions\":[\n";
    size_t errors = 0, gaps = 0, decoded = 0, playable = 0;
    for (size_t i = 0; i < wads.size(); ++i) {
      const Audit a = audit(wads[i], scripts, names);
      errors += a.errors.size(); gaps += a.gaps.size(); decoded += a.decoded; playable += a.playable;
      if (i) o << ",\n";
      o << "{\"champion\":" << json(a.champion) << ",\"wad\":" << json(a.wad) << ",\"skin\":0,\"graph\":" << json(a.graph)
        << ",\"has_local_gameplay_script\":" << (a.playable ? "true" : "false") << ",\"joints\":" << a.joints << ",\"vertices\":" << a.vertices
        << ",\"atomic_clips\":" << a.atomic << ",\"decoded_clips\":" << a.decoded << ",\"clip_classes\":";
      counts(o,a.classes); o << ",\"event_classes\":"; counts(o,a.events); o << ",\"updaters\":"; counts(o,a.updaters);
      o << ",\"data_errors\":"; findings(o,a.errors); o << ",\"known_renderer_gaps\":"; findings(o,a.gaps); o << '}';
      std::cout << a.champion << ": " << a.decoded << '/' << a.atomic << " clips decoded, " << a.errors.size() << " data errors, " << a.gaps.size() << " known gaps\n";
    }
    o << "\n],\"summary\":{\"champions\":" << wads.size() << ",\"with_gameplay_script\":" << playable << ",\"decoded_clips\":" << decoded
      << ",\"data_errors\":" << errors << ",\"known_renderer_gaps\":" << gaps << "}}\n";
    if (!o) throw std::runtime_error("report write failed");
    return errors ? 2 : 0; // Gaps remain even with exit 0; absence of parse errors is not parity.
  } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
