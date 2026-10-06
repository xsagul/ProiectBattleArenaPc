// lobby.exe: the out-of-game client, built the way League's is (the LCU): a local service on 127.0.0.1 with an HTTP API,
// and a web page as its interface (League shows it in an embedded browser; we open the default one). Picking a champion
// and pressing Start launches server.exe, then client.exe with that champion, as League's client launches the game.
//
//   lobby.exe [--port 21337] [--data <folder with DATA/FINAL>] [--no-browser 1]
//
//   GET  /                     the page (lobby_www/index.html next to the exe); other files of lobby_www by name
//   GET  /fe/<plugin>/<file>   a file of the 14.1 client's front-end plugin rcp-fe-<plugin> (style sheets, pictures,
//                              sounds, fonts), under the address League's own client serves it at; from
//                              lcu-data/14.1/plugins/rcp-fe-<plugin>/global/default/
//   GET  /lol-game-data/assets/<file>   the client's game data (champion portraits, splashes ...), from
//                              lcu-data/14.1/plugins/rcp-be-lol-game-data/global/default/
//   GET  /lol/champions        the champions this install has: [{"name": "Garen"}, ...]
//   GET  /lol/icon/<name>      the champion's square icon (its skin0 iconSquare texture), as PNG
//   POST /lol/start            body "champion=<name>&name=<summoner>": starts a match
//   GET  /lol/status           {"inGame": true|false}
//   GET  /lol/me               {"name": the player's name}

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <shellapi.h>

#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "ba/GameData.h"
#include "ba/Hash.h"
#include "ba/PropertyBin.h"
#include "ba/Texture.h"
#include "ba/Wad.h"

using namespace ba;
namespace fs = std::filesystem;

namespace {

fs::path g_exe_dir, g_data, g_lcu;  // g_lcu: lcu-data/14.1/plugins (empty when the install has none)
uint16_t g_game_port = 5119;
std::mutex g_game_mutex;
HANDLE g_server = nullptr, g_client = nullptr;

// ---------------------------------------------------------------- the champions this install has

std::vector<std::string> champions() {
  std::vector<std::string> out;
  std::error_code ec;
  for (const auto& e : fs::directory_iterator(g_data / "DATA" / "FINAL" / "Champions", ec)) {
    const std::string f = e.path().filename().string();
    const std::string ext = ".wad.client";
    if (f.size() <= ext.size() || f.compare(f.size() - ext.size(), ext.size(), ext) != 0) continue;
    const std::string name = f.substr(0, f.size() - ext.size());
    // the champions the server can play: those whose abilities it has a script for (scripts/<Champion>.lua); the
    // archives of the others, and the texts' archives (Garen.en_US), are not champions to pick
    if (name.find('.') != std::string::npos || !fs::exists(g_exe_dir / "scripts" / (name + ".lua"), ec)) continue;
    out.push_back(name);
  }
  std::sort(out.begin(), out.end());
  return out;
}

/** The champion's square icon: skin0's iconSquare, decoded. Empty when missing. */
std::string icon_png(const std::string& name) {
  try {
    Wad wad(g_data / "DATA" / "FINAL" / "Champions" / (name + ".wad.client"));
    std::string lower = name;
    for (char& c : lower) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    auto bytes = wad.read("data/characters/" + lower + "/skins/skin0.bin");
    if (!bytes) return {};
    const PropertyBin bin(*bytes);
    for (const BinEntry& e : bin.entries()) {
      const BinValue* list = e.field("iconSquare");
      if (!list || list->items.empty()) continue;
      const BinValue& v = list->items[0];
      auto tex = wad.read_hash(v.type == BinType::String ? wad_hash(v.str) : v.u);
      if (!tex) return {};
      const Texture t = read_texture(*tex);
      return encode_png(t.width, t.height, texture_rgba(t));
    }
  } catch (const std::exception&) {
  }
  return {};
}

// ---------------------------------------------------------------- starting a match

HANDLE launch(const fs::path& exe, const std::wstring& args, bool hidden = false) {
  std::wstring cmd = L"\"" + exe.wstring() + L"\" " + args;
  STARTUPINFOW si{};
  si.cb = sizeof si;
  PROCESS_INFORMATION pi{};
  if (!CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, FALSE, hidden ? CREATE_NO_WINDOW : 0, nullptr, g_exe_dir.c_str(), &si, &pi)) return nullptr;
  CloseHandle(pi.hThread);
  return pi.hProcess;
}

bool in_game() {
  std::lock_guard<std::mutex> lock(g_game_mutex);
  return g_client && WaitForSingleObject(g_client, 0) == WAIT_TIMEOUT;
}

std::string start_match(const std::string& champion, const std::string& summoner, const std::string& mode, const std::string& map) {
  // 14.1 _generatePracticeToolPayload: PRACTICETOOL, mapId 11, teamSize 1, mutators.id 1.
  // The local server currently implements only this mode. Reject others instead of silently launching map 11.
  if (mode != "PRACTICETOOL" || map != "11") return "{\"ok\":false,\"error\":\"unsupported game mode or map\"}";
  const auto list = champions();
  if (std::find(list.begin(), list.end(), champion) == list.end()) return "{\"ok\":false,\"error\":\"unknown champion\"}";
  std::lock_guard<std::mutex> lock(g_game_mutex);
  // The check and launch share the lock, including requests arriving from two browser tabs at once.
  if (g_client) return "{\"ok\":false,\"error\":\"a match is already running\"}";
  const std::wstring data = L"--data \"" + g_data.wstring() + L"\"";
  const std::wstring port = std::to_wstring(g_game_port);
  const fs::path record = g_exe_dir / "last_match.basr";
  // as League does: the game server first, then the game client pointed at it
  const std::wstring ready_name = L"Local\\BattleArenaReady-" + std::to_wstring(GetCurrentProcessId()) + L"-" + std::to_wstring(GetTickCount64());
  HANDLE ready = CreateEventW(nullptr, TRUE, FALSE, ready_name.c_str());
  if (!ready) return "{\"ok\":false,\"error\":\"cannot create server readiness event\"}";
  g_server = launch(g_exe_dir / "server.exe", L"--port " + port + L" " + data + L" --mode PRACTICETOOL --ready-event \"" + ready_name +
                    L"\" --record \"" + record.wstring() + L"\"", true);
  if (!g_server) { CloseHandle(ready); return "{\"ok\":false,\"error\":\"server.exe did not start\"}"; }
  const HANDLE signals[] = {ready, g_server};
  const DWORD status = WaitForMultipleObjects(2, signals, FALSE, 60000);
  CloseHandle(ready);
  if (status != WAIT_OBJECT_0) {
    TerminateProcess(g_server, 1);
    WaitForSingleObject(g_server, 5000);
    CloseHandle(g_server);
    g_server = nullptr;
    return "{\"ok\":false,\"error\":\"server failed to become ready\"}";
  }
  const std::wstring champ(champion.begin(), champion.end());
  // the summoner's name: letters, digits and spaces only (it goes on a command line)
  std::wstring who;
  for (char c : summoner)
    if (std::isalnum(static_cast<unsigned char>(c)) || c == ' ') who.push_back(static_cast<wchar_t>(c));
  if (who.empty()) who = L"Player";
  g_client = launch(g_exe_dir / "client.exe", L"--port " + port + L" " + data + L" --champion " + champ + L" --name \"" + who + L"\"");
  if (!g_client) {
    TerminateProcess(g_server, 0);
    WaitForSingleObject(g_server, 5000);
    CloseHandle(g_server);
    g_server = nullptr;
    return "{\"ok\":false,\"error\":\"client.exe did not start\"}";
  }
  // when the game window closes, the match ends: the server goes with it
  HANDLE client = g_client, server = g_server;
  std::thread([client, server] {
    WaitForSingleObject(client, INFINITE);
    TerminateProcess(server, 0);
    WaitForSingleObject(server, 5000);
    std::lock_guard<std::mutex> lock(g_game_mutex);
    if (g_client == client) g_client = nullptr;
    if (g_server == server) g_server = nullptr;
    CloseHandle(client);
    CloseHandle(server);
  }).detach();
  return "{\"ok\":true}";
}

// ---------------------------------------------------------------- HTTP on 127.0.0.1

void reply(SOCKET s, const char* status, const char* type, const std::string& body) {
  std::string head = std::string("HTTP/1.1 ") + status + "\r\nContent-Type: " + type + "\r\nContent-Length: " + std::to_string(body.size()) +
                     "\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n";
  head += body;
  for (size_t sent = 0; sent < head.size();) {
    const int n = send(s, head.data() + sent, static_cast<int>(std::min<size_t>(head.size() - sent, 1 << 20)), 0);
    if (n <= 0) break;
    sent += static_cast<size_t>(n);
  }
}

std::string read_file(const fs::path& p) {
  std::ifstream in(p, std::ios::binary);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

/** A file's media type by its extension. */
const char* media_type(const fs::path& p) {
  std::string e = p.extension().string();
  for (char& c : e) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  static const std::map<std::string, const char*> types = {
      {".html", "text/html; charset=utf-8"}, {".css", "text/css; charset=utf-8"}, {".js", "text/javascript; charset=utf-8"},
      {".json", "application/json"},         {".png", "image/png"},               {".jpg", "image/jpeg"},
      {".jpeg", "image/jpeg"},               {".svg", "image/svg+xml"},           {".webm", "video/webm"},
      {".ogg", "audio/ogg"},                 {".otf", "font/otf"},                {".ttf", "font/ttf"},
      {".woff", "font/woff"},                {".woff2", "font/woff2"},            {".webp", "image/webp"},
      {".gif", "image/gif"},                 {".mp3", "audio/mpeg"},
  };
  auto it = types.find(e);
  return it == types.end() ? "application/octet-stream" : it->second;
}

/** %XX in an address back to its character. */
std::string url_decode(const std::string& in) {
  std::string out;
  for (size_t i = 0; i < in.size(); ++i) {
    if (in[i] == '%' && i + 2 < in.size() && std::isxdigit(static_cast<unsigned char>(in[i + 1])) && std::isxdigit(static_cast<unsigned char>(in[i + 2]))) {
      out.push_back(static_cast<char>(std::stoi(in.substr(i + 1, 2), nullptr, 16)));
      i += 2;
    } else if (in[i] == '+') {
      out.push_back(' ');
    } else {
      out.push_back(in[i]);
    }
  }
  return out;
}

/** The file an address names below `root`, or an empty path: no "..", no drive, nothing outside the root. */
fs::path file_below(const fs::path& root, std::string rel) {
  if (root.empty()) return {};
  if (const size_t q = rel.find_first_of("?#"); q != std::string::npos) rel.resize(q);
  rel = url_decode(rel);
  if (rel.find("..") != std::string::npos || rel.find(':') != std::string::npos || rel.find('\\') != std::string::npos) return {};
  const fs::path p = root / fs::path(rel).relative_path();
  std::error_code ec;
  return fs::is_regular_file(p, ec) ? p : fs::path();
}

/** The value of `key` in a form body ("a=1&b=2"). */
std::string form_value(const std::string& body, const std::string& key) {
  size_t at = 0;
  while (at < body.size()) {
    size_t end = body.find('&', at);
    if (end == std::string::npos) end = body.size();
    const std::string item = body.substr(at, end - at);
    if (item.rfind(key + "=", 0) == 0) return url_decode(item.substr(key.size() + 1));
    at = end + 1;
  }
  return {};
}

void serve(SOCKET s) {
  std::string req;
  char buf[8192];
  size_t header_end = std::string::npos;
  size_t content_length = 0;
  while (true) {
    const int n = recv(s, buf, sizeof buf, 0);
    if (n <= 0) break;
    req.append(buf, static_cast<size_t>(n));
    if (header_end == std::string::npos && (header_end = req.find("\r\n\r\n")) != std::string::npos) {
      const size_t cl = req.find("Content-Length:");
      if (cl != std::string::npos && cl < header_end) content_length = std::strtoul(req.c_str() + cl + 15, nullptr, 10);
    }
    if (header_end != std::string::npos && req.size() >= header_end + 4 + content_length) break;
  }
  if (header_end == std::string::npos) return;
  std::istringstream line(req.substr(0, req.find("\r\n")));
  std::string method, path;
  line >> method >> path;
  if (const size_t q = path.find_first_of("?#"); q != std::string::npos) path.resize(q);  // the page's own parameters
  const std::string body = req.substr(header_end + 4);
  if (method == "GET" && (path == "/" || path == "/index.html")) {
    reply(s, "200 OK", "text/html; charset=utf-8", read_file(g_exe_dir / "lobby_www" / "index.html"));
  } else if (method == "GET" && path == "/lol/champions") {
    std::string json = "[";
    for (const std::string& c : champions()) json += (json.size() > 1 ? "," : "") + std::string("{\"name\":\"") + c + "\"}";
    reply(s, "200 OK", "application/json", json + "]");
  } else if (method == "GET" && path == "/lol/modes") {
    reply(s, "200 OK", "application/json", "[{\"gameMode\":\"PRACTICETOOL\",\"mapId\":11,\"teamSize\":1,\"mutatorId\":1,\"available\":true}]");
  } else if (method == "GET" && path.rfind("/lol/icon/", 0) == 0) {
    const std::string png_bytes = icon_png(path.substr(10));
    if (png_bytes.empty()) reply(s, "404 Not Found", "text/plain", "no icon");
    else reply(s, "200 OK", "image/png", png_bytes);
  } else if (method == "POST" && path == "/lol/start") {
    reply(s, "200 OK", "application/json", start_match(form_value(body, "champion"), form_value(body, "name"),
          form_value(body, "gameMode"), form_value(body, "mapId")));
  } else if (method == "GET" && path.rfind("/fe/", 0) == 0) {
    // /fe/lol-champ-select/images/x.png -> rcp-fe-lol-champ-select/global/default/images/x.png
    const size_t slash = path.find('/', 4);
    const fs::path file = slash == std::string::npos ? fs::path() : file_below(g_lcu / ("rcp-fe-" + path.substr(4, slash - 4)) / "global" / "default", path.substr(slash + 1));
    if (file.empty()) reply(s, "404 Not Found", "text/plain", "not found");
    else reply(s, "200 OK", media_type(file), read_file(file));
  } else if (method == "GET" && path.rfind("/lol-game-data/assets/", 0) == 0) {
    std::string rel = path.substr(22);
    for (char& c : rel) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));  // the archive's names are lower case
    const fs::path file = file_below(g_lcu / "rcp-be-lol-game-data" / "global" / "default", rel);
    if (file.empty()) reply(s, "404 Not Found", "text/plain", "not found");
    else reply(s, "200 OK", media_type(file), read_file(file));
  } else if (method == "GET" && path == "/lol/me") {
    // the player: the name of the Windows account, until the client has accounts of its own
    char user[256] = "Player";
    DWORD n = sizeof user;
    GetUserNameA(user, &n);
    std::string name;
    for (const char* c = user; *c; ++c)
      if (std::isalnum(static_cast<unsigned char>(*c)) || *c == ' ') name.push_back(*c);
    reply(s, "200 OK", "application/json", "{\"name\":\"" + (name.empty() ? std::string("Player") : name) + "\"}");
  } else if (method == "GET" && path == "/lol/status") {
    reply(s, "200 OK", "application/json", std::string("{\"inGame\":") + (in_game() ? "true" : "false") + "}");
  } else if (method == "GET") {
    const fs::path file = file_below(g_exe_dir / "lobby_www", path.substr(1));
    if (file.empty()) reply(s, "404 Not Found", "text/plain", "not found");
    else reply(s, "200 OK", media_type(file), read_file(file));
  } else {
    reply(s, "404 Not Found", "text/plain", "not found");
  }
}

fs::path find_data(const std::string& arg) { return find_game_data(arg, g_exe_dir); }

}  // namespace

int main(int argc, char** argv) {
  wchar_t exe[MAX_PATH];
  GetModuleFileNameW(nullptr, exe, MAX_PATH);
  g_exe_dir = fs::path(exe).parent_path();
  uint16_t port = 21337;
  std::string data_arg;
  bool browser = true;
  for (int i = 1; i + 1 < argc; i += 2) {
    const std::string k = argv[i], v = argv[i + 1];
    if (k == "--port") port = static_cast<uint16_t>(std::stoi(v));
    else if (k == "--data") data_arg = v;
    else if (k == "--no-browser") browser = v != "1";
  }
  g_data = find_data(data_arg);
  // the 14.1 client's files: lcu-data/14.1/plugins next to the exe or in a folder above it (the project's root)
  for (fs::path dir = g_exe_dir; !dir.empty(); dir = dir.parent_path()) {
    std::error_code ec;
    if (fs::is_directory(dir / "lcu-data" / "14.1" / "plugins", ec)) {
      g_lcu = dir / "lcu-data" / "14.1" / "plugins";
      break;
    }
    if (dir == dir.parent_path()) break;
  }

  WSADATA wsa;
  if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return 1;
  SOCKET listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);  // this machine only, like League's client API
  if (bind(listener, reinterpret_cast<sockaddr*>(&addr), sizeof addr) != 0 || listen(listener, 16) != 0) {
    std::fprintf(stderr, "lobby: cannot listen on 127.0.0.1:%u\n", port);
    return 1;
  }
  const std::string url = "http://127.0.0.1:" + std::to_string(port) + "/";
  std::printf("BattleArena lobby on %s (game data: %s)\n", url.c_str(), g_data.string().c_str());
  if (browser) {
    // League's client is a window of its own, 1280 x 720, with a browser inside: the page opens as an application
    // window of the PC's Chromium browser (Edge, which Windows ships; else Chrome), sized so that its content is that
    // big; without one, in the default browser
    const std::string args = "--app=" + url + " --window-size=1296,759 --no-first-run --no-default-browser-check --user-data-dir=\"" + (g_exe_dir / "lobby_profile").string() + "\"";
    HINSTANCE h = ShellExecuteA(nullptr, "open", "msedge.exe", args.c_str(), nullptr, SW_SHOWNORMAL);
    if (reinterpret_cast<INT_PTR>(h) <= 32) h = ShellExecuteA(nullptr, "open", "chrome.exe", args.c_str(), nullptr, SW_SHOWNORMAL);
    if (reinterpret_cast<INT_PTR>(h) <= 32) ShellExecuteA(nullptr, "open", url.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
  }
  for (;;) {
    SOCKET s = accept(listener, nullptr, nullptr);
    if (s == INVALID_SOCKET) continue;
    std::thread([s] {
      serve(s);
      closesocket(s);
    }).detach();
  }
}
