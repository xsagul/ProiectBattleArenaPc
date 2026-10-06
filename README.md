# ProiectBattleArenaPc

Versiunea de PC a BattleArena: un client nativ și un server nativ, construite după arhitectura League of Legends.

- `docs/CERCETARE.md`: cum e construit League (client, server, rețea, desenare, formate), cu surse.
- `docs/ARHITECTURA.md`: arhitectura noastră, piesă cu piesă față de League (C++, DirectX 11, HLSL, ENet, Lua 5.1).
- `docs/PLAN.md`: fazele, de la uneltele de lucru până la multiplayer.

## Cum joci

1. Dublu-click pe **`Joaca BattleArena.cmd`** (în folderul proiectului). Se deschide lobby-ul în browser.
2. Alegi campionul (Garen, Lux, Ashe, Tryndamere, Zed) și apeși **Start**. Pornesc serverul și fereastra jocului
   (harta se încarcă în aproximativ 15 secunde).
3. În joc: **click dreapta** = mergi, sau atacă inamicul de sub cursor (minion, turn, inhibitor, nexus); **T** = pune
   păpușa de antrenament din Practice Tool la cursor; **rotița** = zoom; **Y** = camera legată de campion / liberă;
   **săgețile** = mută camera. **Q, W, E, R** = abilitățile, aruncate spre cursor (pe inamicul de sub cursor, la cele
   cu țintă); **Ctrl+Q / W / E / R** sau click pe săgeata de deasupra iconiței = pui un punct în abilitate când crești
   în nivel. Închizi fereastra jocului ca să ieși din meci; fereastra neagră a lobby-ului o închizi ca să oprești tot.

Ce există acum: harta (patch 14.1, cu shader-ele Riot), clădirile, efectele hărții, campionii cu animațiile lor, mersul
pe trasee, atacul de bază și păpușa de antrenament; **valurile de minioni pe cele trei benzi** (primul la 13 secunde
după ce intri), **turnurile care trag**, clădirile care se strică și cad în ordinea din joc, inhibitorii care reapar,
super-minionii, moartea și reapariția campionului la fântână, vindecarea la fântână și sfârșitul meciului la căderea
nexusului. **Interfața** e desenată din datele clientului 14.1: barele de viață de deasupra unităților, rama
jucătorului (portret, nivel, viață, mană, experiență, iconițele abilităților), statisticile, aurul, antetul cu scorul și
timpul, minimapa. Campionul **crește în nivel** din experiența minionilor și strânge **aur**.
**Abilitățile** (pasiva și Q, W, E, R) ale celor cinci campioni sunt scripturi Lua 5.1 în `server/scripts/`, cu cifrele
citite din datele 14.1 ale fiecărei vrăji și cu efectele vizuale ale jocului.
Nu sunt încă făcute: magazinul și obiectele, tabela de scor, efectele vechi `.troy` (proiectilele
minionilor) și monștrii din junglă. Fiecare meci se înregistrează în `build-clang/bin/last_match.basr`
(`server.exe --replay last_match.basr --combat-log 1` îl reia și listează loviturile).

Verificări fără ecran: `server.exe --simulate 1500` rulează 25 de minute de meci cât de repede poate și arată starea
benzilor la fiecare 30 de secunde; `--structure-health 0.05` face clădirile slabe, ca să se vadă tot drumul până la nexus.

## Structura

| Folder | Ce conține |
|---|---|
| `common/` | ce folosesc ambele procese: arhivele `.wad.client`, fișierele `.bin`, hash-urile League, protocolul ENet, timpul în tick-uri și generatorul aleator determinist |
| `server/` | `server.exe`: un meci, un singur fir, 30,3 tick-uri pe secundă, cu înregistrarea comenzilor |
| `client/` | `client.exe`: fereastra DirectX 11, conectarea la server, comenzile jucătorului |
| `lobby/` | `lobby.exe`: lobby-ul (ca LCU: serviciu local HTTP + pagină web), pornește serverul și clientul |
| `tools/` | `bainfo` (fișierele League prin parserele C++), `fetch_wads.py` (arhivele de pe CDN-ul Riot) |
| `third_party/` | ENet 1.3.18, Lua 5.1.5, zstd 1.5.6, xxHash 0.8.2, din sursele oficiale, cu sumele de control verificate |
| `game-data/` | arhivele League, în aceeași structură ca o instalare (`DATA/FINAL/...`); nu intră în git |

## Build

Ai nevoie de Visual Studio 2022 Build Tools (C++) și CMake.

```
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
```

## Rulare (local, ca la League: serverul și clientul sunt procese separate)

```
build\bin\Release\server.exe --match 1
build\bin\Release\client.exe --name Sorin
```

## Datele League

```
python tools/fetch_wads.py Champions/Garen.wad.client DATA.wad.client Scripts.wad.client
build\bin\Release\bainfo.exe bin game-data\DATA\FINAL\Champions\Garen.wad.client data/characters/garen/garen.bin GarenQ ..\BattleArena\art\lol-data
```

Notă legală: proiectul nu conține și nu rulează clientul Riot. Doar citește formatele de date League, iar fișierele Riot
(`game-data/`) nu se distribuie împreună cu proiectul.
