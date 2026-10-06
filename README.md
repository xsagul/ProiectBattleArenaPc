# ProiectBattleArenaPc

League of Legends 13.3, jucat cu clientul original al lui Riot (exe-ul 13.3 despachetat) conectat la **serverul nostru**,
pornit dintr-o interfață de lobby refăcută din fișierele clientului de lobby 13.3.

Din 6 octombrie 2026, clientul nativ C++ (14.1 / 12.23) e abandonat în favoarea exe-ului Riot; sursa lui rămâne doar în
istoricul git (commit `5a1669c`). Replay-ul 13.3 e doar referință pentru măsurători; meciul îl simulează serverul nostru.

## Cum joci

Dublu-click pe **`Joaca 13.3 (client).cmd`**. Se deschide lobby-ul în browser: PLAY → Summoner's Rift → Confirm →
Find Match → Accept → alegi campionul → Lock In. Pornesc serverul și jocul; când închizi jocul, revii în lobby.

## Structura

| Folder | Ce conține |
|---|---|
| `game/` | clientul Riot 13.3: `League of Legends.unpacked.exe` (fără packer), `ba_host.dll` (gazda noastră pentru exe), `d3d11.dll` (capturi de ecran), `DATA/` |
| `client-src/` | clientul ca sursă brută: imaginile din memorie ale exe-ului (`exe_image_*.bin`, baza 0x580000), harta funcțiilor, tabelele de handlere și importuri, `ba_host.c` și scripturile care construiesc exe-ul despachetat |
| `server/` | serverul de joc: `lnp_server.py` (transportul, pachetele, logica), `world.py` (minionii), `items133.py`, motorul de vrăji, codecurile de pachete |
| `launcher/` | interfața 13.3 (`www/`) și serverul ei local (`lobby_server.py`), care pornește meciul |
| `tools/` | uneltele de învățat și de verificat: formatele pachetelor, harta exe-ului, `disx.py` (dezasamblare), testele de meci (`run_match.sh`, `match_shots.sh`, `game_input.ps1`), `bin/` (`bainfo`, `luac`, `unluac`), `gpu_sponge/`, `third_party/` |
| `data/` | ce citesc serverul și uneltele: `exe133/` (formatele pachetelor învățate, tabele măsurate, culoarele, meciurile de test), `lua133/` (scripturile Riot), `lcu133/` + `lcu/13.3/` (lobby-ul 13.3), `hashes/`, `rofl/` (replay-ul 13.3), `replays/maknee13_2/` (pachete decodate din meciuri reale 13.2) |
| `docs/` | jurnalul de lucru și concluziile (`MIGRARE_12.23.md`) |
| `toolchain/` | `llvm-mingw` (pentru `ba_host.dll`), Java (pentru `unluac`), procmon |

## Teste

```
bash tools/run_match.sh 90 nume python server/lnp_server.py --replay-574 --own-574 --set574 "1.champion=Jinx;1.champion_id=222;1.skin=0" --slot 1 --hero 4000001e --own-79 --set79 "1.champion=Jinx;1.skin=0" --start-only --shots-game "73" --stream data/rofl/KR-6363178603_13.3.rofl
```
Pornește serverul și jocul pentru 90 de secunde; jurnalele ajung în `data/exe133/match_nume/`, capturile (la secundele
de joc din `--shots-game`) în `game/sponge/`.

Notă: fișierele Riot (`game/`, `data/lcu/`) nu se distribuie împreună cu proiectul.
