# Planul pe faze

Ordinea: **fidelitatea de arhitectură și limbaj întâi, local**. Multiplayer-ul prin internet vine la final.

## Faza 0: uneltele
- **Visual Studio 2022 Build Tools** (compilatorul MSVC + Windows SDK, care include DirectX 11 și compilatorul HLSL),
  **CMake**. Se instalează cu `winget`, cu acordul tău.
- Bibliotecile (sursă deschisă, incluse în proiect): **ENet**, **Lua 5.1**, **zstd** (WAD-urile sunt comprimate cu
  zstd), **xxHash** (căile din WAD sunt hash-uri xxh64).
- Scheletul: `client/`, `server/`, `common/` (protocolul, formatele, matematica), `data/` (parserele), CMake.

## Faza 1: datele și primul cadru
- Parserele C++: WAD → BIN, TEX, SKN, SKL, ANM, MAPGEO. Fiecare verificat față de uneltele Python existente.
- Fereastră DirectX 11, camera ca în League, harta cu texturile BC urcate direct, Garen animat.
- **Măsurăm FPS-ul pe UHD 620**, comparat cu browserul.

## Faza 2: serverul și conexiunea locală
- `server.exe`: tick de 30,3/s, un singur fir, ceas întreg, RNG XOR-shift cu seed (determinist).
- Navigația pe `.aimesh_ngrid`, mișcare cu trasee.
- ENet pe `127.0.0.1`, 7 canale, pachete binare.
- `client.exe` conectat: campionul se mișcă fluid, pe trasee.
- Înregistrarea de tip SNR și testul de reluare (aceeași stare finală la fiecare rulare).

## Faza 3: lupta și datele
- Statistici, atacuri, minioni, turnuri, monștri, din `.bin`.
- Scripturile Lua pentru abilitățile celor 5 campioni și pentru buff-uri, cu formulele din `mSpellCalculations`.
- Itemele. Testele de paritate (portarea suitelor `verify:*`).

## Faza 4: imaginea completă
- Particulele (VFX), ceața de război, conturul Sobel, iarba, apa, decalurile, FXAA.
- HUD-ul, targeterii, target frame-ul, tabela de scor, din atlasele reale.

## Faza 5: lobby-ul și lansarea
- Lobby-ul web pornește `server.exe` cu setările meciului, apoi `client.exe`, cu adresa și cheia (ca la League).
- Reluările meciurilor, din înregistrări.

## Faza 6: multiplayer prin internet
- Abia aici: cum găzduiește League meciurile (servere dedicate) și ce variantă alegem pentru tine și Naim.

---

Versiunea web din `Desktop/BattleArena` rămâne jucabilă până când versiunea de PC o ajunge din urmă.
