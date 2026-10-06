# Cercetare: cum e construit League of Legends

Ce se știe sigur (publicat de Riot sau verificabil în fișierele jocului) și ce e dedus. Scopul: clientul și serverul
nostru de PC să urmeze aceeași arhitectură din prima, ca să nu refacem nimic mai târziu.

Legendă: **[sigur]** = sursă Riot sau verificat în fișiere; **[comunitate]** = reverse-engineering public;
**[dedus]** = concluzia noastră.

---

## 1. Imaginea de ansamblu

League are trei părți complet separate:

| Parte | Ce face | Tehnologie |
|---|---|---|
| **Clientul din afara meciului** (lobby, alegerea campionului, magazin) | interfață, prieteni, invitații | **web**: Chromium Embedded Framework + Ember.js, cu servicii C++ în spate ([sigur][lcu]) |
| **Clientul de meci** (`League of Legends.exe`) | desenează meciul, trimite comenzi | motor propriu **C++**, DirectX 11 (DX9 doar ca rezervă până de curând) ([sigur][dx11]) |
| **Serverul de meci** | rulează regulile jocului | proces **C++**, câte unul pe fiecare meci, pe mașini din centrele lor ([sigur][det-impl]) |

Clientul din afara meciului vorbește cu serviciile Riot prin REST/WebSocket/RTMP. Clientul de meci vorbește direct cu
serverul de meci, prin UDP ([sigur][lcu]; [comunitate][proto]).

**Pentru noi:** lobby-ul și meniurile pot rămâne web (exact ca la League). Doar meciul devine client nativ.

---

## 2. Serverul de meci

### 2.1 Ritmul (tick-ul) [sigur]
- Serverul simulează în **tick-uri de 0,033 s, adică 30,3 pe secundă** ([wiki tick][tick]). La fiecare tick: comenzile
  jucătorilor, AI, pathfinding, poziții, statistici, damage.
- Totul e **cuantizat pe tick**: un cast de 0,25 s se termină de fapt la tick-ul 8, deci după 0,264 s ([wiki tick][tick]).
- Timpul unui cadru e **măsurat**, nu fix: dacă serverul întârzie, Riot preferă cadre mai rare decât un joc „cu
  încetinitorul” ([sigur][det-clock]).
- Ceasul ține timpul ca **număr întreg de tick-uri** (`QueryPerformanceCounter` pe Windows) și îl convertește în secunde
  doar când e citit. Acumulatoarele float pe 32 de biți produceau derivă ([sigur][det-clock]).

### 2.2 Un singur fir de execuție [sigur]
- Bucla de joc a serverului e construită să ruleze eficient **pe un singur fir**. Celelalte fire nu modifică starea
  jocului fără sincronizare deterministă ([sigur][det-impl]).

### 2.3 Determinism (Project Chronobreak) [sigur]
- Serverul e **determinist**: același set de intrări duce la exact aceeași stare. Așa pot re-rula un meci înregistrat și
  „derula înapoi” un meci de esports ([sigur][det-intro]).
- Fiecare meci e înregistrat ca **SNR** (Server Network Recording): toate comenzile, în ordinea sosirii, plus setările
  de start („Megapacket”) ([sigur][det-impl]).
- Reguli pe care le-au impus:
  - **un singur generator de numere aleatoare** (XOR-shift), cu seed-ul = id-ul unic al meciului;
  - **un singur ceas** (aveau 6 API-uri de timp diferite, unificarea a durat 6 luni);
  - toate câmpurile inițializate explicit;
  - **nicio iterare ordonată după adrese de memorie** (dădea ordine diferită de la o rulare la alta).
- Rejucarea unui meci de 40 de minute durează sub 3 minute, pentru că simularea nu mai e frânată la 30/s
  ([sigur][det-intro]).

### 2.4 Logica abilităților [sigur, din fișiere]
- La început (2009) abilitățile erau **scripturi Lua 5.1** compilate („Building Blocks”). Le vedem încă în wad-ul
  Scripts (`.luabin64`) și le citim deja cu `tools/luabin.py`.
- Acum o mare parte e **date**, în fișierele `.bin`:
  - `SpellObject.mSpell` cu `DataValues` și `mSpellCalculations` (formule: `NamedDataValue`, `StatByCoefficient`,
    `ByCharLevelBreakpoints` …);
  - `BuffData`;
  - `mTargeterDefinitions`;
  - `mMissileSpec` (`FixedSpeedMovement`, `FixedTimeMovement`, `AcceleratingMovement`).
- Logica propriu-zisă e pe server și nu ajunge la client. Clientul primește doar datele de afișare.

### 2.5 Navigația [comunitate]
- Harta e o grilă **`.aimesh_ngrid`**: pe Summoner's Rift are 295 × 296 celule de **50 × 50 unități**. Fiecare celulă are
  flag-uri (zid, tufiș, râu, ce bandă e cea mai apropiată …) ([ngrid][ngrid]).
- Din sezonul 10 există `.ngrid_overlay`: unii dragoni schimbă harta prin overlay-uri peste grilă.
- Grila e deja în proiectul nostru (`art/rift-ngrid`).

### 2.6 Ceața de război [sigur]
- O grilă CPU de **128 × 128**, mărită la 512 × 512 și estompată, apoi aplicată pe scenă și pe minimapă ([sigur][fog]).

---

## 3. Rețeaua

- Transport: **UDP cu ENet** (o bibliotecă de „UDP sigur”, pornită de la versiunea 1.2), cu **7 canale logice**.
  Pachetele sunt criptate cu **Blowfish**, cheie de 16 octeți ([comunitate][proto]; [comunitate][lsb]).
- Pachetele sunt mici: aproximativ **120 de octeți** ([tick]).
- **Mișcarea se transmite ca trasee, nu ca poziții la fiecare tick:** pachetele `WaypointGroup` conțin timpul și lista de
  puncte (x, z) pentru fiecare unitate ([comunitate][waypoints]). Clientul parcurge singur traseul între pachete.
  **[dedus]** De aceea mersul în League e fluid deși serverul trimite doar de 30 de ori pe secundă. Noi trimitem
  poziții la fiecare snapshot, ceea ce explică sacadarea.
- Modul spectator e alt protocol: HTTP, pe bucăți de 30 de secunde plus „keyframes” ([comunitate][proto]).
- Porturi: 5000–5500 UDP pentru meci ([comunitate][proto]).

---

## 4. Clientul de meci (motorul grafic)

### 4.1 Cadrul, pe etape [sigur]
Ordinea în care League desenează un cadru ([sigur][pipeline]):

| # | Etapă | Cum |
|---|---|---|
| 0 | Ceața de război | grilă 128² → textură 512² estompată |
| 1 | Umbre | shadow map-uri (adâncimea în RGB), estompate pentru margini moi |
| 2 | Geometria statică (harta) | **lumina și umbrele hărții sunt deja „coapte” în texturi** |
| 3 | Mesh-uri animate (personaje) | 1–4 oase pe vârf; Fresnel, emisiv, ceața modulează culoarea; scriu și adâncimea pentru contur |
| 4 | Contur („inking”) | filtru Sobel pe adâncime (rezervă: stencil) |
| 5 | Iarba | mesh-uri animate care se leagănă |
| 6 | Apa | mesh-uri semitransparente cu valuri animate |
| 7 | Decaluri | plane texturate peste teren |
| 8 | Contururi speciale | mai groase și estompate (hover, selecție) |
| 9 | Particule | fiecare abilitate, buff sau efect e un sistem de particule |
| 10 | Post-procesare | FXAA, apoi corecție gamma (plus desaturarea la moarte) |
| 11 | Bare de viață și damage | |
| 12 | HUD | ~1000 de triunghiuri |

Cifre pentru o scenă: ~**200.000 de triunghiuri, din care 90.000 sunt particule**, **695 de draw call-uri** și
**28 de milioane de pixeli** desenați ([sigur][pipeline]).
**[dedus]** Particulele sunt cel mai mare consumator, la fel ca la noi.

### 4.2 API grafic [sigur]
- DX11 începând cu patch-ul 10.16. Din 25.02, cerința minimă e **DirectX 11 feature level 11_0** pe Windows și Metal pe
  Mac ([sigur][dx11]).
- Placa ta UHD 620 suportă DX11, DX12 și Vulkan, deci e în cerințele oficiale.

### 4.3 Formatele de fișiere [sigur, le citim deja]

| Format | Ce conține | Cine îl citește (open source) |
|---|---|---|
| `.wad.client` | arhive, fișierele identificate prin hash xxh64 al căii | `ltk_wad` (Rust), `tools/lolcdn.py` |
| `.bin` (PROP/PTCH) | toate datele: personaje, abilități, efecte VFX, materiale, hartă (sistem de proprietăți cu reflecție, câmpuri identificate prin hash FNV1a) | `ltk_meta` (Rust), CommunityDragon |
| `.tex` / `.dds` | texturi **deja comprimate pentru placa video** (BC1/BC3/BC7) | `ltk_texture` (Rust) |
| `.skn` / `.skl` / `.anm` | mesh animat, schelet, animații (inclusiv comprimate) | `ltk_mesh`, `ltk_anim` (Rust), `tools/lolchar.py` |
| `.scb` / `.sco` | mesh-uri statice (particule) | `ltk_mesh` |
| `.mapgeo` | geometria hărții, cu lumină coaptă | `ltk_mapgeo`, `tools/mapgeo.py` |
| `.aimesh_ngrid` | grila de navigație | convertoare din comunitate |
| `.luabin64`, `.preload` | scripturi Lua 5.1 compilate | `tools/luabin.py` |
| `.troybin`, `.inibin` | particule și date în format vechi (2009–2017) | `tools/troybin.py` |
| `.stringtable` | textele traduse | `ltk_rst` |

Biblioteca **League Toolkit** (Rust, licență Apache-2.0) citește toate formatele moderne și e considerată matură
([ltk][ltk]). Asta e motivul principal pentru care clientul nostru nativ ar trebui scris în Rust.

### 4.4 Istoricul (de unde s-a plecat)
- 2009: motor propriu C++, **DirectX 9**, scripturi **Lua**, interfață Flash/ActionScript, arhive **RAF**, date
  `.inibin`, particule `.troybin` ([sigur][dx11]; [comunitate][lsb]).
- Evoluție: RAF → **WAD**; `.inibin` → **`.bin`** (proprietăți cu reflecție); `.troybin` → **`VfxSystemDefinitionData`**
  în `.bin` (Riot a convertit singur efectele vechi; vezi `shared.cdtb.bin.json`); Flash → interfață nativă în meci și
  CEF în afara lui; DX9 → **DX11**.
- Versiunea 4.20 (2014) a fost ultima fără criptare serioasă a pachetelor. Pe ea s-au construit emulatoarele publice de
  server (LeagueSandbox în C#, IntWars, LeagueEmulatorJS) ([comunitate][lsb]; [comunitate][lejs]).

---

## 5. Partea legală (important)

- LeagueSandbox (emulatorul de server pentru 4.20) a fost **arhivat în 2022 după o somație de încetare (cease-and-desist)
  din partea Riot** ([comunitate][lsb]).
- **Concluzie:** nu descărcăm, nu rulăm și nu emulăm clientul Riot (nici pe cel vechi, 4.20). Construim **clientul și
  serverul nostru**, care doar **citesc formatele de date** League.
- Cea mai curată variantă pe termen lung: clientul citește fișierele **din League-ul instalat al fiecărui jucător**, în
  loc să distribuim noi fișierele Riot. Pentru joc privat între prieteni riscul e mic, dar proiectul nu trebuie publicat
  cu fișierele Riot incluse.

---

## Surse

- [lcu]: https://www.riotgames.com/en/news/architecture-league-client-update — The Architecture of the League Client Update (Riot)
- [det-intro]: https://www.riotgames.com/en/news/determinism-league-legends-introduction — Determinism in LoL: Introduction (Riot)
- [det-impl]: https://www.riotgames.com/en/news/determinism-league-legends-implementation — Determinism in LoL: Implementation (Riot)
- [det-clock]: https://www.riotgames.com/en/news/determinism-league-legends-unified-clock — Determinism in LoL: Unified Clock (Riot)
- [pipeline]: https://www.gamedeveloper.com/programming/a-layer-by-layer-breakdown-of-i-league-of-legends-i-rendering-process — A Trip Down the LoL Graphics Pipeline (Riot, republicat)
- [fog]: https://www.riotgames.com/en/news/story-fog-and-war — A Story of Fog and War (Riot)
- [dx11]: https://www.leagueoflegends.com/en-us/news/game-updates/help-us-beta-test-dx11-support-for-league/ — DX11 în League (Riot); cerințe minime: https://support-leagueoflegends.riotgames.com/hc/en-us/articles/201752654
- [tick]: https://wiki.leagueoflegends.com/en-us/Tick_and_updates — Tick and updates (LoL Wiki)
- [proto]: https://nelsonslog.wordpress.com/2015/08/11/libenet-league-of-legends-protocol-success/ și https://nelsonslog.wordpress.com/2014/08/07/league-of-legends-game-protocol/
- [lsb]: https://github.com/LeagueSandbox/GameServer — LeagueSandbox GameServer (arhivat, AGPL-3.0)
- [lejs]: https://github.com/Karmel0x/LeagueEmulatorJS
- [waypoints]: https://huggingface.co/datasets/maknee/league-of-legends-decoded-replay-packets — pachete de replay decodate (WaypointGroup)
- [ngrid]: https://github.com/FrankTheBoxMonster/LoL-NGRID-converter și https://lolmodding.fandom.com/wiki/Ai_Mesh_Nav_Grid_File
- [ltk]: https://github.com/LeagueToolkit/league-toolkit — League Toolkit (Rust, Apache-2.0)
- https://github.com/CommunityDragon/Docs — documentația formatelor (CommunityDragon)
- https://github.com/LeagueToolkit/awesome-league — lista de unelte din comunitate

[lcu]: https://www.riotgames.com/en/news/architecture-league-client-update
[det-intro]: https://www.riotgames.com/en/news/determinism-league-legends-introduction
[det-impl]: https://www.riotgames.com/en/news/determinism-league-legends-implementation
[det-clock]: https://www.riotgames.com/en/news/determinism-league-legends-unified-clock
[pipeline]: https://www.gamedeveloper.com/programming/a-layer-by-layer-breakdown-of-i-league-of-legends-i-rendering-process
[fog]: https://www.riotgames.com/en/news/story-fog-and-war
[dx11]: https://www.leagueoflegends.com/en-us/news/game-updates/help-us-beta-test-dx11-support-for-league/
[tick]: https://wiki.leagueoflegends.com/en-us/Tick_and_updates
[proto]: https://nelsonslog.wordpress.com/2015/08/11/libenet-league-of-legends-protocol-success/
[lsb]: https://github.com/LeagueSandbox/GameServer
[lejs]: https://github.com/Karmel0x/LeagueEmulatorJS
[waypoints]: https://huggingface.co/datasets/maknee/league-of-legends-decoded-replay-packets
[ngrid]: https://github.com/FrankTheBoxMonster/LoL-NGRID-converter
[ltk]: https://github.com/LeagueToolkit/league-toolkit
