# Arhitectura BattleArena PC

**Prioritatea 1 e fidelitatea față de referință:** aceleași limbaje, aceeași tehnologie și aceeași împărțire în procese ca
League (vezi `CERCETARE.md`). Unde se știe cum face League, facem la fel. Unde nu se știe, alegem varianta cea mai
apropiată de ce se știe. Multiplayer-ul prin internet vine **după** ce versiunea locală e fidelă.

---

## 1. Limbaje și tehnologii, față de League

| Piesa | League | Noi |
|---|---|---|
| Motorul clientului de meci | **C++**, motor propriu | **C++ (C++20)**, motor propriu |
| API-ul grafic | **DirectX 11** (minim feature level 11_0) | **DirectX 11**, feature level 11_0 (UHD 620 îl suportă) |
| Shaderele | **HLSL** | **HLSL** (compilate cu `fxc`/`dxc` din Windows SDK) |
| Serverul de meci | **C++**, un proces pe meci, un singur fir | **C++**, proces separat, un singur fir |
| Rețeaua | **ENet** (UDP fiabil), 7 canale | **ENet** (aceeași bibliotecă C), 7 canale |
| Scripturile abilităților | **Lua 5.1** (Building Blocks, scripturile `.luabin` de pe server); acum și date în `.bin` + C++ | **Lua 5.1** pentru scripturile de abilități și buff-uri + date din `.bin` + nucleu C++ |
| Datele | `.wad`, `.bin`, `.tex`, `.skn`, `.skl`, `.anm`, `.mapgeo`, `.aimesh_ngrid` | **aceleași fișiere, citite direct** de parserele noastre C++ |
| Clientul din afara meciului | **web** (CEF + Ember) | **web**: lobby-ul și alegerea campionului din BattleArena |
| Construcția | (internă) | CMake + MSVC (Visual Studio Build Tools) |

Parserele de formate sunt scrise de noi în C++. Pornim de la cele pe care le avem deja în Python și care funcționează
(`tools/lolcdn.py` pentru wad, `lolchar.py` pentru skn/skl/anm, `mapgeo.py`, `troybin.py`, `luabin.py`), cu
documentația CommunityDragon și League Toolkit ca referință de verificare.

---

## 2. Procesele (local, de la început)

```
lobby (web, din BattleArena)  --pornește-->  server.exe (meciul)  <--ENet/UDP localhost-->  client.exe (meciul)
```

- Și când joci singur, **serverul e un proces separat** de client, ca la League: clientul nu conține reguli de joc, doar
  desenează și trimite comenzi.
- Lobby-ul pornește serverul cu setările meciului (echivalentul „Megapacket”: harta, campionii, roboții, seed-ul) și apoi
  clientul, cu adresa, portul și cheia de conectare. League lansează la fel `League of Legends.exe` din client.
- La început totul rulează pe `127.0.0.1`. Multiplayer-ul prin internet e o etapă separată, mai târziu.

---

## 3. Serverul de meci

- **Un singur fir pentru simulare.** Rețeaua (ENet) poate avea firul ei, dar nu atinge starea jocului.
- **Tick-uri de 0,033 s (30,3/s).** Toate duratele sunt cuantizate pe tick (un cast de 0,25 s se termină la tick-ul 8).
- **Ceasul e un număr întreg de tick-uri** (`QueryPerformanceCounter`); secundele se calculează doar la citire.
- **Determinist din prima:**
  - un singur RNG (XOR-shift), cu seed-ul = id-ul meciului;
  - containere cu ordine stabilă (nicio ordonare după adrese de memorie);
  - toate câmpurile inițializate explicit (inițializare inline, stil C++11).
- **Înregistrare de tip SNR:** setările de start și toate comenzile, cu tick-ul sosirii. Din ea vin reluările și testele
  de tip Delta Checker (rulezi o înregistrare și verifici starea finală).
- **Datele din `.bin`:** `DataValues` și `mSpellCalculations` (formulele League), `BuffData`, `mMissileSpec`.
  Comportamentul abilităților e în **scripturi Lua 5.1**, ca Building Blocks la League, cu funcții expuse din C++
  (damage, buff, dash, missile, efecte). Kit-urile din BattleArena (TypeScript) sunt referința de portat.
- **Navigația** pe grila `.aimesh_ngrid` (295 × 296 celule de 50 × 50), cu A* și netezire.
- **Ceața de război** pe server, pe o grilă de 128 × 128 per echipă. Unitățile nevăzute nu se trimit clientului.

## 4. Rețeaua (ENet)

- ENet, **7 canale**, ca la League. Repartizarea pe canale (ce trimite League pe fiecare nu e documentat public; e
  deducția noastră):
  - 0: conectare și handshake;
  - 1: comenzile jucătorului (fiabile, ordonate);
  - 2: mișcare (`WaypointGroup`: trasee);
  - 3: evenimente de luptă (cast-uri, damage, buff-uri, efecte);
  - 4: replicarea statisticilor (delta);
  - 5: chat și anunțuri;
  - 6: rezervat.
- **Mișcarea ca trasee:** serverul trimite „unitatea X merge pe P1…Pn cu viteza V, de la tick-ul T”, iar clientul o
  parcurge singur, fluid.
- **Pachete binare compacte**, definite o singură dată și folosite de ambele procese. League ajunge la ~120 de octeți pe
  pachet.
- Criptarea (Blowfish la League) se poate adăuga la final. Nu schimbă arhitectura.

## 5. Clientul de meci

### 5.1 Datele
- Citește direct **`.wad.client`**:
  1. din League-ul instalat al jucătorului, dacă există;
  2. altfel, din fișierele descărcate de pe CDN-ul Riot prin manifest.
- Texturile `.tex` (BC1/BC3/BC7) merg **direct în placa video**, fără decomprimare.

### 5.2 Desenarea: etapele League, în ordine

| # | Etapă | Cum |
|---|---|---|
| 0 | Ceața de război | grila de 128² de la server → textură 512² estompată |
| 1 | Umbre | shadow map pentru personaje (umbrele hărții sunt coapte) |
| 2 | Harta | `.mapgeo`, cu lumina coaptă din textură |
| 3 | Personaje | `.skn` + `.skl` + `.anm`, skinning pe GPU (1–4 oase pe vârf), Fresnel și emisiv din materialul din `.bin`; scriu și adâncimea pentru contur |
| 4 | Contur | Sobel pe adâncime |
| 5–7 | Iarbă, apă, decaluri | din `.mapgeo` și materialele hărții |
| 8 | Contururi speciale | hover și selecție, groase și estompate |
| 9 | Particule | `VfxSystemDefinitionData` din `.bin`, cu semantica validată în BattleArena (flex, linger, lookup, beam, overlay …) |
| 10 | Post | FXAA + gamma |
| 11 | Bare de viață și damage | |
| 12 | HUD | din atlasele reale |

### 5.3 Bucla clientului
- Desenează independent de tick-ul serverului (cu limită de FPS), iar unitățile își parcurg traseele local.
- Comenzile pleacă imediat; serverul are ultimul cuvânt.

## 6. Ce refolosim din BattleArena
- **Regulile descoperite:** VFX, spațiul League (coordonate, oglindire), targeterii, iconițele, valorile din date.
- **Uneltele Python** de extragere, ca referință pentru parserele C++ și ca verificare (aceleași rezultate).
- **Logica jocului** (`src/game`) ca referință pentru scripturile Lua și pentru nucleul C++, plus suitele `verify:*` ca
  teste de paritate.
- **Lobby-ul și alegerea campionului** (web).
