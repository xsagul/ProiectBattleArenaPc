# Migrarea la patch-ul 12.23

Decizia utilizatorului (2026-10-03): tot jocul trece de pe 14.1 pe **12.23.4835208** (`Desktop\lol12.23`). Harta,
structurile, minionii, monștrii, campionii, abilitățile și efectele vin din 12.23, iar logica și arhitectura sunt ale
lui 12.23, citite nativ — fără straturi care „traduc” forme de 14.1. La final nu rămâne nimic din 14.1.

## Ce are 12.23 și 14.1 nu avea

| Ce | Unde (12.23) | Ce înseamnă |
|---|---|---|
| Scriptul de nivel al serverului Riot | `Scripts.wad`: `levels/map11/scripts/levelscript.luabin64` → `data/shared/scripts/globallevelscript`, `sr_levelscript` | valuri, upgrade-uri, turnuri, inhibitori, nexus, bonusuri de bază — logica reală, nu deducție |
| Spawn-ul junglei | `data/shared/scripts/sr_neutralminionspawn` | tabere, timpi, dragoni, Baron, Herald |
| AI-ul unităților | `data/scripts/*.luabin64` (minion, turret, hero, aggro, leashed, baronminionai, rivercrab ...) | cum aleg ținta minionii, turnurile, monștrii |
| Replay-uri cu pachetele serverului | HF `maknee/league-of-legends-decoded-replay-packets`, folder `12_23` (768 loturi, 62 GB) | ce a trimis serverul Riot real: spawn-uri, daune, replicare de statistici, mișcări |

Abilitățile campionilor rămân stub-uri și în 12.23 (fișiere de ~300 octeți, doar flag-uri) — logica lor a fost doar pe
server. Pentru ele: datele spell-urilor 12.23 + Wiki la data patch-ului 12.23 (live 2022-12-07 .. 2023-01-10) +
verificare pe replay (`CastSpellAns`, `UnitApplyDamage`).

Unelte: `tools/bin/unluac.jar` (cu JRE-ul portabil din `toolchain/jdk-*-jre`) decompilează orice `.luabin`;
listele/sursele sunt în `data/lua1223/src/` (153 de scripturi). `tools/bin/luac51_x86.exe -l -l` dă listarea.

## Diferențe de format găsite

- **Navgrid:** numit de `map11.bin` MapSkin `mNavigationMesh` ("AIPath_SRX_2.aimesh_ngrid"), fișierul e în
  `Map11LEVELS.wad` la `levels/map11/`. Versiunea 7, la fel. — **făcut**
- **Mapgeo v13:** fără controller de vizibilitate, fără render flags, trei canale de textură. Tufișurile nu mai sunt în
  mapgeo: sunt personaje `brush_sru_a..h` plasate ca `GdsMapObject` „Level Props” (cu animații). — **cititorul făcut**;
  tufișurile ca personaje: de făcut
- **Structuri:** nu există `BarracksLevelController` / `SpawnAiTurret` în bin-uri. Le face motorul + scriptul de
  nivel: obiectele hărții (`Turret_T1_C_05`, `Barracks_T1_L1`, `HQ_T1`) + `objectcfg_srx.cfg` (viață, regen, rază,
  skin, rubble-ul turnului) + record-urile `Characters/Turret/CharacterRecords/SR_Outer | SR_Inner | SR_Inhibitor`.

## Pașii

1. Datele se încarcă (navgrid, mapgeo v13, shaderele 12.23) — **făcut**, harta se vede.
2. Gazda de level-script în server (`server/src/MatchLevel.cpp`) — **făcut**: Lua rulează scriptul Riot ales de
   mutatorul `LevelScriptFile` (CLASSIC pe harta 11: `LevelScript_SRX.lua`), motorul oferă API-ul (`GetTurret`,
   `GetDampener`, `GetHQ`, `SetInvulnerable`, `SetTargetable`, `SetNotTargetableToTeam`, `InitTimer`,
   `CreateChildTurret`, `SetDisableMinionSpawn` ...) și cheamă `OnLevelInit`, `OnPostLevelLoad`, `OnLevelInitServer`,
   `OnGameStartup`, `GetInitSpawnInfo`, `GetMinionSpawnInfo`, `HandleDestroyedObject`, `BarrackReactiveEvent` și
   timerele după nume. **Turnurile le creează scriptul** (`CreateLevelProps.lua`: `SpawnTurret(obiect, personaj,
   record, echipă, poziție, bandă)`), motorul pune doar inhibitorii și nexusurile. Parametrii de mutator vin din
   Global.wad (`GameMutatorExpansions` "Default" + "CLASSIC", intrarea `{d109e1824a0373d3}`). Funcțiile de motor încă
   lipsă se scriu o dată în log: `level script: missing engine function X`.
3. AI-ul unităților din `data/scripts/*.luabin64` (minion, turret) cu API-ul lor.
4. Jungla din `sr_neutralminionspawn`.
5. Campionii și abilitățile pe datele 12.23; comportamentul re-verificat pe Wiki la 12.23 și pe replay.
6. Efecte: particulele 12.23 (VfxSystemDefinitionData + troybin), tufișurile ca personaje.
7. Interfața (HUD, magazin, ecran de încărcare) din UI-ul 12.23.
8. Comparatorul cu replay-ul: pentru fiecare regulă, rulăm meciul nostru și îl punem lângă pachetele reale
   (timpi de spawn, daune, viteze).
9. Curățenie: niciun fișier, comentariu sau ramură de cod care să mai țină de 14.1.

## Stare la 2026-10-03

- harta, structurile, minionii (primul val la 65 s, melee 477 HP la naștere = scriptul) rulează pe 12.23;
- `NeutralMinionInit` (jungla) încă cade: lipsesc `CreateNeutralCamp` & co. → pasul 4; din cauza asta `OnLevelInit`
  nu ajunge să încarce `EndOfGame.lua`;
- regulile turnurilor din `Match::attack_damage` (plăci, Warming Up, Fortification, cote fixe pe minioni) și itemele
  hardcodate (ex. Cryptbloom 3118) sunt încă cele din 14.1 → de refăcut pe 12.23 (pasul 5);
- clientul încă deduce turnurile exterioare (plăcile din bara de viață) din navgrid, nu de la server.

## Verificat deja pe replay (lotul 12_23/batch_001, primul meci)

- primul val la 65,0 s, minionii la ~0,83 s unul după altul, valuri la 30 s (scriptul: `INITIAL_TIME_TO_SPAWN = 65`,
  `WaveSpawnRate = 30000`, `SingleMinionSpawnDelay = 800`);
- turnurile exterioare pornesc cu 5000 HP (`SR_Outer` baseHP 5000).

## Buretele 1: comparatorul cu pachetele reale (`tools/replay_facts.py`)

Din `data/replays1223/batch_001.jsonl.gz`, meciul 0 (23 852 lovituri `UnitApplyDamage`, 1062 minioni):

- daunele casterului = record (23) + **partea întreagă** a `DamageBonus` din scriptul de nivel: valul 1 → 24
  (nu 24,5), valurile 4–6 → 26, 7–9 → 27, 10–12 → 29, 13–15 → 30, 16+ → 35 (cu `DamageUpgradeLate`). Potrivire 1,000
  pe toate loviturile minion→minion până la 210 s. Serverul nostru nu rotunjește încă → de corectat.
- după 210 s (`mvm_StartTime`) apare sistemul minion-vs-minion al lui 12.23 (constantele CLASSIC: `mvm_PercentDamage
  ToOtherMinionsBase` 0,05, `...ByTowerAdvantage` 0,05, `mvm_LevelDiffCap` 3, `mvm_FlatDRFromOtherMinionsBase` 1,
  `mvm_UpdateInterval` 1, `mvm_MaxLifetime` 600): loviturile primesc −1 fix (raporturi 26/27, 28/29, 34/35) și un bonus
  în trepte de 1% (×1,01 … ×1,04). Regula exactă a treptelor: de dedus din loviturile pe minut și avantajul de turnuri.
- valori foarte mari pe minioni (1480, 2385, 4560) = alt mecanism (execuție / ucidere instant) — de identificat.

## Căutarea unui `.rofl` 12.23 (2026-10-03)

Negăsit public. Verificate: depozite GitHub cu fișiere `.rofl` (versiuni găsite: 9.23, 10.2, 10.4, 10.14, 12.3, 12.7,
13.3, 14.7, 14.11, 15.1, 15.20), issue-uri GitHub ale uneltelor de replay (dec. 2022 – feb. 2023), archive.org,
replays.xyz (secțiunea pro e goală), seturile HF ale lui maknee (cel „brut” se oprește la 12.22, și acolo doar JSON).
Uneltele pentru buretele 2 sunt în `toolchain/procmon` (Process Monitor, cere administrator pentru driver) și
`toolchain/RenderDoc_1.46_64` (portabil).

## Buretele 2: clientul Riot rulând un replay (2026-10-03)

- Clientul 13.3 (`ProiectBattleArenaPc\game`, build 13.3.491.0366) rulează replay-ul `data/rofl/KR-6363178603_13.3.rofl`
  offline: `"League of Legends.exe" "<rofl>" "-GameBaseDir=<joc>" -SkipRads -SkipBuild -EnableLNP "-UseDX11=1:1"
  -Locale=en_US`. Fără `-UseDX11=1:1` pornește pe DX9. `Config/game.cfg` [General] `EnableReplayApi=1` deschide
  Replay API pe https://127.0.0.1:2999 (`/replay/playback` sărit în timp/viteză, `/replay/render` camera,
  `/replay/particles`, `/replay/recording`). 12.23 cu un replay 12.3 rămâne la ecran negru (versiune).
- Clientul e pe 32 de biți și protejat (`stub.dll`): RenderDoc nu se poate atașa (IAT read-only) și e omorât dacă e
  încărcat din interior.
- **Buretele GPU propriu** (`tools/gpu_sponge/d3d11_proxy.c` → `lol13.3\d3d11.dll`, cu `d3d11_real.dll` copia celui de
  sistem): patch pe tabelele de metode ale device-ului, contextului și swapchain-ului. Runtime-ul D3D11 își rescrie
  singur intrările de desen din tabelul contextului (variante după stare) — burete le reface după fiecare apel.
  Înregistrează: bytecode-ul fiecărui shader, fiecare textură/buffer/stare creată (cu hash-ul datelor), iar la cerere
  (`sponge_capture.txt`) fiecare desen cu tot ce era legat și fiecare scriere în buffere.
  `tools/run_replay.sh start|seek|capture|stop`, `tools/read_sponge.py`, `tools/shader_index.py`
  (numește shaderele prinse după ShaderCache.dx11).
- Primul cadru (replay la 2,7 s): 575 de desene, toate shaderele numite. Ordinea Riot: harta (`srx_blend_master`,
  `defaultenv_flat[_alphatest]`, `flickeralpha_flipbook`), personaje (`lit_uber`, `darkstar`), particule (`quad`, `mesh`,
  `distortion`, `quad_fixedalphauv`, `skinnedmesh/particle`), ceața războiului (`fogofwar/fastseparablegaussianblur`,
  `fade`, `applyoverlayandcolor`, `hud/minimapfow`), post (`bloomhigh`, `fxaa_ps`, `gamma/ps_gamma`), UI (`ui`, `font`,
  `cooldown`, `ammoline`, `desaturate`, `circlemaskdesaturate`).

## Buretele 2: ce s-a măsurat pe clientul 13.3 (2026-10-03, după restart)

Unelte noi în `tools/`: `texture_index.py` (hash de textură GPU -> fișier din WAD), `explain_draw.py` (un desen:
permutarea shaderului, stările de amestec / adâncime / raster, fiecare constantă pe numele din shader),
`run_replay.sh cam | pause | play | only` (camera liberă a Replay API ține poziția doar în modul `fps`; `only` ascunde
toate sistemele de particule în afară de cele numite). Buretele citește acum înapoi de pe GPU și bufferele de constante
care nu au fost scrise în cadrul capturat (efectele statice). În clientul nostru: `--eye x,y,z` (camera exact ca a
clientului Riot: ochi la 1911,85 deasupra, 1289,5 în spate, înclinare 56, FOV 40), `BA_VFX_DUMP=<fișier>` (fiecare desen
de particule al ultimului cadru), `BA_VFX_ONLY=<nume>`.

Capturi păstrate: `data/sponge/t005` (râu, 17 s), `t007` / `t010` (baza roșie), `t011` (baza roșie doar cu efectele
statuii și ale apei).

| Ce | Măsurat | Unde e aplicat |
|---|---|---|
| Tufișuri | personaje desenate cu `lit_uber` (permutarea TINTING); primul os stă exact pe un `GdsMapObject` tip 10; `TINT_COLOR` = harta de nuanță a ierbii la poziția tufișului (majoritatea la 1/255; câteva mai închise: [de măsurat]); instanțele aceluiași model nu sunt în fază | `LevelProps` în `client/src/main.cpp` |
| Decor animat | 1352 obiecte tip 10 în `base_srx.materials.bin`: 1279 tufișuri + negustori, animale; cele cu `eSportCharacter: 1` (steagurile) nu se desenează | idem |
| Graful tufișului | `Distance` (GrassSwayIntensityParametricUpdater: 0 -> Idle1, 100 -> direcție) și direcția (GrassSwayDirectionParametricUpdater: -180..180 -> Back / Left / Front / Right) | doar Idle1 deocamdată; legănarea la trecerea unităților: de făcut |
| Lumina personajelor | `LIGHTGRID_COLORS` = (1 + max(0, soare·normală)) / 1,75 pe fiecare față, `LIGHTGRID_SCALE` = (1,75; 0,25), `SELF_ILLUMINATION` din skin: lumina se saturează la 1 (personaje la luminozitate plină) | neschimbat (rezultatul nostru e același) |
| Moduri de amestec ale particulelor | `blendMode` lipsă -> ONE, ONE (alfa culorii nu contează: vârfurile au alfa 255); 1 -> SRC_ALPHA, INV_SRC_ALPHA; 3 -> fără amestec, adâncime scrisă; 4 -> SRC_ALPHA, ONE | `client/src/Vfx.cpp` |
| `uvMode: 2` | alfa texturii se citește la UV-ul fără derulare (`SEPARATE_ALPHA_UV` / `quad_vs_fixedalphauv`), 28 din 28 de desene | idem |
| Textura „mult" | în 12.23 `textureMult` e chiar calea, iar câmpurile ei stau în emitter (în 13.3+ sunt într-un `VfxTextureMultDefinitionData`); necitită, cascadele ieșeau mult prea luminoase | idem |
| `assetRemappingTable` | `oldAsset` e hash FNV-1a; tabela schimbă texturile Order <-> Chaos doar pentru jucătorul din Chaos (culori relative) | idem |
| Modele `.scb` | pozițiile, UV-urile și culorile noastre coincid vârf cu vârf cu bufferul încărcat de client | verificat, neschimbat |
| Rotația particulelor-model | `birthRotation0 (0, θ, 0)` -> x' = cos θ·x + sin θ·z | verificat, neschimbat |
| Structuri | stau la înălțimea și scara obiectului lor de hartă: cristalul fântânii roșii la y 466, scară 0,5; inhibitorii 1,1 / 1,2; turnul fântânii albastre 0,89 | `structure_height` în `main.cpp` |
| Piste de animație cu același hash | scheletul `SRUAP_MageCrystal` are oasele „root" și „Root" (hash identic); fiecare are pista lui: al k-lea os ia a k-a pistă | `common/src/Model.cpp`, `Character.cpp` |

Nelămurit: emitterul `ShoreTop` (spuma de pe marginea bazinului, `importance: 0`, tabelă de probabilitate pe scară) nu e
desenat de clientul Riot în niciuna dintre capturi, la noi apare. `birthUvRotateRateMult`, `texDivMult`,
`uvScrollAlphaMult`, `uvScrollClampMult` nu sunt citite încă.

Clientul Riot: după blocajul de la 08:11 (pauză + captură), pornește din nou după repornirea Windows-ului. Rulează pe
ecran complet; când își pierde focusul fereastra ajunge la 1x1 și imaginea salvată e goală (desenele rămân valide).

## Plăcile turnurilor exterioare (2026-10-03)

Stâlpii cu cristale din jurul turnurilor exterioare nu sunt o animație a turnului: sunt o unitate separată,
`PreSeason_Turret_Shield`.

- **Serverul** [măsurat: pachetele unui meci real 12.23, `data/replays1223`, meciul 0]: la timpul 0 apare câte un
  `SpawnMinion` cu acest nume pe poziția fiecăruia dintre cele 6 turnuri exterioare, neselectabil, orientat spre punctul
  de apariție al echipei lui (`position2 - position1` e vectorul unitate spre `__Spawn_T1` / `__Spawn_T2`, pe toate
  șase); cele rămase mor la 845,06 s. Niciun script din datele clientului nu o creează. La noi:
  `Match::spawn_turret_plating` (`server/src/MatchLevel.cpp`); dispare odată cu turnul sau la 845,06 s. Nelămurit: la
  turnul roșu de jos pachetele dau z 4525, obiectul de hartă 4505.
- **Skinul** [măsurat: textura legată de clientul 13.3]: 0 pe turnurile Order (cristale albastre), 2 pe cele Chaos
  (numit „Choas_Blue", dar cu textura `..._Skin02_Chaos_Red`, cristale roșii). 1 și 3 sunt cealaltă culoare a fiecăruia
  (ce vede un jucător din Chaos): nefăcut.
- **Animațiile** [măsurat cu potrivitorul de poziții, `client.exe --match-pose`]: după creare `Spawn` (7,2 s), apoi
  `Idle1`; scara 1,1 (a skinului), orientarea −137,44° la turnul albastru de mijloc și 42,47° la cel roșu, exact
  direcția spre punctul de apariție.
- **Ruperea plăcilor**: graful are `Part1..5_Hit`, `Part1..5_Destruction`, `Shutdown0..4` pe piste cu `mBlendMode: 1`:
  valorile lor se adună peste poziția de repaus (translații adunate, rotații și scări înmulțite); redate singure strâng
  toate oasele în origine. Prima placă distrusă e `Part1` [măsurat: cu o placă lipsă clientul nu mai desenează
  submesh-ul `Unbroken_Part1` și nimic în locul lui]; ordinea 1..5 a celorlalte și „o placă = o cincime din viață" sunt
  [dedus]. La noi: `CharacterInstance::add_clip` + `Clip::additive` (`client/src/Character.*`), logica în `main.cpp`.
  `ShutdownN` (căderea plăcilor la minutul 14) nu e redat încă.

Potrivitorul de poziții: `python tools/palette.py <captură> <desen> pal.txt`, apoi
`client.exe --champion <personaj> --dump-skin <n> --match-pose pal.txt` scrie `pose_match.txt`: animația și momentul
care reproduc oasele din captură, plus poziția, orientarea și scara unității.

## Buretele 3: decodorul de pachete al exe-ului 13.3 (2026-10-03)

Sursa: imaginea din memorie a clientului 13.3 în timp ce rula replay-ul (`client-src/exe_image_t900.bin`, bază
0x580000). La prima trecere 1178 din 4010 pagini de cod rămâneau criptate (Riot le decriptează la cerere, abia când
codul lor e folosit prima oară), dar tot codul de rețea folosit de replay era deja în clar.

### Deblocarea tuturor paginilor de cod (2026-10-03, seara)

Împachetătorul (`stub.dll`) ține fiecare pagină de cod nefolosită cu pagină neaccesibilă până la prima folosire `PAGE_NOACCESS`; la prima atingere,
gestionarul lui de excepții decriptează pagina pe loc și o lasă `PAGE_EXECUTE_READ`. Buretele face acum chiar asta,
fără să modifice nimic din proces: pe cererea fișierului `sponge_touch.txt` (format `mod primul număr`) citește câte un
octet din fiecare pagină blocată din `.text`, exact cum ar face jocul la prima folosire, și lasă împachetătorul să o
servească. `tools/run_replay.sh touch <mod> [primul count]`: **mod 0** doar numără paginile blocate; **mod 1**
citește din codul buretelui; **mod 2** citește printr-o instrucțiune `mov al, [ecx]; ret` care face parte din codul
jocului (rva 0x243bdc, verificată înainte). Un gestionar de excepții vectorizat prins ultimul (`touch_veh`) prinde
cazul în care împachetătorul *nu* servește pagina și o sare — pagina rămâne blocată, jocul merge mai departe. (Prima
oară, cu citirea din DLL-ul nostru pe toate cele 4010 pagini deodată, clientul a rămas blocat pe un thread și a trebuit
oprit; servit pagină cu pagină, în tranșe, cu verificarea `/replay/playback` între ele, s-a desfășurat fără incident.)

Rezultat (`client-src/exe_image_unpacked.bin`, dump complet după atingere; `..._pages.txt` = regiunile si
permisiunile lor de memorie): **toate cele 1178 de pagini deschise, 0 neservite**. Dintre cele 1177 nou-apărute (una era goală și în
imaginea veche), **1046 se dezasamblează curat** ca și cod — acoperirea curată urcă de la 2832 la **3683 din 4010
pagini**. Codul nou cuprinde primitivele OpenSSL CRYPTOGAMS (RC4, ChaCha20, Camellia pentru x86) și buclele de
de-obfuscare a câmpurilor pe care `packet_emu.py` le reconstruise (ex. rva 0x14b000: `xor 0xab`, căutare în tabela de
la rva 0xfb5850, `sub`, `ror`, `ror`, scriere — acum vizibile ca sursă Riot). `server/exe_dis.py` folosește acum
`exe_image_unpacked.bin` (suprascriere cu `BA_EXE_IMG=`).

**Corectat pe 2026-10-04:** blocul de la rva 0x1c000..0x41000, despre care scria aici că „rămâne criptat”, nu e
criptat. E o tabelă de date, corect decriptată (vezi „Harta completă a secțiunii de cod”). Nicio pagină de cod nu
lipsește din imagine.

- **Recepția** [citit în cod, rva 0x351c60]: citește un ID de pachet u16, cere obiectul de la fabrică, apoi apelează
  `vtable[1](&cursor, end)` = deserializarea; la eșec scrie în log `SEJ-A56A09C4 {#PacketID}`.
- **Fabrica** [rva 0x7fc950]: `switch (id - 2)` pe 0x315 cazuri (tabel de salt la rva 0x804ddc); fiecare caz =
  `new(mărime)` + constructor. **556 de tipuri de pachete** în 13.3, tabelul complet în `data/exe133/packet_table.txt`
  (id, mărimea obiectului, constructor, vtable, deserializator); `tools/packet_table.py` îl reface.
- **Trimiterea** [rva 0x36ef80]: `vtable[0]` = serializarea; peste 0xffff octeți scrie `SEJ-J72G92B`.
- **Formatul pe fir**: `[id u16][netID u32][corp]`; replay-ul ține id-ul și netID-ul în antetul blocului, corpul e
  identic.
- **Obfuscarea câmpurilor**: fiecare câmp e citit din biții de pe fir (cu tabele de substituție per câmp), apoi e
  ascuns pe loc în obiect, octet cu octet (o buclă `mov byte [r], al; inc r; cmp r, end; jne`); citirea lui în joc îl
  decodează la loc. Valoarea în clar = conținutul câmpului chiar înainte de bucla care îl ascunde.
- **Emulatorul** (`server/packet_emu.py`, Unicorn): rulează constructorul și deserializatorul Riot pe pachetele
  replay-ului. `check` → **toate cele 1.399.917 pachete ale replay-ului 13.3 (173 de tipuri) sunt acceptate și citite
  exact până la ultimul octet** (`data/exe133/emu_check.txt`). `fields <id> [n]` arată câmpurile în clar ale primelor
  n pachete; `decode <out.jsonl.gz> [k/N]` scrie tot replay-ul cu câmpurile în clar (făcut, cu regulile
  corectate: 8 părți `data/exe133/decoded_13.3_part0..7.jsonl.gz`, după poziția în flux `% 8`, câmpul `i` =
  poziția; 1.399.917 pachete, 0 eșuate, 95 MB). Alocatorii jocului (operator new,
  rva 0x9bb8d0; pool-ul de la rva 0x9d4570) sunt înlocuiți; TEB-ul are slotul TLS plin, ca statice MSVC să fie văzute
  inițializate.
- **Primul pachet citit în clar, id 98 = apariția unui minion** [măsurat]: +0x0c ora (float, 65,039 s la primul val),
  +0x10 netID-ul minionului, +0x14 = 4, +0x15 = 1, +0x16 = 22, +0x18 = 64, +0x1c netID-ul barăcii (0xFFBA00E8,
  0xFF5EC9AF), +0x20 = 1. Sensul lui 4 / 1 / 22 / 64 / 1 se deduce comparând valurile între ele.
- Pachetele mari țin liste: 595 (149k pachete, 29 MB) are un tampon de 2100 octeți; 367 (69k, 29 MB) are o listă de
  elemente polimorfe de 152 octeți (vtable rva 0x15bf6e8).
- **Numele tipurilor**: legătura id → funcția de tratare se face la rulare (hărți FNV-1a după netID și id, rva
  0x352610), nu stă static în imagine. Numirea se face potrivind câmpurile în clar cu pachetele 12.23 cu nume
  (`data/replays1223`, setul maknee). Mostre din fiecare tip: `data/exe133/kinds_sample.txt`.
  - 98 = `BarrackSpawnUnit` [măsurat: aceleași netID-uri de barăci ca în 12.23, ora 65,04, valul 1].
  - [dedus, de confirmat] 506 = `DoSetCooldown` (slot 0/1/2, display −1 la t 0); 387 = `LeaveFog` (511k, 1 octet);
    595 = `Replication` (149k pe canalul 2; confirmat, vezi mai jos); 68 = ~~crearea turnurilor~~ **greșit**: e
    iconița de pe minihartă a unei unități (vezi „Numele din șirurile pachetelor”); 286 / 26 / 592 =
    atacuri de bază (minion / turn / campion: țintă, netID proiectil, poziție); 49 = `CastSpellAns` (hash vrajă,
    proiectil); 134 = sunet (`Play_s…`); 65 / 790 = nume de animații (`Idl…`, `Recall…`).
- Vectorii 3D: deserializatorul trece bucla de ascundere o dată peste câmpul gol, apoi îl citește și îl ascunde din
  nou; valoarea în clar = starea dinaintea **ultimei** treceri (rezolvat). Șirurile ies octet cu octet.

### Fluxul nostru lângă al lui Riot (`tools/netlog_compare.py`)

`server.exe --netlog <f.banl>` (în meci sau cu `--simulate S`) scrie fiecare mesaj trimis; construirea mesajelor unui
tick e acum o singură funcție (`emit_tick`, `server/src/main.cpp`), folosită și de rețea și de simulare.
`netlog_compare.py kinds|waves <f.banl>`.

Valurile de minioni (pachetul 98 Riot vs `UnitSpawn` al nostru, simulare de 1868 s) [măsurat]:
- același număr pe val (36; 42 cu tunuri la fiecare al treilea val, apoi la fiecare al doilea după ~900 s), 6
  barăci, aceleași momente la ±0,04 s pe primele valuri;
- în val: un minion pe baracă la 0,8225..0,8295 s (medie 0,826; scriptul: 825 ms) — la fel la noi;
- între valuri: 30,000..30,033 s (doar primul 29,977), medie 30,014: timerul se re-armează de la momentul real al
  valului, iar valurile alunecă (+0,88 s la valul 60). Aplicat: `next_wave_` (`server/src/MatchLevel.cpp`). Rest
  nerezolvat: tick-ul nostru fix de 33 ms face din 30 s mereu 910 tick-uri = 30,030 s (la valul 60: +0,90 s față de
  Riot; înainte, cu orar fix, −0,88 s); cadrele Riot sunt de durată variabilă.
- câmpurile pachetului 98 [măsurat]: +0x14 = tipul (4 corp la corp, 5 la distanță, 6 tun); +0x15 = numărul valului;
  +0x16 = partea întreagă a `HPBonus` din script (22 / 6 / 62 la primul val, apoi 44, 66, 89, 113, 146 …: primul
  upgrade, `UpgradeMinionTimerInitial`, rulează la 65 s înaintea primului val). **La noi e identic**: viața
  minionului corp la corp e 455 + bonus = 477, 499,3, 521,9 … val cu val. +0x20 urcă neregulat 1..14 (pare să
  depindă de jucători); +0x18 = 64 constant. Ordinea într-un val: corp la corp ×3, tunul, la distanță ×3.

Alte tipuri numite [măsurat pe replay, după netID-uri și valori]:
- 263 = `UnitApplyDamage`: obj = ținta, +0x14 damage (12,0 la primul schimb de lovituri: AD-ul minionului corp la
  corp), +0x20 sursa.
- 286 = atacul de bază al unui minion: obj = atacatorul, +0x14 ținta, +0x2c netID-ul atacului, +0x30 poziția
  atacatorului (x, y, z), +0x3c / +0x40 poziția țintei. Damage-ul (263) vine la 0,397 s după (windup-ul).
- 61 = moartea (obj = unitatea; 98% din minioni, mediana la 37,6 s după apariție).
- 506 = de 4 ori la apariția fiecărei unități (slot 0..3, display −1: cooldown-uri); 606, 770, 518 = o dată la
  apariție; 359 + 488 = creaturile din junglă la 88,93 s (poziții de tabără).

**Diferență găsită, nerezolvată: momentul primului atac al minionilor.** Riot: 88,535 s, cei doi minioni la 88–119
unități între centre; la noi: 88,308 s, la 199 de unități (raza de atac 110 + razele). Pe toate valurile și culoarele,
distanța la care începe atacul la Riot variază 76…237 → între intrarea în rază și atac trece o întârziere variabilă
de 0…~0,19 s (IA-ul minionilor nu caută ținta la fiecare cadru?). Perioada nu se poate stabili fără pozițiile în timp:
pachetul de mișcare 552 ține un tampon comprimat (decodat acum în clar, formatul încă necitit).

**Pachetul de mișcare 552 (`WaypointGroup`), citit** (`server/waypoints.py`) [măsurat: toate cele 42.706 de
tampoane ale replay-ului se citesc până la ultimul octet]: obiectul are +0x0a numărul de intrări, +0x0c un contor,
+0x10 tamponul. Fiecare intrare: u8 = 2 × numărul de puncte (+1 dacă urmează un octet „teleport id”), u8 flaguri,
u32 netID, f32 viteza, [u8 teleport id], câte un bit pe coordonată după primul punct (1 = delta pe un octet cu semn,
0 = i16 întreg), apoi x0, z0 (i16) și restul. Poziția = 2 × coordonata + mijlocul limitelor grilei de navigare
((min + max) / 2 din `AIPath_SRX_2.aimesh_ngrid` = 7358,65; 7412,48), potrivit pe 1517 poziții de atac. Prin 552 se
mișcă și campionii, și minionii (89 de mii de intrări de minion).

**Retrimiterea traiectoriei la minionii împinși** [măsurat, aplicat]: la Riot, înainte de primul atac un minion își
primește traiectoria de ~12 ori; ~1,8 dintre ele au aceeași destinație ca precedenta, la 2,01..2,08 s una de alta. La
noi: tot ~11 cu destinație nouă, dar 79 cu aceeași destinație (raportul de împingere la fiecare 12 unități). Acum un
minion împins e retrimis cel mult o dată la 2 s (`kMinionPathResend`, `server/src/Match.cpp`): 1,4 pe minion, la
2,01 s; simularea dă exact același joc, fluxul scade de la 19 la 11,4 MB, simularea e de 3,5 ori mai rapidă.

**Momentul atacului, măsurat cu pozițiile reale**: distanța între centre la începutul primului atac — corp la corp
mediana 148 (p10 95, p90 192; maximul teoretic rază + raze ≈ 206), la distanță 587 (p90 632; ≈ 646), tun 347. Achiziția
țintei se vede ca traiectorie nouă spre țintă (la primul val din mijloc: 87,909 s, la 410 unități), atacul vine când
sunt deja mult sub rază. Nu e un timer periodic (nicio concentrare de fază la perioade 0,067..0,6 s, nici față de
apariție, nici globală). Mecanismul rămâne nelămurit; la noi atacul pornește la intrarea în rază (neschimbat).

Unealta, două corecții: Unicorn nu dă valoarea scrierilor SSE (fiecare valoare se citește acum din memorie după
scriere), iar o buclă care scrie octet cu octet dar citește din altă parte (de pe fir) e o citire, nu o ascundere.

## Harta completă a secțiunii de cod (2026-10-04)

Întrebarea: ce e în fiecare din cele 4010 pagini ale `.text` și lipsește ceva? Răspuns: **nu lipsește cod**. Unealta
`tools/code_map.py` dă fiecărui octet din `.text` (16.424.960 de octeți) o clasă și verifică singură rezultatul.

Cum merge (`code_map.py build`, 25 s):
- **semințe**: punctul de intrare, tabela de exporturi și fiecare adresă relocată din `.rdata` / `.data` care arată în
  `.text` (62.945: tabele virtuale, funcții de apel invers, tabele de excepții);
- **coborâre**: dezasamblează de la fiecare sămânță, urmează salturile și apelurile, se oprește la `ret` / `jmp` /
  `int3` și după apelul unei funcții care nu se întoarce (23 găsite: după apelul lor compilatorul lasă `int3`);
- **tabele**: tabelele de salt ale `switch`-urilor sunt găsite din codul care le folosește (`jmp [reg*4 + A]`,
  `movzx r, byte ptr [reg + A]`), cu lungimea din limita `cmp reg, N` dinaintea lor;
- **insule**: cod la care nu duce nimic (funcții moarte sau apelate doar prin adrese calculate), acceptat doar dacă
  se dezasamblează curat de la un capăt explicat până la `ret` / `jmp`;
- **date cunoscute**: tabelele identificate după conținut (lista de mai jos).

Rezultat [măsurat]:

| clasă | octeți | parte |
|---|---|---|
| cod atins din semințe | 15.462.663 | 94,14% |
| cod-insulă (nimic nu arată spre el) | 219.894 | 1,34% |
| tabele de salt (adrese) | 34.400 | 0,21% |
| tabele de indici ale `switch`-urilor | 17.714 | 0,11% |
| umplutură între funcții (`int3`, `nop`) | 508.065 | 3,09% |
| date identificate | 169.936 | 1,03% |
| pagină goală (rva 0x1000) | 4.096 | 0,02% |
| **neexplicat** | **8.192** | **0,05%** |

- **4008 din 4010 pagini au fiecare octet explicat.** 57.499 de începuturi de funcții (`client-src/functions.txt`).
- Verificarea hărții (`code_map.py audit`): din 4.787.371 de instrucțiuni marcate drept cod, doar 11 sunt de un fel pe
  care codul compilat nu îl are, și toate 11 sunt legitime (`int 0x29` = oprirea rapidă a CRT-ului, `xlatb` în
  funcțiile matematice scrise de mână, `loop` în asamblarea OpenSSL). Zero conflicte de decodare (niciun drum nu
  intră în mijlocul unei instrucțiuni decodate de alt drum).
- Cifra veche „3683 din 4010 pagini curate” venea dintr-o regulă pe pagină întreagă, care respingea paginile cu
  tabele printre funcții. Harta pe octeți o înlocuiește.

**Blocul de 37 de pagini (rva 0x1c000..0x41000) nu e criptat** [măsurat]: e `ecp_nistz256_precomputed` din OpenSSL,
tabela de 37 × 64 de puncte ale curbei P-256 (64 de octeți fiecare = 151.552 de octeți = exact 37 de pagini), aliniată
la pagină, urmată imediat de constanta `RR = 3, 0, −1, −5, −2, −1, −3, 4` a aceluiași fișier. `tools/
nistz256_table.py` o recalculează din ecuația curbei (intrarea [i][j] = (j+1)·2^(7i)·G, în formă Montgomery) și, după
transpunerea pe octeți pe care o folosește varianta x86 (octetul i al intrării n stă la i·64 + n), **toate cele 37 de
pagini sunt egale octet cu octet cu imaginea**. Entropia mare (7,95 biți/octet) vine din faptul că sunt numere de
256 de biți, nu din criptare.

Alte date ținute în `.text`, recunoscute după constante (lista `KNOWN` din unealtă, fiecare verificată la construire):
tabelele OpenSSL scrise de mână — Whirlpool (0x48b00), Camellia SIGMA + S-box (0x13dc0), DES SPtrans (0x11e80),
SHA-512 K (0xff00), SHA-256 K (0x86c0), GHASH (0x1a480), SHA-1, ChaCha20, AES-NI, constantele nistz256 (0x41000),
textele „… CRYPTOGAMS by <appro@openssl.org>”; și formatele de date DirectInput `c_dfDIMouse2` + `c_dfDIKeyboard`
(0x69310, 267 de intrări a 16 octeți, cu adresele GUID-urilor de axă / tastă). Asamblarea OpenSSL își citește tabelele
relativ la contorul de program, de aceea nicio adresă din imagine nu arată spre ele.

**Ce rămâne neexplicat: 2 pagini, rva 0x2000..0x4000** [măsurat ce conțin, sensul necunoscut]. Sunt aproape goale: 173
de octeți nenuli din 8192, așezați pe coloane la pas de 64 (pagina 0x2000: coloanele 53 și 54; pagina 0x3000: 12 și
14). O coloană ține valori de forma 2^k − 1 (0x01, 0x03, 0x07, 0x0f, 0x7f), cealaltă tipare de biți (0x92, 0xb6, 0x96…
respectiv 0x41, 0xc1, 0xc3…). Nu sunt instrucțiuni. Ca să aflăm ce sunt trebuie văzut cine le citește în timpul
rulării (un pas cu buretele, pe clientul pornit).

Despre împachetător, aflat pe drum [măsurat]:
- tabela de relocări a imaginii nu are nicio intrare în `.text` (0 din 82.898): împachetătorul își relochează singur
  codul după ce îl decriptează;
- pe disc 3996 din 4010 pagini sunt criptate, cu două cifruri pe pagină: unul = un bloc de 64 de octeți repetat,
  cu un singur octet-contor care se schimbă de la bloc la bloc; celălalt = un șir fără perioadă.

## Tabela id de pachet → funcția care îl tratează (2026-10-04)

Legătura nu stă într-o tabelă statică, dar codul care o construiește da [citit în cod]:
- **`RegisterHandler`** (rva 0x3710a0): argumente = obiectul, id-ul pachetului (constantă), un `std::function`. Are 260
  de apeluri; `tools/handlers.py table` scoate din fiecare id-ul și funcția membru →
  `client-src/handler_table.txt`.
- **Ascultătorii generali** (lista de la +0x198 a clientului de rețea, `vtable[1](pachet, timp)`): funcții care fac
  singure `switch` pe id. `tools/listeners.py` le găsește și le citește cazurile: rva 0x355f80 (lumea: 185
  de id-uri, între ele 98 apariția minionilor, 552 mișcarea, 595 replicarea, 367), 0x562a80 (37), 0x3554e0 (16,
  sincronizare / conexiune), 0x3601d0 (9).
- Acoperire: **171 din cele 173 de tipuri din replay** au funcția de tratare localizată (lipsesc 213 și 215); 497 din
  cele 556 de id-uri ale fabricii. `handlers.py digest` → `client-src/handler_digest.txt` (tip, număr, funcție,
  șirurile la care ajunge codul ei).

### Numele din șirurile pachetelor (`tools/kind_strings.py` → `data/exe133/kind_strings.txt`) [măsurat]

- **71 = lista de înlocuiri de animație a unei unități** (perechi „animația nouă, animația înlocuită”; pachetul
  poartă lista întreagă de fiecare dată când se schimbă; listă goală = fără înlocuiri). Exemple: `Run_Fast` ← `RUN`,
  `CRIT` ← `ATTACK1` / `ATTACK2`, `IDLE_HOMEGUARD` ← `IDLE1..3`, `STATE2` ← `IDLE1`.
- **65 și 771 = redă o animație** (`Attack1_Dash`, `Spawn`, `Spell2`, `State2_seq`, `Death`…).
- **68 = iconița de pe minihartă a unității** (`WardDurationLow`, `TowerPalisades5`, `CampRespawn`, `Recall`…), nu
  crearea turnurilor cum scria mai sus.
- 345 = apariția unei unități oarecare (`SightWard`, `AzirSoldier`, `SRU_Plant_Health`…); 359 = monstru de junglă
  (`SRU_RazorbeakMini`, `North_Spawn4`); 134 / 438 = sunet (`Play_sfx_…`, `Play_vo_…`); 496 = schimbare de material
  (`Tower_Palisades_Order_Unbroken_Part1_Mat`); 589 = animațiile obiectelor hărții (`RUNETIMER_CHAOS_TOP`,
  `BARON_VFX1`); 259 / 723 = numele vrăjii dintr-un slot (`SummonerFlash`, `TalonWMissileTwo`); 612 = schimbarea
  modelului (`NidaleeCougar`); 172 / 156 = iconițe de dragon pe minihartă; 574 = lista jucătorilor (rang, poziții).
- Din șirurile funcției de tratare: 98 = `Minion_T%03dL%01dS%02uN%04d` (numele minionului), 263 = textul plutitor al
  loviturii (`game_floatingtext_dodge` / `miss` / `invulnerable`).

### Regulă măsurată, neaplicată încă: animația morții unui minion depinde de cine l-a ucis

Pe tot meciul (1.285 de morți de minioni uciși de minioni, fără nicio excepție): când un minion corp la corp sau la
distanță e ucis **de un minion**, serverul trimite în aceeași clipă cu moartea (61) un pachet 71 cu înlocuirea
`DEATH` → `DEATH_MELEE` (ucigaș corp la corp), `DEATH_CASTER` (ucigaș la distanță) sau `DEATH_SUPER` (ucigaș tun
sau super-minion). Tunurile și super-minionii uciși nu primesc nimic; la fel orice minion ucis de un campion.
Datele 12.23 au clipurile (minionul corp la corp: `Death` = `minion_melee_death.anm`, `Death_Melee` = `…death2`,
`Death_Super` = `…death3`, `Death_Caster` = `…death4`). La noi toți minionii redau `Death`.

### Stările de avarie ale structurilor: mecanismul [măsurat], pragurile încă nu

La fiecare treaptă serverul trimite două pachete în aceeași clipă: 65 (redă `State2_seq` / `State3_seq` /
`Destroyed_seq`, tranziția) și 71 (`STATE2` / `State3` / `Destroyed` înlocuiește `IDLE1`, bucla de după). Pragurile de
viață nu se pot scoate din pachetul de daune 263 (nu cuprinde daunele minionilor); trebuie viața din replicare.

### Pachetul de replicare 595, citit (`server/replication.py`) [măsurat]

Toate cele 74.543 de tampoane se citesc până la ultimul octet: `u8` mască de grupe, `u32` netID, apoi pe grupă `u32`
mască de valori, `u8` mărime, valorile. O valoare e fie un float (4 octeți; `0xff` singur = zero; `0xfe` + 4 octeți),
fie un întreg împachetat pe 7 biți. Care bit e ce nu stă în pachet: unealta învață felul fiecărui bit din grupele cu
o singură valoare. Aflat: viața unui turn = grupa 5 bitul 0 (5000,0 la început), a unui minion = grupa 3 bitul 0.
Același conținut apare de mai multe ori la rând (câte o copie pe spectator): repetările sunt sărite.

## Trecerea pe 13.3 și modul de replay (2026-10-04)

**Criteriul de reușită, stabilit cu utilizatorul:** clientul nostru, pus pe replay-ul 13.3
(`data/rofl/KR-6363178603_13.3.rofl`), îl redă cap-coadă și scoate prin bureți același lucru ca al lui Riot. Asta
acoperă drumul replay-ului (cel mult ~70% din cod: jocul însuși deschisese 2832 din 4010 pagini după 900 s de
replay); ce face doar un jucător (comenzi, magazin, trimiterea de pachete) se verifică separat.

**Datele sunt acum 13.3** (`data-path.txt` → `C:\Users\Sorin\Desktop\ProiectBattleArenaPc\game`; vechea valoare în
`data-path.12.23.bak`). Verificat [măsurat]: simularea de 130 s dă exact același meci ca pe 12.23 (aceleași atacuri,
proiectile, morți); cei 5 campioni își lansează abilitățile fără erori noi (avertismentele lui Tryndamere despre
valori lipsă existau identic și pe 12.23).

### Cum pornește un replay [măsurat]

Fluxul din bucățile replay-ului nu creează turnurile și campionii: starea de pornire stă în **cadrele-cheie** (32, câte
unul pe minut). Primul are 3203 pachete de 64 de tipuri, dintre care 33 nu apar deloc în bucăți; emulatorul le citește
pe toate (`packet_emu.py key 1 decode …`, 0 eșuate, acum pe imaginea cu toate paginile deschise).

- 79 = crearea unui campion: +0x18 netID, +0x20 numele campionului, +0x30 numele jucătorului, +0x44 poziția, +0x64
  skinul, +0x68 = 1 pentru cei cinci de la baza Order.
- 565 = crearea unui turn: netID 0x40000005.., +0x20 recordul (`SR_Outer`), +0x40 numele obiectului de hartă + `_A`
  (`Turret_T1_R_03_A`).
- 345 = orice altă unitate: +0x2c netID, +0x0c poziția, +0x3c personajul, +0x5c numele; 355 = cui îi aparține (plăcile
  unui turn).
- 518 = starea de mișcare a unei unități când devine vizibilă: octetul 26 al tamponului = 3 (stă: poziție + direcție)
  sau 2 (un drum, în formatul pachetului 552).
- **Obiectele puse de hartă** (inhibitoare `Barracks_T1_L1`, nexusuri `HQ_T1`, barăcile minionilor
  `__P_Order_Spawn_Barracks__C01`) nu sunt create prin pachete: clientul le are din hartă, cu netID =
  `0xFF000000 | (CRC-32(nume) & 0xFFFFFF)` [citit în cod, rva 0x2e9090; verificat pe 36 din cele 40 de astfel de
  id-uri din replay].
- Minionii morți nu sunt scoși de server: după pachetul morții nu mai vine nimic despre ei, clientul îi șterge singur.

### Clientul nostru redă replay-ul (`client/src/Replay.cpp`)

`client.exe --replay <fișier.barp> --offline-start <secunda>`; lansator: `Reda replay 13.3.cmd [secunda]`.
- **Etapa 1 (făcută):** fișierul `.barp` (`tools/export_replay.py`, 125 MB) ține pachetele cu câmpurile în clar,
  citite de deserializatoarele Riot în emulator: întâi primul cadru-cheie, apoi bucățile. Fiecare tip tratat în
  `Replay::apply` face lumii clientului ce face funcția de tratare a lui Riot.
- **Etapa 2 (nefăcută):** clientul citește direct `.rofl` (Blowfish, gzip, apoi cititoarele noastre de câmpuri,
  verificate funcție cu funcție față de emulator).
- Tratate acum, 14 tipuri: 79, 565, 345, 355, 98, 518, 552, 595, 61, 286 / 26 / 592, 263, 71.
- **Scorul** (fișierul `<captură>.replay.txt`, scris de client): la secunda 300 clientul a aplicat 36.634 din 184.629
  de pachete (19,8%) și are funcție pentru 14 din cele 176 de tipuri văzute. Ținta e 100%.
- Verificat pe capturi: valurile de minioni la mijloc la 95 s (poziții, viață 477 / 296), campionii replay-ului
  (Talon, Azir, Blitzcrank…) cu skinurile lor, iar minionul ucis de un minion la distanță redă `DEATH_CASTER` (regula
  măsurată mai sus, acum venită direct din pachetul 71).
- Provizoriu, de înlocuit cu ce spune fluxul: timpul unui atac vine din recordul unității (viteza de atac replicată
  nu e citită încă), proiectilul pleacă la sfârșitul pregătirii (pachetul 117 necitit), trupul unui minion stă 3 s.

Comparația cu bureții pe clientul Riot la aceeași secundă și aceeași cameră nu a fost rulată încă (cere pornirea
clientului Riot).

## Exe-ul 13.3 despachetat, pornit de biblioteca noastră (2026-10-04)

**Hotărârea utilizatorului:** în loc să refacem clientul bucată cu bucată, luăm tot exe-ul 13.3: îl despachetăm, îl
facem să meargă întreg fără împachetător, apoi înțelegem și organizăm, înlocuind funcție cu funcție cu C++ scris de
noi. Exe-ul merge la fiecare pas; scorul = câte din cele 57.499 de funcții sunt deja ale noastre.

**Pasul 1 și 2, făcute** [măsurat]: `League of Legends.unpacked.exe` pornește fără `stub.dll` (verificat cu fișierul
`stub.dll` redenumit, deci absent), trece prin `GAMESTATE_PREGAME → SPAWN → GAMELOOP` și redă replay-ul: API-ul de
replay raportează timpul înaintând, iar buretele GPU a numărat peste 1,2 milioane de desene în primele 3000 de cadre.
Lansator: `Porneste 13.3 despachetat.cmd`.

Cum e asamblat (`client-src/build_unpacked.py`):
- antetele și secțiunile de date vin din fișierul de pe disc (sunt în clar); `.text` vine din imaginea decriptată;
- codul a fost relocat de împachetător la baza 0x580000, iar lista acelor relocări o ține doar el, așa că noul exe
  are baza fixă 0x580000: datele sunt relocate o singură dată, cu tabela de relocări a fișierului (82.898 de intrări,
  niciuna în `.text`), apoi tabela e oprită. Verificare: după relocare, `.rdata` e identică cu cea din procesul viu
  pe 1957 din 1959 pagini (cele două care diferă sunt sloturile umplute la pornire);
- secțiunea `.text` e marcată pe disc doar „cod”, fără drept de citire sau execuție (împachetătorul și-l dădea
  singur): acum e citibilă și executabilă;
- punctul real de intrare: rva 0xf40d33 (`call __security_init_cookie; jmp __scrt_common_main_seh`, singurul cod de
  forma asta spre care nu arată nimic);
- vechea secțiune `.stub` ține acum un salt de 11 octeți (`call ba_start`, apoi salt la intrarea reală) și singurul
  import al fișierului: `ba_host.dll!ba_start`.

**Importurile** [măsurat]: împachetătorul scosese lista funcțiilor Windows; la pornire pune în fiecare din cele 430 de
sloturi (rva 0xfab000..0xfab708) adresa unui mic cod al lui, care calculează adresa reală (`push eax; mov eax, K;`
câteva `rol` / `bswap` / `add`; `ret 4`). `client-src/read_stubs.py` le-a citit din procesul viu (doar citire, din
afară), iar `resolve_imports.py` le-a rulat în emulator și a găsit pentru fiecare modulul și funcția:
`client-src/import_table.txt`, 430 din 430 numite (KERNEL32 188, USER32 58, WS2_32 43, advapi32 35 …).
`client-src/ba_host.c` (biblioteca noastră, 32 de biți) umple sloturile la pornire.

**Neumplut, cu bună știință:** 25 de sloturi la rva 0xfb2808..0xfb2884 prin care jocul cheamă servicii ale
împachetătorului însuși. Funcțiile jocului care le folosesc verifică dacă slotul e gol și întorc „indisponibil”;
jocul a pornit și a redat replay-ul cu ele goale. Ce făceau acele servicii nu știm încă.

**Neverificat încă:** replay-ul până la capăt (a rulat ~2 minute), săritul în timp, un meci jucat; comparația prin
bureți între exe-ul original și cel despachetat (ar trebui să fie identice: e același cod).

**Pasul 3, de început:** înlocuirea funcțiilor. `ba_host.dll` e locul: pune un salt la începutul unei funcții a
jocului spre varianta noastră în C++, după ce varianta a fost verificată față de original pe aceleași intrări.

## Clientul 13.3 despachetat în mod de meci: ce cere de la un server (2026-10-04)

**Hotărârea utilizatorului:** întâi conectăm clientul despachetat la serverul nostru; arhitectura serverului o
deducem din ce cere clientul și din fluxul replay-ului.

[măsurat] Pornit cu `"127.0.0.1 5119 <cheie> <id jucător>" -Product=LoL -PlayerID=1 -GameID=1 -GameBaseDir=…`
(primul argument = adresa serverului în locul fișierului `.rofl`), clientul intră în mod de meci: scrie în log
`Connecting to address (127.0.0.1) port (5119)`, `Waiting for response from game server...`, iar după 30 s fără
răspuns arată fereastra „Failed to Connect”. `tools/udp_listen.py` (un ascultător care nu răspunde nimic) a
prins ce trimite: datagrame UDP de 515 octeți, una la 0,1 s, toate cu aceiași primi 8 octeți (`44cdc6edede36b43`),
restul cifrat, câteva variante care se repetă. La fel cu și fără `-EnableLNP`: 13.3 are un singur protocol de
transport, cel nou al lui Riot (în imagine nu există niciun șir „ENet”). Capturi:
`data/exe133/client_hello_lnp.txt`, `client_hello_enet.txt`.

Unde e codul de transport [citit în cod]: o singură funcție cheamă `sendto` (rva 0x2ef720), una singură `recvfrom`
(rva 0x2ed590); socketul e creat la rva 0x2eb010.

**Scriitoarele de pachete lipsesc din client** [măsurat]: din 529 de clase de pachete, toate au cititor
(`vtable[1]`, 1–13 KB fiecare), dar există doar 7 funcții de scriere distincte; pentru toate cele 174 de tipuri
server → client văzute în replay, `vtable[0]` e un ciot de 16 octeți. Serverul trebuie deci să scrie pachetele cu
inversul cititoarelor lui Riot; fiecare scriitor se poate verifica trecând pachetul prin cititorul original din
emulator.

Straturile serverului și ce știm despre fiecare:
1. transportul (UDP propriu al lui Riot, salut cifrat): necunoscut, codul localizat;
2. intrarea în meci (versiune, listă de jucători, încărcare, apariție): nu apare în replay-uri (un replay ține doar
   ce primește un spectator); de citit din cod. Primul cadru-cheie al replay-ului arată starea de care are nevoie
   clientul la început (3203 pachete, 64 de tipuri);
3. fluxul de joc server → client: 174 de tipuri, toate citite în clar; lipsesc scriitoarele;
4. comenzile jucătorului client → server: nestudiate;
5. logica de joc: serverul nostru de acum (valuri, turnuri, abilități), care ar hrăni stratul 3.

### Transportul complet și primul pachet Riot primit de client (2026-10-04, `server/lnp_server.py`) [măsurat]

Serverul de test (Python) vorbește acum protocolul de transport al clientului 13.3 cap-coadă; clientul despachetat
se conectează, primește pachetul 574 din replay, afișează lista celor 10 jucători reali și încarcă meciul.

Ce s-a citit în cod și s-a verificat pe client (straturile, în ordinea primirii):
- pachet cu număr > 0: ține conexiunea în viață (rva 0x2e24f7; altfel deconectare după `Timeout` 8000 ms);
- pachet cu bitul de sus al numărului setat = confirmare: număr = −(ultimul primit), după octetul de steag vine un
  u64 cu bitul k = pachetul (ultimul − k) primit (construit la rva 0x2ee8a0, citit la rva 0x2ed360). Clientul își
  începe masca cu toți biții 1. Verificat: clientul scrie `PacketAck ... received` și `MessageAck ... received`;
- octetul de steag ≠ 0: corp comprimat zstd, cel mult 1100 de octeți după decomprimare (rva 0x2e2020);
- corpul = mesaje una după alta (rva 0x2e1da0, antetul la rva 0x2dcd40): `u16 w` (lungime = w >> 3; bit0 fragment;
  bit1 număr = precedentul + 1; bit2 canal = precedentul), `[u8 canal]`, `[u16 număr]`,
  `[u16 id fragment, u8 câte fragmente, u8 indexul]`, apoi pachetul de joc `[u16 id][u32 net id][corp]`;
- **fragmentele**: fiecare fragment are numărul lui de mesaj (consecutive), iar mesajul reasamblat ia numărul din
  câmpul „id fragment”, care trebuie să fie numărul de *după* ultimul fragment. Cu id = primul fragment, stratul de
  ordonare (rva 0x2e0a00) aruncă mesajul întreg ca vechi;
- canalele 1–6 (rva 0x34f340): 2 = nesigur și neordonat; celelalte sigure;
- mesajele ajung la joc prin coada de evenimente a aplicației: observatorul rva 0x2e0cd0 le pune în coadă, iar
  clientul de rețea al jocului (rva 0x370810, în fiecare cadru) o golește prin rva 0x2dbdc0 → 0x2ec600, care dă
  mesajele callback-ului de la +0x20c (vtable rva 0x1581c88) → dispecerul de pachete.

Fluxul conexiunii [măsurat]: clientul trimite pachetul 1 (37 octeți, canal 1) și 279 la 2 s (canal 4). Serverul îi
trimite 574 (lista jucătorilor, 14 930 de octeți, din replay, canal 1, 15 fragmente). Clientul scrie
`Game Info Received`, lista celor 10 jucători (Darius, Nidalee, Talon, Kalista, Alistar / Jax, LeeSin, Azir, Jhin,
Blitzcrank), `Game Server Connection Established after 0.020 seconds`, încarcă harta și campionii și ajunge la
`Start Main Loop` (6 s). Apoi trimite 362, 527 și 22 (fără corp) = a terminat încărcarea; în timpul încărcării
trimite 205 pe canalul 2.

Fluxul replay-ului către client [măsurat]: `lnp_server.py --replay-574 --stream <rofl>` trimite, după 527, toate
pachetele chunk-urilor în timp real, pe canalele lor. 7616 mesaje primite în 34 s de joc, fără nicio eroare. Dar
clientul rămâne pe ecranul de încărcare (captură prin buretele GPU): lipsește pachetul „start joc”, care nu există
în replay (spectatorul intră după start). Ascultătorul conexiunii (rva 0x3554e0) mai tratează 545, 603, 663, 697,
719, 739, 743, 760 — candidații pentru el.

Rulare (≤ 40 s, fereastra clientului apare pe ecran):
`bash tools/run_match.sh 40 <nume> python server/lnp_server.py --replay-574 --stream data/rofl/KR-6363178603_13.3.rofl`.
Sondele din `ba_host.dll` urmează acum și lanțuri de pointeri: `probe.py <rva>=nume@44,0` (de la ecx) sau
`nume@s1,0` (de la al doilea cuvânt de pe stivă).

### Pachetul de start și intrarea în joc (2026-10-04) [măsurat]

Jurnalul unui replay oficial arată trecerile: `GAMESTATE_PREGAME -> GAMESTATE_SPAWN for reason Received StartSpawn
packet` și `GAMESTATE_SPAWN -> GAMESTATE_GAMELOOP for reason Received Game Start Packet`. Șirurile duc (rva 0x2eaac0,
0x2ea8b0) la ascultătorul rva 0x355f80: **StartSpawn = pachetul 10** (fără corp), **Game Start = pachetul 20**
(1 octet). Amândouă stau în **keyframe-ul 1** al replay-ului (3203 pachete: 213, 201, 308, … 10 la poziția 10,
creările de obiecte, … 20 ultimul), nu în chunk-uri. Fișierul are ordinea chunk 1, chunk 2, keyframe 1, chunk 3…;
un spectator primește chunk-urile plus primul keyframe (celelalte servesc doar la derulare) — așa trimite acum
`lnp_server.py --stream`.

Primul start a căzut în inițializarea HUD-ului (rva 0x2ca580: eroul slotului local e nul): 574 îi dăduse clientului
slotul 17, al spectatorului. **Octetul 2 din corpul lui 574 = slotul jucătorului care primește pachetul**, ascuns;
clientul îl decodează la rva 0x36489d (rulat în emulator pe toate cele 256 de valori: 0xef → 17; sloturile 1–11 =
0xfa, 0x3a, 0x7a, 0xca, 0x0a, 0x4a, 0x8a, 0xda, 0x1a, 0x5a, 0x9a). Slotul 0 nu e valid (rva 0x3630c0 cere 1..51) și
lasă clientul fără conexiune. Cu `--slot 1` clientul intră în joc ca Darius: „Welcome to Summoner's Rift”, ceasul
merge, HUD-ul lui Darius, minimapa și chatul cu semnalele reale din meci; în 34 s de joc 10 617 pachete trimise.

`bash tools/run_match.sh 40 <nume> python server/lnp_server.py --replay-574 --slot 1 --stream data/rofl/KR-6363178603_13.3.rofl`

### Darius la click (2026-10-04, `server/lol_packets.py`) [măsurat]

Comanda de mișcare a clientului: 3 click-uri dreapta automate au produs exact 3 mesaje noi, **pachetul 491**
(39 de octeți, canal 1, net id = eroul). Constructorul lui (rva 0x13cbd0, vtable rva 0xfb5970) și scriitorul
(`vtable[0]`, rva 0x94b3d0) rulează în emulator (`server/c2s_emu.py`; `rand()` cere datele firului CRT, rva
0xf7f84c, înlocuite cu un bloc al nostru). Obiectul real, prins cu o sondă pe scriitor în clientul viu și refăcut în
emulator, dă exact octeții capturați. Formatul: octet aleator, octet de steaguri (tipul ordinului 0/1/2 împachetat în
el ca 2/5/7; altfel un octet separat), câmpurile prezente, apoi **drumul calculat de client**: varint lungime +
octeții în ordine inversă, fiecare printr-o substituție (`data/exe133/c2s_491_bytemap.txt`), în același format de
intrare ca 552. Tipul 2 = mișcare; drumul = [poziția eroului, punctul clicat] (ex. din (681, 680) în (1099, 576)).

Pachetul de mișcare **552**: antet `b0 b1 b2 [un octet în plus pentru unele b0]` + varint lungime, apoi bufferul
prin substituția H (`data/exe133/s2c_552_bytemap.json`). Verificat pe 400 de pachete din replay; un 552 real al
lui Darius se reface octet cu octet. Serverul (`--hero 4000001e`) scoate intrările eroului din toate 552-urile
replay-ului (1500 verificate prin cititorul lui Riot, 0 greșeli) și, la fiecare 491 de mișcare, îi trimite un 552 cu
drumul cerut. Rezultat: Darius pleacă din bază și merge unde dai click, iar următorul drum calculat de client pornește
din punctul unde l-am dus noi.

`bash tools/run_match.sh 30 <nume> python server/lnp_server.py --replay-574 --slot 1 --hero 4000001e --stream data/rofl/KR-6363178603_13.3.rofl`

### Abilități: creșterea și primul Q al lui Darius (2026-10-04) [măsurat]

- **Ctrl+Q/W/E/R → pachetul 384** (corp de 1–2 octeți = slotul ascuns). Constructorul (rva 0x535d30) și scriitorul
  (rva 0x94b9e0) rulate în emulator dau Q = `e5` (identic cu captura), W = `e0`, E = `e6`, R = `e47f`.
- **Răspunsul = 676** (câmpuri în clar: slot, 1, nivelul nou, 0). În spectator 606 = nivelul campionului (nivel nou,
  +1 punct). Corpurile 676/606 pentru fiecare combinație, luate din replay:
  `data/exe133/s2c_676_606_bodies.json`. Keyframe-ul 1 conține câte patru 676 per erou (inițializarea
  abilităților); acelea trebuie păstrate, se scot doar cele din timpul jocului.
- Cu Q la nivel 1, clientul tot refuza („You cannot cast that right now!”): biții de lansare vin de la server prin
  replicare, **595 grupul 0 bitul 3 = `mReplicatedSpellCanCastBitsLower1`** (numele variabilelor replicate, în
  ordinea înregistrării, la rva 0x17a490: mGold, mGoldTotal, mMinimumGold, CanCastBits...). Valoarea din replay
  0x2030 = biții 4, 5 (Flash/Teleport) și 13 (Recall); Q = bitul 0. 595 pe fir: `b0 b1` + varint lungime (prin M) +
  bufferul inversat prin M (`s2c_595_bytemap.json`) + 6 octeți de sincronizare; verificat pe 3000 de pachete.
  Serverul scoate grupul 0 al eroului din 595-urile replay-ului și trimite propriul 595 cu biții abilităților
  învățate.
- După asta **Q trimite pachetul 16** (35 de octeți, cererea de lansare). Răspunsul e deocamdată cel al serverului
  Riot la primul Q al lui Darius din replay (113,0 s: 49 lansarea, 271, 65 animația, 693; +0,76 s: 522, 63, 65,
  453, 220, 406 ×10, 271), trimis cu aceleași distanțe în timp. Rezultat: Darius face Decimate în bază (capturi), cu
  „+21” cu monedă copiat din lansarea originală (corectat 2026-10-05: nu e vindecare, e aurul pentru minionul
  0x40000232 omorât de acel Q în replay, pachetul 453). Următorul pas: construirea acestor pachete de server (câmpurile
  lui 49 decodate), apoi W/E/R și atacul.

### Pachetul 79 scris de serverul nostru (2026-10-05, `server/pkt_codec.py`, `create_hero.py`) [măsurat]

79 = crearea unui campion. Funcția clientului care îl tratează (ascultătorul rva 0x355f80, cazul 79 → rva 0x365650)
scrie în jurnal „Spawn Champion Request {ChampionName} [{#SummonerName}] SkinID({SkinID}) NetID({NetID})”.

**Forma cititorului** (rva 0x875990, citit în cod și reluat în emulator): după `[u16 id][u32 net id]` vin 6 octeți
de antet = 48 de biți (citiți prin rva 0x91cae0, ordine little-endian a biților), apoi câmpurile, mereu în aceeași
ordine. Pentru fiecare câmp, 1–3 biți din antet îi dau „modul”: o constantă (0, 1, 2, −1, 1.0, −1.0, 2.0 …, fără
octeți pe fir) sau un fel de a-l citi. Felurile de citire sunt puține și toate trec fiecare octet printr-un tabel:
- **fix**: n octeți, fiecare într-un octet al câmpului (ordinea poate fi inversată: vec3 citit de la z la x, float big-endian);
- **varint**: grupuri de 7 biți, cel mic primul;
- **text**: lungime varint, apoi octeții în una din trei ordini: înainte, invers, sau de la capete (0, L−1, 1, L−2…,
  cu un alt tabel pentru octetul din mijloc);
- un octet poate fi respins de cititor după citire (slotul jucătorului: doar 1..51).
Mai multe moduri citesc la fel (ex. net id: modurile 1, 2, 4, 5, 6, 7); bitul 47 nu e folosit; bitul 46 e un bool
testat direct în cod.

**`pkt_codec.py learn 79`** învață singur toate modurile tuturor câmpurilor, rulând cititorul Riot în emulator pe
corpuri construite de el (fiecare octet de pe fir încercat cu toate cele 256 de valori; text: lungimi 1–7, ordinea
dedusă) → `data/exe133/codec/79.json`; `show 79` le afișează. Scriitorul (`encode`) alege ca serverul: un mod
constant când valoarea e chiar constanta lui, altfel primul mod citit. Instrumentul nu are nimic specific lui 79 în
afară de bitul testat direct (`INLINE`), deci se aplică la fel celorlalte pachete.

**Verificare (`pkt_codec.py check 79 200`):** cele 10 pachete 79 ale replay-ului, decodate și rescrise cu modurile
lor, ies **identice octet cu octet**; rescrise cu alegerea noastră de moduri, cititorul Riot le citește cu aceleași
câmpuri (10 din 10); 200 din 200 de pachete cu valori aleatoare (toate modurile, texte de 0–60 de octeți) sunt citite
înapoi identic.

**Câmpurile** (`create_hero.py`, ce face funcția clientului cu ele):

| offset | nume | valoare în replay | ce face clientul |
|---|---|---|---|
| +0x18 | net_id | 0x4000001e.. | NetID din jurnal, obiectul eroului |
| +0x20 | champion | „Darius” | ChampionName; preîncărcare (rva 0x2e92d0) și creare (rva 0x1a2d90) |
| +0x30 | summoner | numele coreean | SummonerName (un bot primește „game_bot_<campion>”) |
| +0x2c | slot | 1..10 | slotul jucătorului, 1..51; egal cu slotul local = eroul tău |
| +0x68 | team_order | 1 / 0 | 1 → echipa 100, 0 → echipa 200 |
| +0x64 | skin | 15, 6, 29… | SkinID |
| +0x44 | position | (554, 171, 581) / (14180, 179, 14271) | locul creării (fântâna) |
| +0x0c | facing | (−0.8, 0, −0.6) / (0.8, 0, 0.6) | direcția, pusă pe erou la +0x1bec |
| +0x58 | mastery | 4..7 | merge în codul MasteryBadge (rva 0x237bc0) |
| +0x52 | bot | 0 | numele devine „game_bot_<campion>” |
| +0x1c | state | 0 | 2 → rva 0x1a7cf0 (folosește „Death”) cu death_a, death_b; 1 → rva 0x1a7f40 |
| +0x3c, +0x54 | death_a, death_b | 0 | cele două float-uri pentru state = 2 |
| +0x5c | until | −1.0 | un timp de joc: cât e în viitor, se aplică flag_60 și flag_51 |
| +0x60, +0x51, +0x61, +0x0a | flag_* | 0, 0, 1, 1 | trimise la rva 0x178850, 0x11ef60, 0x1b7d10, membrul +0x3e08 |
| +0x2d, +0x53 | value_2d, value_53 | 1, 64 | +0x10 în obiectul de la vtable[0xcc]; al 8-lea argument al creării |
| +0x40, +0x50, +0x69 | | 0 | +0x40 citit, folosire neurmărită; +0x50 și +0x69 necitite de funcție |

Interpretări neverificate încă: state = 2 ar fi „mort la conectare” cu timpii morții; mastery = nivelul de măiestrie.

**În client:** `lnp_server.py --own-79` trimite toate cele 10 creări construite de noi din
`data/exe133/s2c_79_heroes.json` (câmpuri cu nume); `--set79 "1.skin=0"` schimbă un câmp. Cu skinul lui Darius
schimbat 15 → 0, clientul intră în joc (GAMELOOP) și Darius apare în skinul clasic, cu portretul clasic în HUD
(captura `data/exe133/match_own79skin/frames/compare_skin15_vs_skin0.png`: stânga 79 din replay, dreapta al
nostru). Capturi din meci: `tools/match_shots.sh <nume> <secunde...>` lângă `run_match.sh`.

`bash tools/run_match.sh 34 <nume> python server/lnp_server.py --replay-574 --slot 1 --hero 4000001e --own-79 --set79 "1.skin=0" --stream data/rofl/KR-6363178603_13.3.rofl`

### Pachetul 574 scris de serverul nostru (2026-10-05, `server/pkt_tree.py`, `pkt_schema.py`, `game_info.py`) [măsurat]

574 = informațiile meciului: clientul scrie „Game Info Received”, apoi câte o linie „ROST” pe jucător (echipă,
nume, campion, skin, rol, PUUID). Spre deosebire de 79, e imbricat: obiectul pachetului conține alte obiecte, fiecare
cu vtable-ul lui și cititorul lui la `vtable[1]`, de aceeași formă (antet de biți de mod, apoi câmpuri).

**Structurile** (10 tipuri, 116 câmpuri; cititorul fiecăruia rulat separat în emulator):
- rădăcina (rva 0x88d530, 8 câmpuri): +0x14 = slotul clientului care primește pachetul (1..51; replay-ul: 17 =
  spectator), +0x28 = lista de înregistrări de jucător, +0x34 = configurarea meciului, +0x14c = lista din joc;
- înregistrarea de jucător (rva 0x908710, 18 câmpuri): id-ul summonerului (u64), PUUID, numele, iconița, slotul,
  JSON-urile de profil (challenges, regalia);
- configurarea (rva 0x8feb90, 35 de câmpuri): coada („Worlds_TrophyOnly”), tipul („MATCHED_GAME”),
  „teambuilder-match-<id>”, versiunea („Version 13.3.491.6222 [PUBLIC]”), platforma („KR”), modul („CLASSIC”),
  mutatorii, liste de perechi de numere (rva 0x8fe8b0), două blocuri binare mari (rva 0x907ba0, „PTCH… PROP…”);
- lista din joc (rva 0x907980 → înregistrări rva 0x902a30, 39 de câmpuri): echipa (100/200), slotul, campionul,
  skinul, rolul („TOP”…), nivelul de măiestrie (același cu +0x58 din 79), rangul și divizia;
- mai mici: rva 0x90a970, 0x902670, 0x907bf0.

**Felurile de câmp noi față de 79** (toate învățate prin încercări în emulator, nimic scris de mână):
- *liste* (`seq`): un număr varint, apoi elementele — texte, numere varint, octeți validați (o listă de sloturi
  acceptă doar 1..51) sau structuri — în ordinea înainte, invers sau de la capete (0, n−1, 1, n−2…);
- *structuri încorporate*: modul constant copiază o instanță implicită (nu se citește nimic), modul citit rulează
  cititorul sub-structurii;
- *biți de mod testați direct în cod* (fără rva 0x91cae0): găsiți schimbând fiecare bit din antet și văzând care câmp
  își schimbă primul comportamentul;
- cititorii de structuri se recunosc singuri: o funcție care citește de pe fir și primește cursorul ca prim argument
  (după `this`) e cititor; dacă îl primește ca al doilea (după destinație) e o funcție ajutătoare.

Observat pe drum: în modul „citit”, o listă cu 0 elemente face bucla lui Riot să citească de la adresa −12 (pornește
de la ultimul element fără să verifice lista goală) — serverul trimite lista goală prin modul constant.

**Verificare (`pkt_schema.py check 574 40`):** pachetul din replay, decodat și rescris de noi, e citit de cititorul
Riot cu exact aceleași valori (al nostru are 14 999 de octeți față de 14 930: alegem alte moduri, la fel de
valide); 40 din 40 de variații aleatoare (texte, numere, liste, jucători scoși/dublați/schimbați) sunt citite
înapoi identic. Ordinea a două liste pe care replay-ul nu o arăta (2 elemente identice) a fost verificată separat cu
3 elemente diferite (`pkt_schema.py orders 574`): `rev` și `ends`.

**Rămase neînvățate (nefolosite de replay):** două tipuri de structuri care nu apar niciodată cu conținut
(rva 0x907ee0 la +0x5c în înregistrarea de jucător, rva 0x8fe400 ca elemente ale listei +0x58 din configurare):
scriitorul le trimite doar în modul implicit / goale.

**În client:** `lnp_server.py --own-574 [--set574 "1.name=BattleArena;1.skin=0"]` trimite 574 construit de noi din
valorile replay-ului (`data/exe133/codec/574.values.json`), cu slotul local pus prin codec (nu mai e nevoie de
tabelul `SLOT_BYTE`). Cu `--own-79` împreună: jurnalul clientului scrie
`'BattleArena' **LOCAL** - Champion(Darius) SkinID(0)`, intră în GAMELOOP, iar Darius apare în skinul clasic
(`data/exe133/match_own574/frames/s26.png`).

`bash tools/run_match.sh 32 <nume> python server/lnp_server.py --replay-574 --own-574 --set574 "1.name=BattleArena;1.skin=0" --slot 1 --hero 4000001e --own-79 --set79 "1.skin=0" --stream data/rofl/KR-6363178603_13.3.rofl`

Învățarea (`pkt_schema.py learn 574`) durează ~2 ore și se reia de unde a rămas (structurile învățate sunt păstrate
în `data/exe133/codec/574.tree.json`).

### Pachetul 49 (lansarea unei abilități) scris de serverul nostru (2026-10-05) [măsurat]

49 = o lansare (5198 în replay). Imbricat, 4 tipuri de structuri (`data/exe133/codec/49.tree.json`): rădăcina
(rva 0x850f50, 3 câmpuri) → informația lansării (rva 0x813050, 32 de câmpuri) → lista țintelor (elemente rva
0x817db0) și o sub-structură (rva 0x818170, 8 câmpuri).

Valorile Q-ului lui Darius din replay (113,0 s), citite din câmpuri: +0x3c și +0x5c = net id-ul lui Darius
(lansatorul / proprietarul), +0x4c și +0x60 = poziții (x, y, z), +0x78 = 113,0 (timpul lansării), +0x28 = o
direcție, +0x1c și +0xc4 = alte net id-uri (0x4000059a, 0x40000599); în sub-structura +0x8c: „Darius” (+0x24),
skinul 15 (+0x18), 113,2 (+0x10), un hash (+0x14, același ca +0xbc). Acestea sunt citiri ale valorilor, nu ale
codului care le folosește (funcțiile lui 49 nu au texte).

**Verificare:** pachetul din replay rescris de noi: citit identic; 40/40 variații aleatoare; **300 din 300 de
pachete 49 luate din tot meciul** (`pkt_schema.py many 49 300`): rescrise și citite înapoi identic. Rescris cu
modurile și biții nefolosiți ai replay-ului, iese identic octet cu octet (`replay_modes.py`).

**În client:** `lnp_server.py --own-49` construiește 49-ul din răspunsul la Q (din valorile replay-ului, cu timpul
lansării pus la ora jocului și skinul eroului nostru); `--auto-q <secundă>` face serverul să crească și să lanseze Q
singur (fără taste: scriptul de taste nu mai ajungea în joc când altă fereastră era în prim-plan, deci l-am
oprit). Dovada că 49-ul nostru e citit: cu sonde pe cititorul lui (rva 0x850f50) și pe cele două funcții care îl
tratează (rva 0x546bc0, 0x164ae0), datagrama noastră de 134 de octeți sosește la tick 175242812, iar la 175242828
rulează toate trei (`data/exe133/match_q49probe/ba_net.log`). Darius face Decimate (capturi
`match_q49own/frames`). Schimbarea skinului 15 → 0 în 49 nu se vede în efectul lui Q.

**Ce a mai învățat instrumentul pe drum** (aplicat și la 574, reverificat):
- biți de mod care contează doar pentru unele valori ale vecinilor (un mod de 3 biți ale cărui valori 1..7 se citesc
  la fel, iar 0 e respins): fiecare bit e acum încercat și pe fundaluri aleatoare ale celorlalți biți. Așa au ieșit
  corect biții 19–21 și 8–10 din rva 0x818170 (codul: `shr al, 3; and al, 7` pe octetul 2);
- un vector de 3 float-uri are aceeași mărime (12 octeți) ca un text: text/listă doar când primul cuvânt arată în
  heap sau e adresa textului gol (0x01532fb2);
- valorile modurilor constante ale textelor erau citite după ce alte rulări schimbaseră memoria (gunoi): acum
  fiecare e recitită dintr-o rulare a ei (`pkt_schema.py consts`). După reparare, 574 rescris are exact mărimea
  celui al lui Riot (14 930 de octeți);
- pasul dintre elementele unei liste cu un singur element în replay se măsoară cu două copii (`orders`).

### Pachetele 271, 65 și 693 scrise de serverul nostru (2026-10-05) [măsurat]

Toate trei sunt plate (o singură structură): 271 (rva 0x83b7c0, 6 câmpuri), 65 (rva 0x8ab170, 10 câmpuri), 693
(rva 0x8497d0, 16 câmpuri; o listă al cărei tip de element nu apare cu conținut în replay: scrisă doar goală).

Ce arată valorile din răspunsul la primul Q al lui Darius (citite din câmpuri):
- **65 = joacă o animație**: +0xc = numele animației („Spell1Windup” la lansare, „Spell1” după 0,76 s), +0x1c = 1,0;
- **271 = cooldown-ul unei abilități**: la lansare totul 0; la +0,76 s, +0x14 = +0x18 = 9,0 (Q la nivelul 1 are 9 s);
  +0x10 = slotul (0 = Q);
- **693**: net id-ul lui Darius (+0x44), un hash (+0x10 = 0x0ccd11a4), 15 (+0x15), −987,8 (+0x2c, aceeași valoare ca
  +0x18 din 49) — semnificație neverificată.

**Verificare (`pkt_schema.py check <id> 40` și `many <id> 20000`):** pentru fiecare, pachetul din replay și 40/40
de variații aleatoare se citesc identic; și **toate pachetele din meci**: 11 275 / 11 275 (693), 6 337 / 6 337 (271),
4 887 / 4 887 (65) rescrise și citite înapoi identic.

**În client:** `lnp_server.py --own-cast [--q-cooldown 3]` rescrie toate pachetele învățate ale răspunsului la Q
(49, 271, 65, 693) din valorile replay-ului; restul (406 ×10, 522, 63, 453, 220) vin încă din replay. Cu cooldown-ul
din 271 pus la 3 s, HUD-ul arată Q-ul 3 → 2 → 0,2, față de 9 → 8 → 7 cu 271 din replay
(`data/exe133/match_castown/frames/compare_cooldown.png`, Q lansat de server cu `--auto-q 10`).

### Pachetele 406, 522, 63, 453 și 220: tot răspunsul la Q scris de noi (2026-10-05) [măsurat]

Toate cinci sunt plate: 406 (rva 0x8af5c0, 4 câmpuri), 522 (rva 0x84cdb0, 3), 63 (rva 0x8ca910, 4), 453 (rva 0x8f4e10,
4), 220 (rva 0x8503e0, 4). **Verificare:** pachetul din replay și 40/40 de variații citite identic; și toate
pachetele lor din meci: 850 / 850 (406), 10 988 / 10 988 (522), 5 925 / 5 925 (63), 2 420 / 2 420 (453),
5 873 / 5 873 (220).

**453 = aur primit** (observația utilizatorului, confirmată în replay): +0xc = suma (float), +0x10 = cine primește
(Darius), +0x18 = unitatea de la care vine. La 113,759 s, 0x40000232 primește lovituri (263) și moare (61) în aceeași
clipă cu 453 de 21: minionul omorât de acel Q. Sumele din 453 în meci: cel mai des 14 și 21 (apoi 20, 13), 300 de 50
de ori. Corectat mai sus: „+21” nu era o vindecare.

Celelalte, doar din valori (neverificate): 522 are același hash ca 693 (0x0ccd11a4) și 15 — par perechea care
pune / scoate un efect pe erou; 220 = un hash (0x0d318fd1) și 2; 63 = un hash (0xa742331b); cele 10 × 406 din Q sunt
identice (1, 0x34).

**În client:** cu `--own-cast` serverul scrie acum toate cele 20 de pachete ale răspunsului la Q (9 tipuri: 49, 271,
65, 693, 522, 63, 453, 220, 406), din valorile replay-ului; `--q-gold 77` schimbă suma din 453: pe ecran apare „+77”
cu monedă în loc de „+21” (`data/exe133/match_castown2/frames/compare_gold.png`).

### Pachetele 263 (daune) și 61 (moarte) scrise de serverul nostru (2026-10-05) [măsurat]

263 e plat (rva 0x8f5490, 8 câmpuri); 61 are o sub-structură (rva 0x8516a0 → 0x82f3d0; 5 + 5 câmpuri).
**Verificare:** toate pachetele din meci: **41 956 / 41 956** (263) și 3 446 / 3 446 (61) rescrise și citite identic;
40/40 de variații fiecare.

Din valorile minionului 0x40000232, omorât de primul Q al lui Darius:
- **263 = daune**: +0xc = ținta, +0x14 = suma (12 și 24 de la minioni, **127,4 de la Q-ul lui Darius**), +0x20 = sursa,
  +0x1c = 4, +0x1d = 1 de la minioni / 0 de la Darius (sens neverificat);
- **61 = moarte**: +0x2c = ucigașul (Darius); sub-structura +0x10 are 0x11 și 0xc922 (sens neverificat).

**În client:** `--q-kill <net id>` (cu `--own-cast`): la Q, serverul trimite 263 și 61 construite de noi din cele
ale minionului, cu ținta schimbată. Cu Alistar (0x40000022, aliat în bază): apare „127” deasupra lui, bara de viață
se sparge, iar Alistar rămâne mort pe jos (`data/exe133/match_qkill/frames/qkill_strip.png`). Viața lui din
replicare (595) vine încă din replay.

### Pachetul 595 (replicarea) scris de serverul nostru, valorile pe nume (2026-10-05) [măsurat]

**Învelișul** (cititorul rva 0x8559c0, învățat cu `pkt_schema.py learn 595`): +0xc = bufferul (un text: tabel de
octeți, scris de la coadă), +0x18 = numărul de unități din buffer (34 în primul 595), +0x1c = un timp de joc (23,02 s),
+0x20 = un contor (452). Pachetul din replay și 40/40 de variații se citesc identic; toate cele 149.108
pachete 595 din meci: identice.

**Conținutul** (formatul din `replication.py`): pentru fiecare unitate grupuri (bit în masca primară), în fiecare
grup valori (bit în masca secundară). **Ce valoare e fiecare (grup, bit)** [citit în cod]: fiecare clasă de unitate
își înregistrează variabilele la construcție: rva 0x1a2ff0 face managerul peste 8 tabele de grup (obiecte statice), apoi
fiecare variabilă intră cu `mov ecx, <tabela>; push <nume>; push <variabilă>; push <proprietar>; call rva 0x189df0 /
0x19ccc0`. Funcția de înregistrare scrie în tabelă: +0 numărul, +8+4i deplasamentul variabilei, +0x88+4i numele,
iar la +4 un bit per variabilă = **float (1) sau întreg împachetat (0)**. Bitul din 595 = indicele i. Tabelele se
umplu la construirea primei unități din clasă, deci le citim dintr-o imagine luată din clientul nostru la secunda
~78 de joc (`client-src/exe_image_match78.bin`, minionii ieșiți): `repl_names.py` →
`data/exe133/repl_names.json`.

| clasa (înregistrare) | grupuri folosite |
|---|---|
| erou (rva 0x17a490) | 0: mGold, mGoldTotal, mMinimumGold, biții de lansare, ManaCost_0..3…; 1: mEvolvePoints…; 2: ActionState, StatusFlags, mBaseAttackDamage, mArmor…; 3: penetrări, regenerări, mAbilityHasteMod…; 4: mFlatBaseArmorMod, mFlatBaseSpellBlockMod; 5: mHP, mMaxHP, scuturi, mExp, mPAR (mana), mMaxPAR, mMoveSpeed, mLevelRef… |
| minion de culoar (rva 0x1cdd20, tabelele alese de un bit; varianta 0) | 2: mLifetime, mPAR, ActionState, mArmor…; 3: **mHP**, mMaxHP…; 5: mMoveSpeed, mPercentDamageToBarracksMinionMod…; 7: mIsTargetable… |
| turn (rva 0x1ce2a0) | 2: mMaxMP, mMP, ActionState…; 5: **mHP**, mMaxHP, …, mMoveSpeed; 7: mIsTargetable, mIsTargetableToTeamFlags, mPalisadesCount, mMaxPalisadesCount (plăcile) |
| structuri (rva 0x770d60 / 0x770f40 / 0x7710a0) | 2: mHP, mMaxHP, scuturi, StatusFlags; 7: mIsTargetable… |

**Verificare:** 200 000 de actualizări de unități din replay (94 424 de eroi, 93 896 de minioni, 11 344 de turnuri,
336 de structuri), decodate pe nume și re-encodate de `repl_codec.py`: identice octet cu octet, nicio pereche
(grup, bit) necunoscută. Un 595 construit de noi (Darius: mGold 9999, mHP 300, mMaxHP 732, mLevelRef 5) e citit corect
de cititorul Riot.

**În client:** `lnp_server.py --hero-set "mGold=9999"` trimite la fiecare 2 s un 595 al nostru pentru erou, cu
valorile pe nume: HUD-ul arată **9999** de aur (`data/exe133/match_hero595/frames/gold_hud.png`). Măsurat: cu
contorul +0x20 = 1 valoarea nu apare, cu 1 000 000 apare (pare o verificare de „pachet mai vechi”; necitită în cod).

Rămase: varianta 1 a minionului (alt fel de unitate AI) și clasa rva 0x1ce4c0 au tabelele goale în imaginile noastre
(nicio unitate de felul lor până la secunda 78); felul de unitate al fiecărui net id îl alegem încă după interval
(eroi 0x4000001e..27, turnuri sub, minioni peste, structuri 0xff…).

### Un campion care nu e în replay: Garen ca erou local (2026-10-05) [măsurat]

Pasul 1 din planul „orice campion, orice abilitate”. Fără nicio modificare în client, doar pachete construite de noi:
- **574**: în lista din joc (rva 0x902a30), pe slotul 1: numele campionului (+0x94, +0xd8), skinul (+0x84) și **id-ul
  numeric al campionului (+0x80)**: în replay Darius 122, Nidalee 76, Kalista 429…; același număr stă în fișierul
  personajului (câmpul {bc169602} din `garen.bin` = 86, din `darius.bin` = 122);
- **79**: numele campionului „Garen”, skin 0;
- **259 = o abilitate pusă pe un slot** (învățat cu `pkt_schema.py`: rădăcina rva 0x83fbc0 → sub-structura rva
  0x819740; +0xc+0x7 = slotul 0..3, +0x18 = numele abilității ca text). În keyframe-ul replay-ului sunt patru 259
  pentru Darius: DariusCleave, DariusNoxianTacticsONH, DariusAxeGrabCone, DariusExecute (exact numele din
  `darius.bin`). Toate cele 6 330 de pachete 259 din replay se rescriu identic. Pentru Garen: GarenQ, GarenW, GarenE,
  GarenR (din `garen.bin`).

Rezultat: clientul scrie `'BattleArena' **LOCAL** - Champion(Garen)`, intră în joc cu modelul, portretul și pasiva lui
Garen. Doar cu 574 + 79, iconițele Q/W/E/R erau negre; cu id-ul în 574 tot negre; cu cele patru 259 ale noastre apar
iconițele lui Garen (`data/exe133/match_garen2/frames/hud.png`). Rămas greșit: viața (732) și restul valorilor
replicate vin încă din 595-urile lui Darius din replay.

`bash tools/run_match.sh 30 <nume> python server/lnp_server.py --replay-574 --own-574 --set574 "1.champion=Garen;1.champion_id=86;1.skin=0;1.name=BattleArena" --slot 1 --hero 4000001e --own-79 --set79 "1.champion=Garen;1.skin=0" --hero-spells "GarenQ,GarenW,GarenE,GarenR" --stream data/rofl/KR-6363178603_13.3.rofl`

### Pasul 2: cererea de lansare a clientului (16) citită de server, câmpurile lui 49 (2026-10-05) [măsurat]

**16 (client → server).** Pentru pachetele clientului, cititorul din vtable e un ciot (rva 0x146910:
`xor al, al; ret 8`); clasa lui 16 e găsită după constructorul care pune id-ul (`mov eax, 0x10` + vtable-ul de bază
rva 0xfb357c): constructorul rva 0x5359a0, vtable rva 0x15a04ac, scriitorul rva 0x94a990. Scriitorul are forma
cititoarelor (3 octeți de antet cu modurile câmpurilor, apoi câmpurile) și alege între modurile echivalente cu
`rand() % 6` (starea lui rand la +0x18 în blocul per-fir al CRT, rva 0xf6ab25).
`server/c2s_codec.py` învață decodorul din scriitor: construiește obiectul cu valorile noastre (scrise în câmp
imediat după ce constructorul îl pune la 0 și înainte de bucla care îl ascunde), rulează scriitorul cu sămânța
noastră și deduce modurile, tabelele de octeți și ordinea câmpurilor (`data/exe133/codec/c2s_16.json`).
Verificare: 300 din 300 de pachete scrise de scriitorul clientului din valori și semințe aleatoare sunt citite înapoi
identic.

Câmpurile, din cererile capturate în teste: +0xc = net id-ul lansatorului, +0x10 = punctul țintit (x, z), +0x1c =
poziția lansatorului (554, 581 la fântână), **+0x24 = slotul** (Q 0, W 1, D 4), **+0x34 = hash-ul ELF al numelui
abilității** (Q: `elf("dariuscleave")` = 0x0f4a2805; W: `elf("dariusnoxiantacticsonh")` = 0x054fdd98; D:
`elf("summonerhaste")` = 0x064acc95), +0x18 = 5 la Q / 0 la celelalte (sens necunoscut), +0x28 = (0, 0), +0x30 = 0.
`lnp_server.py` scrie acum la fiecare 16 slotul, abilitatea, ținta și poziția.

**49 pe 40 de lansări diferite** (8 campioni, Q/W/E/R, Recall, atacuri speciale;
`data/exe133/codec/casts49_sample.txt`). Sigure (verificate cu numele / valorile cunoscute):
- +0xc+0x8c+0x14 (= +0xc+0xbc) = hash-ul ELF al abilității (Recall: 0x078b982c = `elf("recall")`);
- +0xc+0x8c+0x24 = numele personajului (inclusiv „nidaleecougar” în forma de puma); +0xc+0x8c+0x18 = skinul (Nidalee
  6, Azir 14, Talon 29, Alistar 19 — aceleași ca în 574);
- +0xc+0x34 = slotul (0–3 Q–R, 13 = Recall pentru toți campionii, altele 12, 45, 50…).
Deduse din valori, neverificate în cod: +0xc+0x80 = un număr de ordine al lansărilor (crește), +0xc+0x84 = costul în
mana (Darius Q 30, Nidalee 50, Talon 55, Blitzcrank 100), +0xc+0xc8 = cooldown-ul (Darius Q 9, Lee Sin 10/11,
Nidalee 6, Recall 0), +0xc+0x24 = timpul de pregătire (0,25 / 0,5), +0xc+0x58 = durata lansării (Recall 8,5),
+0xc+0x8 = lista țintelor (net id-uri), +0xc+0x4c / +0x60 = poziții.

### Pasul 3: orice abilitate a eroului, de la server (Garen Q/W/E/R)

`lnp_server.py --hero-spells "GarenQ,GarenW,GarenE,GarenR"`: la un 16 (sau la `--auto-cast "10:0;14:1;18:2;22:3"`,
fără taste) serverul răspunde cu propriile pachete, construite peste primul Q al eroului din replay ca șablon:
- **49** cu hash-ul ELF al abilității (+0xc+0x8c+0x14 și +0xc+0xbc), personajul și skinul eroului, slotul, cooldown-ul și
  mana rangului (din fișierele jocului, `spell_info.py` prin `bainfo spells`, linia nouă „ranks” = valorile pe rang),
  timpul de pregătire (cast time din date), timpul de joc, pozițiile și direcția, net id-uri noi pentru lansare;
- **65** cu animația abilității din date (Garen: Spell1, Spell2, —, Spell4; E nu are animație în date);
- **271** cu cooldown-ul slotului, după timpul de pregătire.

Rezultat în client (cadre în `data/exe133/match_garencast/frames`, `match_garenr/frames`): Garen face Q, W și R
(pozele se văd), iar HUD-ul arată cooldown-urile 8 (Q), 23 (W), 9 (E), 120 (R) care scad. R la nivelul 1 nu apare pe HUD
(slotul rămâne negru, ca în joc: R cere nivelul 6); cu `--hero-set "mLevelRef=6"` (595 al nostru) portretul și bara arată
nivelul 6 și R pornește cu 120 pe HUD.

Ce lipsește (pasul 4): efectele și logica abilităților — Q (atacul întărit, viteza), W (scutul), E (rotirea, care în
joc vine dintr-un buff, nu din animația lui 49), R (lovitura de execuție); daunele, buff-urile și rachetele. Viața și
mana eroului vin încă din 595 al lui Darius din replay (652/732). Timpul de pregătire 0 pentru Q/W/E e valoarea din
date; Darius Q are 0,234 în replay față de 0 în date, deci sensul exact al câmpului +0xc+0x24 rămâne de verificat.

### Pasul 4, bucla 1: buff-urile (693, 522, 220) și animația ținută (65 +0x24) (2026-10-05) [măsurat + dedus]

**Toate pachetele 693, 522, 220, 63 și 65 din meci decodate** (`tools/pkt_dump_all.py <id>` →
`data/exe133/codec/<id>.all.jsonl`), iar hash-urile citite cu un dicționar construit din fișierele jocului
(`server/name_hashes.py`: toate textele din binurile campionilor din replay + Garen, Global, Map11, hash-uite ELF
și FNV-1a; 4,1 M intrări). Ce reiese (măsurat pe valori):
- **693 = buff pus**: obiectul = unitatea care îl primește, +0x10 = **hash-ul ELF al numelui buff-ului** (DariusHemo,
  KalistaESlow, Stun, Recall…), +0x44 = sursa, +0x15 = slotul buff-ului pe unitate (0..65 în meci), +0x18 = durata (s),
  +0x34 = tipul (Stun 5, Stealth 6, încetiniri 11, DariusHemo 13, haste 15 — aceleași valori pentru toți
  campionii), +0x16 = 0 / 2 / 3, +0x1d = numărul de stack-uri la pornire, +0x2c = un hash al „familiei” sursei
  (Darius 0x05f176c4, Kalista 0x92ff8858, rune 0xa5ab3717, obiecte 0xbdff53d5; numele lui nu se găsește cu ELF, FNV,
  CRC32, sdbm sau djb2);
- **522 = buff scos**: +0xa = slotul, +0x10 = hash-ul numelui; **220 = stack-uri**: +0xc = numărul, +0x15 = slotul;
- **63** = un nume de animație (FNV: Spell1_Dash, Spell2, Run, Reload…), sens neverificat;
- **65 +0x24 = cât e ținut clipul** (crab_hide 5,0 s, Spell3 al lui Jax 2,25 s, Idle 1,0), +0x31 des 1.

**Efectele vizuale ale abilităților nu vin printr-un pachet cu nume de particule:** scanarea câmpurilor în clar ale
tuturor tipurilor de pachete (`tools/hash_scan.py`, emulatorul cititorului Riot) după hash-uri de nume de
particule nu dă nimic în afară de coincidențe. Animațiile lui Garen au `ParticleEventData` în clipuri, deci
particulele legate de clip pornesc odată cu 65.

**Buff-urile lui Garen** (`server/spell_effects.py`, sursele acolo): numele din scripturile 13.3
(`Scripts.wad`, `data/lua133`: GarenQ → BuffName „GarenQBuff”, GarenQHaste, GarenW, GarenE cu SpellToggleSlot),
duratele din valorile pe rang ale vrăjii (`spell_info.py` citește acum și mDataValues): Q MovementSpeedDuration 1 s
(haste) și AttackWindow 4,5 s, W DRDuration 2 s, E Duration 3 s. Tipul și +0x16 nu sunt în date: luate prin analogie
cu buff-urile pe sine ale lui Jax la lansare (tip 2, +0x16 = 3) și cu haste-urile din meci (tip 15) — **de verificat
cu jocul real**. Rotirea lui E: 65 „Spell3” (clipul parametric al rotirii din graful de animație) ținut 3 s.

**În client** (`data/exe133/match_garenfx2/frames`, `buffbar.png`, `e_strip.png`; cadrele legate de oră prin
linia nouă „capture asked” din jurnalul serverului):
- iconițele buff-urilor apar deasupra portretului, cu cronometrul circular: Q (dispare între +0,8 și +1,5 s =
  haste-ul de 1 s), W (2 s), E (3 s);
- **GarenQBuff (4,5 s) nu apare pe HUD**, deși 693 și 522 lui pleacă (cauză necunoscută);
- Garen se rotește 3 s la E (sabia în altă poziție la +0,4 / +0,8 / +1,5 s), dar **fără efectul vizual al
  rotirii** (Garen_Base_E_Spin există în date; ce îl pornește nu e găsit).

### Cine animă o abilitate: clientul singur sau serverul (2026-10-05) [măsurat]

Întrebarea utilizatorului: exe-ul 13.3 știe toată partea vizuală, serverul doar spune ce abilitate. Măsurat:
- **Test fără niciun 65 de la noi** (`lnp_server.py --no-anim`, `data/exe133/match_garennoanim2/frames/sheet.png`):
  R-ul lui Garen se animă complet singur din 49 (săritura, sabia de lumină care cade din cer); Q, W, E nu.
- **În replay** (toate cele 5198 de 49 decodate, `data/exe133/codec/49.all.jsonl`): doar 1073 din 4016 lansări ale
  campionilor au un 65 în aceeași clipă, iar asta depinde de vrajă, nu de lansare. Regula: câmpul `flags` al vrăjii
  (SpellDataResource) **fără bitul 4** → clientul animă singur (24 din 27 de vrăji: JhinW, RocketGrab, JavelinToss…;
  excepție Alistar R); **cu bitul 4** (vrăji conduse de scriptul serverului) → animația vine de la server: 14 vrăji
  mereu cu 65 (DariusCleave, JaxCounterStrike, Overdrive…), 7 uneori, 8 niciodată (învelișuri / fără animație proprie:
  AzirQWrapper, JaxEmpowerTwo…). Garen: Q, W, E au flags 4, R nu are.
- **Timpii din 49 se calculează din date** (`spell_info.cast_times`, 3355 din 3691 de lansări identice; restul =
  canalizări și 2 cazuri speciale): +0xc+0x24 = `mCastTime`, altfel 0,5 × (1 + delayCastOffsetPercent);
  +0xc+0x58 = max(+0x24, 2,0 × (1 + delayTotalTimePercent)); vrăjile canalizate adaugă durata canalizării (JhinR 11).
  `bainfo spells` arăta greșit 0 la DariusCleave (mCastTime 0,2344 = replay 0,234): `spell_info.raw_fields` citește
  acum câmpurile direct din bin.

Consecință în server: 65 se trimite doar pentru vrăjile cu flags & 4; pentru celelalte, 49 singur ajunge. Ce 65 trimite
serverul real pentru Garen Q/W/E (scriptul lor nu e livrat) nu se poate afla din date: DariusCleave primește
„Spell1Windup” apoi „Spell1”, nu doar mAnimationName.

### Darius W: tot ce trimite serverul real, învățat și rescris (2026-10-05) [măsurat]

**Pachete noi învățate** (`pkt_schema.py learn/many`, toate exemplarele din meci rescrise și citite identic): 721
(489/489), 118 (1201/1201), 465 (1707/1707), 606 (2660/2660), 516 (8024/8024), 71 (4830/4830, învățat pe cel mai lung
pachet: `PKT_LONGEST=1`, primul avea lista goală), 326 (13 960/13 960), 750 (6268/6268), 740 (6086/6086),
568 (7127/7127), 592 (exemplarul de 142 B identic, 40/40 de variații). Sensuri (din valori):
- **592 = atacul de bază**: ținta, slotul vrăjii de atac (45 = DariusNoxianTacticsONHAttack la W), id-ul nou,
  poziția, plus o structură de lansare ca a lui 49 (timpi, poziții, numele vrăjii); 516 îl însoțește (poziția țintei,
  ținta, 2);
- **71 = lista de animații înlocuite** (SPELL2_RUN în loc de RUN / RUN_FAST, SPELL2_IDLE în loc de IDLE1 / IDLE2),
  trimisă crescător (4 pachete) la pornire și descrescător la oprire;
- **259** pune în slotul 45 vraja „DariusNoxianTacticsONHAttack”, **118** = 45 (următorul atac e acea vrajă; 0xff =
  înapoi la normal), **721** = numele lui W + 0,1, **326** = actualizarea unui buff (durată, stack-uri, slot, sursă);
- 693 +0x2c este aceeași valoare ca 49 +0xc+0x18 a lansatorului (Darius 0x05f176c4), nu un hash al sursei.

**Ce trimite serverul real la W** (`tools/spell_replies.py`: toate cele 96 de lansări au aceeași secvență,
cu valori fixe; doar timpii, id-urile și ținta variază):
- la lansare: 49, 271, 693 (DariusNoxianTacticsONH, 4 s, tip 2), 721, 259, 118 (45), 465, 4×71, 65
  „Spell2_Activate”, 592 (atacul cu vraja din slotul 45), 516;
- la lovire (+0,329 s): 522 (buff-ul scos), 271 (cooldown-ul), 118 (0xff), 465, 4×71 (înapoi), 65
  „Spell2_DeactivateArm”; pe țintă 693 DariusNoxianTacticsSlow (1 s, tip 11) și DariusHemo (5,1 s, tip 13), 263
  (daunele); la ucidere: 453 (aur), 606, 61 (moartea, cu vraja ONHAttack ca ucigaș), un 271 cu cooldown-ul
  înjumătățit (rambursarea lui W).

**Serverul nostru** (`server/spell_templates.py cut` taie tick-ul de lansare și pe cel de lovire din replay în
`data/exe133/templates/`; `lnp_server.py --auto-w "12:40000022"` le rescrie cu id-urile, contorul de lansări,
timpii și pozițiile noastre). În client (`data/exe133/match_dariusw/frames/wide.png`): Darius ridică și rotește
toporul cu strălucirea lui W, iar pe Alistar apare „113”.

Încă din replay, nu calculat: daunele (113,4), ținta și poziția ei (Alistar lângă fântână, fără verificarea razei);
lipsesc atacul de bază obișnuit, ținta aleasă de jucător (491 cu tipul ordinului și ținta e acum citit:
`c2s_codec.py learn ... 491 2 1`, 300/300) și uciderea.

### Atacul de bază al lui Darius (2026-10-05) [măsurat]

**În replay** (392 de 592 ai lui Darius, `data/exe133/codec/592.all.jsonl`; 592 verificat pe tot meciul:
4179 / 4179 identice): un atac = **592** (slotul 0x40 BasicAttack sau 0x41 BasicAttack2, alternate la întâmplare
~50/50 cum spun `basicAttack` / `extraAttacks.mAttackProbability` 0,5; 0x2d = atacul lui W) + **516** (ținta și
poziția ei); la lovire **263** (daunele) și **693 DariusHemo** pe țintă; la ucidere 453 (aur) și 61 („DariusBasicAttack”).
- **Momentul loviturii**: perioada = 1 / (attackSpeed × mAttackSpeedMod din 595), windup = baza + (perioada × p − baza)
  × r, cu p = 0,3 + mAttackDelayCastOffsetPercent (Darius −0,1), baza = p / attackSpeed, r =
  mAttackDelayCastOffsetPercentAttackSpeedRatio (0,5); lovitura vine pe primul tick de server (1/30 s) de după windup.
  Pe 342 de loviri: 276 exact pe tick-ul prezis, 30 la un tick (`spell_info.attack_times`).
- **Daunele**: AD = baseDamage + damagePerLevel × (niv − 1) × (0,7025 + 0,0175 × (niv − 1)) (67,6 la nivelul 2, ca în
  595) + bonusul plat (595 mFlatPhysicalDamageMod); pe minioni (armură 0) daunele = AD exact (77,4 = 64 + 13,4 la
  126 s). Pe campioni intră penetrarea, runele și obiectele: neverificat încă.

**Serverul nostru**: `--auto-attack "12:40000022"` (sau un 491 cu tipul 3 și o țintă; tipul 2 oprește) trimite 592 + 516
din atacul tăiat din replay (`templates/darius_aa.json`) la fiecare perioadă, iar 263 (+ Hemo la prima lovire) pe
tick-ul calculat, cu daunele AD × 100 / (100 + armura țintei din datele ei). În client
(`data/exe133/match_dariusaa/frames/aa.png`): Darius balansează toporul, pe Alistar apare scânteia loviturii
(pusă de client singur) și „44” (64 × 100 / 144) la fiecare atac, la 1,6 s.

### Input real în client: click dreapta pe un inamic, Ctrl+W, W (2026-10-05) [măsurat]

Utilizatorul a permis trimiterea de taste și clickuri în joc. `tools/game_input.ps1 "<plan>"` (ex.
`"14:rclick:735,375;15.5:key:ctrl+w;18:key:w"`, secunde de la apariția ferestrei, coordonate în cadrul de 1920×1080)
trimite input **numai când fereastra jocului e în față** (verificat înaintea fiecărei acțiuni). Motivul pentru care
tastele de mai demult nu mai ajungeau: structura INPUT a lui `SendInput` era cea de 32 de biți (28 de octeți); în
PowerShell pe 64 de biți e de 40 (uniunea la offset 8), iar `SendInput` o refuza (întorcea 0).

**491 citit complet** (tip, țintă, punct): `c2s_codec.py learn 0x13cbd0 0x94b3d0 491 2 1` (antet de 2 octeți, primul
aleator); 300/300 de pachete scrise de client citite identic pentru +0x10 (tipul ordinului), +0x14 (ținta, varint),
+0x18 (punctul clicat, 2 float-uri). Click pe teren → tipul 2; click pe un inamic → **tipul 3 cu ținta**.

**Test** (`data/exe133/match_dariusclick/sheet.png`; Alistar trecut în echipa adversă cu
`--own-79 --set79 "5.team_order=0"`, bara lui devine roșie): click dreapta pe Alistar → 491 tip 3, ținta 0x40000022 →
atacurile lui Darius la 1,6 s, „44” pe Alistar, conturul roșu de țintă; Ctrl+W → 384 → 676 (W nivel 1); W → 16 (slot
1, hash-ul lui W) → răspunsul W cu resetarea atacului: „62” (1,4 × 44,44); click pe teren → 491 tip 2 → atacul se
oprește. Lipsesc: raza de atac și mersul până la țintă (Darius lovește de la distanță), viața țintei, uciderea.

### Raza de atac și mersul până la țintă (2026-10-05) [măsurat + aproximat]

**Pozițiile** (`server/positions.py`): fiecare 552 din replay dă unei unități un drum (primul punct = unde stă) și
o viteză; între pachete unitatea merge pe drum. Control: Darius la 125,825 s e la x 2522,6, iar 592 al lui are
+0x3c = (2522, 12470) — **592 +0x3c = poziția atacatorului (x, z)**, +0xc+0x24 = poziția țintei (x, y, z).

**Măsurat în replay**:
- distanța Darius–țintă la atac: pe campioni cel mult 297 (< 175 rază + 80 raza lui Darius + 65); clădirile (id-uri
  0xff…) și monștrii mari ajung la 300–530 (raze mari) — regula „raza de atac + razele celor doi” se potrivește;
  razele: `overrideGameplayCollisionRadius` din date (Darius 80, Alistar 80), altfel 65 (neverificat);
- în 92 din 286 de atacuri, serverul trimite în același tick un **552 cu un singur punct** (oprirea), în rest Darius
  stătea deja în rază;
- ordinul de atac al clientului (491 tip 3) vine cu un drum de **un singur punct** (poziția eroului): drumul spre țintă
  îl face serverul; drumurile lui Darius înainte de un atac vin la 0,1–0,5 s una de alta (cu clickurile jucătorului);
- viteza din drumurile serverului: 340 (= baseMoveSpeed), nu 697,5 cât pune clientul în ordinul lui.

**Serverul nostru**: ține poziția eroului (pornește din punctul de spawn al lui 79, merge pe drumurile trimise de el
cu baseMoveSpeed); la un ordin de atac, dacă ținta e în rază → oprire (552 cu un punct) și atac; altfel drum drept
spre țintă, refăcut când ținta s-a mutat (cel mult la 0,25 s). Pozițiile din 592 / 516 / 49 sunt acum cele reale.
În client (`data/exe133/match_dariuschase/`): Darius lovește pe Alistar cât e lângă el, apoi iese din fântână
după el (Alistar, cu viteza mărită la ieșirea din bază, se îndepărtează).

Aproximări: drum în linie dreaptă (fără navgrid), ritmul refacerii drumului, raza implicită 65, înălțimea 171.

### Viața țintei, uciderea unui campion, aurul, rambursarea W, sângerarea pasivei (2026-10-05) [măsurat + dedus]

**Viața** (595 `mHP`, grupul 5 al unității): contorul 595 (+0x20) crește la fiecare pachet (~1000/s); serverul nostru
trimite viața țintei cu un contor mare (1.000.000+) și scoate grupul 5 al țintei din 595-urile replay-ului. Viața
pornește din date (baseHP + creșterea pe nivel; Alistar 670) și scade **în momentul în care lovitura ajunge**
(evenimente programate, în ordinea sosirii). În client bara roșie a lui Alistar scade la fiecare lovitură.

**Uciderea unui campion în replay** (Jax de Darius la 308,379; pachete noi învățate, toate exemplarele identice: 417
53/53, 440 57/57, 780 53/53, 222 1124/1124, 238 5367/5367, 101 107/107, 215 97/97, 190 53/53, 46): 453 (300 de aur),
215 `OnChampionKill` (anunțul), 101 {1, ucigașul}, 46 {330, ucigașul}, 190 (death recap: daunele primite pe surse —
DariusCleave, DariusHemoMarker, atacuri de minioni), 750 (evenimente), pe victimă 417 (ca 61, ucigașul + 0x14), 780,
440, 568 (−1, −1), 740; 238 = proiectilele vizuale ale runelor, 222 = statistici (lăsate deoparte). Campionii nu
primesc 61 (acela e doar pentru minioni / monștri). **Moartea campionilor în replicare**: `mHP` = 0 (Jax la 308,445).

**Serverul nostru** (`templates/darius_kill_champion.json`, tăiat cu `WITH_GLOBAL=1` ca să ia și pachetele obiectului 0;
id-urile din blob-urile 750 schimbate și ele): la viața 0 trimite uciderea, aurul eroului (595 `mGold` / `mGoldTotal`,
500 → 800), rambursarea W (271 cu cooldown-ul înjumătățit) când ucide W-ul, și oprește pachetele replay-ului pentru
unitatea moartă. În client (`data/exe133/match_dariuskill/kill.png`, `stacks.png`): „FIRST BLOOD!”, „+300” aur,
scorul 1–0 și KDA 1/0/0, kill feed-ul, mesajul din chat, Alistar mort; aurul din HUD 800.

**Sângerarea** (DariusHemoMarker): în replay, prima lovitură pune 693 DariusHemo (5,1 s), fiecare lovitură următoare
trimite 326 (durata 5,1, stack-urile 2..5, slotul buff-ului), iar daunele vin ca 263 cu +0xa = 6 (daune în timp) la
**1,322 s** unul de altul (244 de ticuri ale lui Darius; datele spun SecondsPerTick 1,26). Formula din date: pe stack,
(13..30 după nivel + 0,3 × AD bonus) pe BleedDuration 5 / SecondsPerTick 1,26 ticuri, prin armură; în replay ticurile
ies mai mari (obiecte / reducere de armură), deci neverificată. Serverul nostru: stack-uri 1..5, 326 la fiecare
lovitură, ticuri cu daune care scad viața, 522 la expirare; uciderea poate veni și dintr-un tic.

Opțiune de test: `--test-hp "40000022=300"` (viața de pornire a unei unități, ca uciderea să vină repede).
Lipsesc: reînvierea, Noxian Might (5 stack-uri), uciderea minionilor (61), XP-ul, asisturile.

### Auditul de proveniență: ce trimitem e fapt, calcul sau copie? (2026-10-05) [măsurat]

Întrebarea utilizatorului: de unde știm că nu hardcodăm și nu trimitem ce serverul real nu trimite? Replay-ul arată
**ce** a trimis serverul (fluxul unui spectator), nu cum a calculat și nu cum e construit; formulele trebuie găsite în
date și verificate pe replay, iar tot ce e copiat dintr-un singur moment trebuie văzut.

**Unealta**: `lnp_server.py` notează la fiecare pachet trimis dintr-un șablon ce câmpuri a schimbat ca id-uri și ce
câmpuri a calculat (`data/exe133/audit_runtime.json`); `tools/template_audit.py` compară fiecare câmp cu
toate cazurile comparabile din replay (același pachet, același rol, aceeași cheie — vraja, buff-ul, animația, slotul —,
aceleași momente: tick-urile lansărilor W, ale atacurilor, ale morților de campion..., aceeași poziție în tick) și îl
clasează: FIXED (același în toate cazurile = fapt de protocol), id, calculat, **COPIED** (copiat deși variază în
replay = hardcodat). Raport: `data/exe133/template_audit.md`. Prima trecere: 148 FIXED, 31 id, 22 calculate,
**52 COPIED**; după corecturile de mai jos: 152 / 28 / 30 / **31** (unele „copiate” sunt de fapt calculate cu aceeași
valoare ca în șablon — unealta vede doar ce se schimbă).

**Corectat din date, verificat pe replay**:
- **timpul de moarte** (417 / 780 +0xc) = `DeathTimes.mTimeDeadPerLevel`[nivel] × (1 + creștere), creșterea
  continuă de mPercentIncrease la 30 s de la fiecare mScalingPoints (map11.bin `{9de5b46c}`: 6, 8, 10, 12, 14, 16, 21,
  27,5, 30…; 900 s 0,425 %, 1800 s 0,3 %, 2700 s 1,45 %): **51 / 51 de morți de campion exacte**; nivelul victimei
  din 606;
- **sursa uciderii** (417 +0x10, aceeași structură ca 61): +0x4 tipul (08 atac, 18 atac de vrajă, 11 vrajă, 10 R,
  20 daune în timp), +0x8 numele vrăjii, +0xc steaguri, +0x10 slotul (0x40 / 0x41 / 1 W / 3 R), +0x14 tipul daunelor
  (0 fizic, 2 adevărat); uciderea lui Jax copiată în șablon era o ucidere prin sângerare;
- **aurul**: prima ucidere din meci = **400** (68,9 s), apoi 300 (mai puțin pentru victime cu serii de morți — nemodelat;
  aur pentru asistențe 75 / 150 / 50); **101** = contorul de multi-kill al ucigașului; **215** +0x14 = slotul
  ucigașului, +0x18 = echipa lui (0x64 / 0xc8), +0xc / +0x10 = un hash pe **personaj** (victimă / ucigaș; Nidalee are
  altul în forma de puma) — luat dintr-un tabel măsurat, funcția lui necunoscută (nu e ELF / FNV / CRC al numelor);
- **recap-ul 190 și blob-urile 750 nu se mai trimit**: fără ele clientul arată la fel „FIRST BLOOD!”, „+400”, scorul,
  KDA-ul și mesajul din chat (`data/exe133/match_dariuskill2/kill.png`); recap-ul e al victimei.

**Încă copiat** (din raport): sloturile buff-urilor (serverul real ia cel mai mic slot liber, dar printre ocupate sunt
și buff-uri interne netrimise clientului — Darius cu {0, 5, 6, 14, 15} primește 17), duratele unor buff-uri, 49 +0x28
(direcția), +0x42, +0x8c+0x1c (un contor), cooldown-ul cu ability haste (+0xc8, 271), 592 +0xc+0x1c, 263 +0x1d, 326
+0xc / +0x10, XP-ul (46), 740, 568 pe victimă.

### Auditul, a doua trecere: de la 31 la 10 câmpuri copiate, toate explicate (2026-10-05) [măsurat]

Auditul compară acum float-urile la 4 cifre (4,0 și 3,999985 sunt aceeași durată cu zgomot de timp), iar la rolul
„țintă” doar unitatea care are acel rol în tick (victima din 417). Funcțiile serverului își declară câmpurile
calculate (`fix.declared`), ca auditul să le vadă și când ies egale cu șablonul. Rezultat: 158 FIXED, 14 id,
59 calculate, **10 COPIED**. Calculate din date / reguli verificate pe replay:
- **cooldown** (49 +0xc+0xc8, 271 +0x14 / +0x18) = cooldownTime[rang] × 100 / (100 + ability haste): **172 / 172** lansări
  Q/W/E/R ale lui Darius (haste din 595 `mAbilityHasteMod`); rambursarea W = 50 %;
- **49 +0xc+0x42 = rangul − 1** (Q la rang 5: 4, în 51 din 62 de lansări);
- **XP la ucidere** (46) = `mExperienceGrantedForKillPerLevel`[nivelul victimei] (map11 `{c6f6a84c}`: 42, 114, 186,
  258, 330…): exact la uciderile solo între niveluri egale; cu diferență de nivel (×0,73..0,76 / ×1,40) și la
  asistențe (împărțit) e altă regulă, nededusă;
- **263**: +0x1d = 1 numai pentru atacurile de bază (0x40 / 0x41), +0xa = 6 pentru daune în timp; **592 +0xc+0x1c** =
  0x80 la primul atac dintr-o serie, mai mic doar la atacurile înlănțuite (un decalaj de timp, dedus);
- **orientarea** (49 +0x28) = cea mai recentă dintre direcția mișcării și a atacului: 165 / 199 (întoarcerea treptată
  nu e modelată); **49 +0x8c+0x1c** = un id diferit la fiecare lansare (96 / 96): generat unic;
- **pe victimă la moarte**: 568 {1, 0, −1, −1} (5 / 6), 740 ținta ștearsă (8 / 8).

**Cele 10 rămase**: sloturile buff-urilor (6 — regula serverului: cel mai mic slot liber, dar printre ocupate sunt și
buff-uri interne netrimise clientului; nu se poate reproduce exact din replay), 693 +0x1d la DariusHemo (1 stack în 290
de cazuri, 5 în 6 — alt mecanism), 326 +0xc / +0x10 (pe slotul sângerării: 5,1 și 0 în toate cele 131 de cazuri —
fix în realitate, auditul nu poate lega 326 de buff), încetinirea W 1 s (o singură excepție de 2 s, pe un minion la
1608,9 s). În client (`data/exe133/match_dariusaudit/final.png`): FIRST BLOOD, +400, aur 900, cooldown-ul W
de 5 s care scade pe HUD.

### Accelerare: motor generic de abilități din date, pentru toți campionii (2026-10-05) [măsurat + aproximat]

Decizia utilizatorului: în loc de abilitate cu abilitate, un motor condus de datele jocului pentru toți cei 163 de
campioni (648 de vrăji Q/W/E/R), aproximările marcate; campionii din replay (10) ajung 1:1 prin extragere automată.

**Recensământ** (`data/exe133/spell_census.json`): 582 de vrăji au formule (`mSpellCalculations`), 397 proiectil,
546 tip de țintire, 306 sunt conduse de script (flags & 4).

**Unelte noi**:
- `server/bin_tree.py`: dump-ul `bainfo bin` transformat în structuri Python (liste, map-uri, structuri imbricate);
- `server/spell_calc.py`: evaluatorul formulelor (Number, EffectValue, NamedDataValue, StatByCoefficient,
  StatByNamedDataValue, StatBySubPart, Sum, Product, ByCharLevelInterpolation / Breakpoints / Formula, Clamp,
  BuffCounter, CooldownMultiplier, AbilityResource, GameCalculationModified / Conditional); **571 / 582** de vrăji se
  evaluează complet; numele calculelor (TotalDamage, BladeDamage…) din token-urile `@Nume@` ale tabelei de texte
  engleze (`Localized/Global.en_US.wad.client`, 11 669 de nume, hash FNV-1a). **Verificat**: Darius Q BladeDamage la rang
  1 cu AD 77,4 = 50 + 1,0 × 77,4 = **127,4 = exact 263 din replay** (113,76 s); W 1,4 × AD = 113,4 (167,2 s);
- `server/spell_engine.py`: forma vrăjii din date (țintire, castRange / castRangeDisplayOverride, castRadius,
  mLineWidth, con, missileSpeed), țintele nimerite (cerc pe sine / la punct, linie cu oprire la primul inamic, con,
  țintă cea mai apropiată de punctul țintit), daunele (calculul TotalDamage / Damage / …Damage; fizic dacă folosește AD,
  altfel magic dacă folosește AP — aproximare), momentul (pregătirea + drumul proiectilului);
- **263 +0x10 = tipul daunelor**: 0 fizic, 1 magic (Azir, 37 / 37), 2 adevărat (Darius R).

**Serverul**: vrăjile eroului vin din `spellNames` ale personajului (orice campion, fără `--hero-spells`); 259 pune
vrăjile lui în sloturi; la orice 16 → 49 / 65 / 271 + motorul (lovituri, 263 cu tipul daunelor, viață, ucidere cu
sursa {11, vraja, 2ac90000, slot, tip}); atacul de bază folosește datele campionului jucat.

**Test cu Garen** (nu e în replay; `data/exe133/match_garenengine/sheet.png`, input real): Q / W / E / R în sloturi,
Ctrl+Q crește Q (la nivelul 1 un singur punct, ca în joc), click dreapta pe Alistar → atacuri cu AD-ul lui Garen (66,
pregătire 0,3 s) „45”, Q → motorul: pe sine, rază 210, 129 brut → 89,6 după armură, apoi **FIRST BLOOD cu portretul
lui Garen**, „+400”, Alistar mort.

**Învățare automată în fundal** (`tools/batch_learn.sh`, rezultate în `data/exe133/codec/batch_learn.txt`):
137 de tipuri de pachete din replay încă neînvățate; primele 16 învățate și verificate 100 % (98, 345, 578, 773, 790,
387, 43, 774…); 117 și 730 au eșuat (de reluat).

Aproximări de știut: tipul daunelor ales din formulă, calculul „de daune” ales după nume, proiectilul se oprește la
primul inamic, mecanicile speciale ale vrăjilor conduse de script (dash-uri, transformări, buff-uri proprii) nu sunt
încă în motor; nivelul 1 fără obiecte la statisticile eroului.

### Extragere automată din replay pentru toți cei 10 campioni (2026-10-05) [măsurat]

`tools/auto_templates.py` face automat, pentru fiecare (campion, vrajă) lansată de cel puțin 3 ori, ce s-a
făcut de mână la Darius W: pachetele lansatorului din tick-ul lansării, secvența cea mai frecventă ca șablon, fiecare
câmp clasat FIXED / variabil pe toate lansările, plus efectele în secunda următoare (buff-uri puse de lansator: nume,
tip, durată; daune: întârziere, tip). Ieșire: `data/exe133/templates/auto/<Campion>/<Vrajă>.json` +
`index.json`; jurnal `data/exe133/auto_templates.log`. Pentru toți cei 10 campioni, inclusiv summoneri, obiecte,
trinket-uri. Exemple: Blitzcrank Q = [516, 49] (35 / 36), W = [49, 693, 65] (41 / 42), E = [49, 693, 259, 118, 465,
271]; Jax E = [693, 49, 65, 693, 721, 467, 271]; Azir Q = [49, 259, 516, 49, 578, 271] (învelișul + vraja); Flash =
[49, 578]. Plus **atacurile** fiecărui campion (592 pe slot și vrajă de atac: 0x40 / 0x41 de bază, 0x42 / 0x43 Lee Sin,
0x2d DariusNoxianTacticsONHAttack / NidaleeTakedownAttack, 0x2f JaxRelentlessAttack, 0x30 AzirBasicAttackSoldier,
0x2e PowerFistAttack, 4 atacuri ale lui Jhin) și **eliberările** vrăjilor care întăresc atacul următor (Darius W:
[522, 271, 118, 465, 71×4, 65]; Nidalee Takedown; Blitzcrank PowerFist).

**Serverul**: pentru un campion din replay, lansarea folosește secvența lui reală (câmpurile variabile calculate cu
regulile verificate: timpi, poziții, contor, orientare, id-uri, cooldown, mana, rang, sloturi de buff — de la 0x30,
regula exactă a serverului fiind necunoscută); **regula generică a atacului armat**: o vrajă cu 118 în tick-ul de
lansare armează atacul următor (cu resetare dacă eroul atacă), atacul folosește șablonul atacului armat al
campionului, daunele vin din calculul vrăjii, iar la lovire pleacă eliberarea; atacurile normale folosesc șabloanele
de atac ale campionului. Tipul daunelor: fizic dacă formula folosește AD, altfel magic dacă folosește AP (aproximare).

**Test cu Blitzcrank** (input real, `data/exe133/match_blitz_sheet.png`, `match_blitzarmed/powerfist.png`): Q
(RocketGrab: șablonul [516, 49] + motorul: proiectil 1800, „79” magic albastru), W (Overdrive [49, 693, 65]), E în
timpul atacului → armat PowerFistAttack (0x2e), resetare, lovitura „82” cu efectul electric, eliberarea (522 pe slotul
nostru, 118 înapoi). Ocolire de test: `--auto-skill "1,2"` (clientul nu cere creșterea lui W / E pentru alți campioni
decât Darius-ul replay-ului; cauză negăsită).

Învățarea automată în fundal: 20 de tipuri noi verificate (98, 345, 578, 773, 790, 387, 43, 774, 68, 256, 770, 375…),
3 eșuate (117, 730, 703) de reluat.

### Creșterea abilităților: corectura utilizatorului și cauza reală (2026-10-05) [măsurat]

Utilizatorul a observat corect: la nivelul 1 există un singur punct, deci testele mele cu Ctrl+Q apoi Ctrl+W / Ctrl+E nu
aveau cum să crească W / E (punctul era consumat de Q); iar `mLevelRef` = 6 schimbă doar nivelul afișat, nu dă puncte.
Testele cu o singură tastă picau din altă cauză, găsită prin experimente de control (nivel 1, o singură tastă):
Darius + Ctrl+E → merge; Blitzcrank (79) **fără** schimbarea campionului în 574 → Ctrl+E merge, HUD-ul are toate
iconițele; Blitzcrank **cu** `--own-574 --set574 "1.champion=Blitzcrank;1.champion_id=53"` → slotul W negru și nicio
cerere 384. Concluzie: campionul din joc e dat de 79; schimbarea lui în 574 strică slotul W (cauza exactă în 574
neștiută) și nu trebuie făcută. `--auto-skill` rămâne doar ca ajutor de test.

### Flash, summoner spells, minionii ca ținte (2026-10-05) [măsurat + aproximat]

**578 nu e dash**: {+0xc 0,0833, +0x10 un vector de direcție, +0x1c} = orientarea (cu timpul de întoarcere). **Flash** =
49 + 578 + un **552 cu id de teleportare** (dimensiune impară: după viteză vine un octet = contorul de teleportări al
unității, 2..17 în replay) și un singur punct (destinația). Pe cele 34 de Flash-uri din replay: distanța mediană 393
(majoritatea 380..420; datele au `castRangeDisplayOverride` 425) → 400. Cooldown 300 (datele globale). **330** =
o stare pornită / oprită (0x0400, 1 → 0, 0) la dash-uri (Lee Q2, Jax E); drumul dash-ului e în 552 cu steaguri 0x00 —
regula generică de dash încă nefăcută.

**Summoner spells (D / F = sloturile 4 / 5)**: care sunt (Darius: D SummonerHaste, F SummonerFlash) din lansările lui
din replay; lansarea = șablonul automat al vrăjii de la oricare campion (summoner-ele sunt la fel pentru toți). În
client (input real): F → Darius sare 400 spre cursor (clientul raportează apoi exact noua poziție), cooldown 300 pe HUD;
D → Ghost. Notă: la începutul jocului D / F sunt în cooldown câteva secunde (clientul nu trimite nimic).

**Minionii** (`tools/minions_table.py` → `data/exe133/minions.json`, `minion_hp.pkl`): 2349 de minioni; tipul
din 98 +0x14 (04 corp la corp → 21 aur, 05 la distanță → 14 în 453 din replay; tun 57 din SR_LevelScript), +0x15 =
valul, echipa după partea hărții unde apar, viața din replicarea replay-ului (grupul 3 bit 0). Serverul îi pune ca ținte
(motorul de vrăji și atacul la click), viața pornește de la cea din replay în momentul loviturii și e apoi a noastră
(grupul 3 al minionului scos din 595-urile replay-ului), moartea = 61 (cu ucigașul și sursa reală) + aurul pe tip.
Test (`data/exe133/match_dariusminion/sheet.png`; ajutoare de test `--speed 3`, `--teleport "88:7150,7150"`, tasta
Y = camera blocată pe erou): Darius la mijloc, atacuri „64” (armură 0), sângerare, minionul 265 → 0, 21 de aur.

## Reconstrucția sursei: Ghidra, compilatorul lui Riot, prima funcție identică (2026-10-06)

**Spațiul de lucru Ghidra.** `tools/ghidra.sh import|decomp|names` (Ghidra 12.1.4 fără interfață) ține exe-ul despachetat în
`client-src/ghidra/BA13.gpr`, cu numele noastre din `client-src/names.tsv` (1.331 de funcții și 910 etichete, doar nume
măsurate; `tools/ghidra_names.py`). Exportul pseudo-C: `client-src/decomp/text_<rva>.c` + `index.tsv`, 60.454 de funcții,
13 eșuate. E material de citit, nu se compilează.

**Compilatorul, măsurat din Rich header-ul lui `game/League of Legends.exe`** (link 2023-02-06, linker 14.32):

| Ce | Build | Obiecte |
|---|---|---|
| codul lui Riot + linker, export, resurse | 31328 | 90 C, 62 C++ |
| biblioteca VC legată static (libcmt / libvcruntime / libcpmt) | 30818 | 23 C, 94 C++, 35 MASM, 5 alias |
| ucrt legat static | 27412 | 53 C, 220 C++, 55 MASM |
| biblioteci gata compilate | 30709 (561 C), 31106, 27031, 27702, 29333, VS 2003-2008 | |

Fără intrări LTCG. Niciun DLL de CRT printre cele 430 de importuri. Build 31328 este exact Visual Studio 2022 **17.2.0**
(pachetul Tools 14.32.31328); `tools/get_msvc.py` îl aduce din canalul fix al lui Microsoft pentru 17.2.0 în
`toolchain/msvc-14.32.31328` (`cl` 19.32.31328, `link` 14.32.31328; bibliotecile lui au build 30818, ca în exe). Prima
descărcare (LTSC 17.2 la zi, build 31342) era alt build și a fost ștearsă. SDK-ul Windows al lui Riot nu e încă
identificat: cele instalate au ucrt cu build 30795 (22621) și 33145 (26100), nu 27412.

**Prima funcție identică.** `client-src/src/LNP_Crc32.cpp` (rva 0x2de720), compilată cu `cl -O2`, dă exact cei 474 de octeți
ai clientului (`python tools/match_func.py client-src/src/LNP_Crc32.cpp Crc@LnpDatagram 2de720 -O2`; octeții acoperiți de
relocări, 80 aici, nu se compară). Ce arată funcția asta despre opțiuni:

| Opțiune | Rezultat |
|---|---|
| `-O2`, `-Ox` | identic (nu le deosebește) |
| `-O1`, `-Od` | diferit (182 / 245 de octeți) |
| `-Oy-` (cu frame pointer) | diferit: Riot omite frame pointer-ul |
| `-arch:IA32` | diferit (4 octeți); implicitul SSE2 și `-arch:AVX2` sunt identice aici |
| `-GS-`, `-Gy -Gw`, `-fp:fast`, `-GR-`, `-MT`/`-MD`, `-std:c++17/20`, `-Ob1`/`-Ob3`, `-Zi` | fără efect pe funcția asta: nemăsurate |

Octeți identici dovedesc compilatorul și opțiunile, nu și scrierea sursei: forma găsită (suma ținută într-un obiect mic,
contorul ultimei bucle inițializat înaintea pointerului) e una care dă aceiași octeți; cu suma într-o variabilă simplă
ies 464 de octeți, cu contorul declarat după pointer diferă un octet. În Git Bash opțiunile se dau cu `-`, nu cu `/`
(`/O2` e transformat în cale).

**Scorul (2026-10-06, seara).** `python tools/match_all.py` compilează tot ce e în `client-src/src/` și compară fiecare
funcție declarată cu `// match: <rva> <simbol>`: 6 din 6 identice.

| rva | Octeți | Sursă | Ce a arătat în plus |
|---|---|---|---|
| 0x146910 | 5 | `Game_SmallPredicates.cpp` (`C2SPacket::Read`) | |
| 0x19ccc0 | 149 | `Replication_RegisterClass.cpp` | bitul se calculează o dată, înaintea ramurii; ordinea a două declarații contează |
| 0x2de720 | 474 | `LNP_Crc32.cpp` | `-O2`, fără frame pointer |
| 0x3630c0 | 29 | `Game_SmallPredicates.cpp` (`GameClient::HasLocalSlot`) | în `names.tsv` se numește `Game_OnConnected`, dar e un predicat: octetul +0x1a8 pus și slotul +0x1a7 în 1..51 |
| 0x370810 | 191 | `Net_PerFrame.cpp` | **`-arch:SSE2`** exact (`-arch:AVX`, `-arch:SSE`, `-arch:IA32` diferă); `-fp:precise/fast/strict` dau aceiași octeți aici |
| 0x9d42e0 | 221 | `Pool_Free.cpp` | lista `{ a, b }` din `for` (cadru de 16 octeți); a doua citire a pointerului de layout e una pe care compilatorul nu are voie s-o unească cu prima (volatile / atomic) |

Metoda când nu iese din prima: o grilă generată de forme de sursă, compilate într-un singur fișier și ordonate după
primul octet diferit (funcțiile ajutătoare cu `__forceinline`, altfel compilatorul nu le mai pune inline când au zeci de
apelanți în fișierul de test).

**Compilatoarele de pe sistem.** Visual Studio Build Tools 2022 17.14 (MSVC 14.44) și Windows SDK 22621 / 26100 au fost
dezinstalate (cu acordul utilizatorului); pe PC rămân doar `toolchain/msvc-14.32.31328` (compilatorul lui Riot) și
`toolchain/llvm-mingw` (pentru `ba_host.dll`, buretele `d3d11.dll`, `bainfo`). Fără SDK nu există anteturi Windows /
ucrt: sursele reconstruite își declară singure ce folosesc (`initializer_list_min.h`), până identificăm SDK-ul lui Riot
(ucrt cu build 27412).

**SDK-ul lui Riot, biblioteca standard și codul de bibliotecă (2026-10-06, mai târziu).**

- *SDK-ul Windows*: `tools/get_winsdk.py get <versiune>` despachetează părți ale unui SDK din pachetele Microsoft în
  `toolchain/` (`msiexec /a`, fără instalare), iar `check` citește build-ul compilatorului din `libucrt.lib`: 10.0.18362
  → 26715, **10.0.19041 → 27412**, exact cât au obiectele ucrt din exe (22621 → 30795, 26100 → 33145). În proiect e
  `toolchain/winsdk-10.0.19041` (doar partea ucrt: anteturi, biblioteci, surse); 20348 și 22000 nu au fost verificate.
  Anteturile Windows propriu-zise (`um`, `shared`) nu sunt încă aduse: `get_winsdk.py get 10.0.19041 headers`.
- *Biblioteca standard se potrivește singură*: instanțiate din anteturile MSVC 14.32, `std::map<i64, T*>::operator[]`
  (rva 0x2d9f00, 140 de octeți), `_Find_lower_bound` (0x2d3f40, 85), `_Insert_node` (0x124b60, 489) și
  `_Throw_tree_length_error` (0x125680, 10) ies identice cu `-O2`. Cu `-EHsc`, `operator[]` are 197 de octeți și un cadru
  de excepții pe care clientul nu-l are: **codul ăsta e compilat fără `/EH`**. `/GS` e pornit: funcția de la
  rva 0x324f50 (tampon de 260 de octeți) își pune cookie-ul de la rva 0x18d5504.
- *Contextul fișierului contează la inline*: singură într-un fișier, `Write` primește `operator[]` inline (554 de octeți);
  cu încă un utilizator al aceluiași `operator[]` în fișier rămâne apel, ca la Riot.
- *Cod de bibliotecă găsit prin octeți* (`tools/match_libs.py` → `client-src/lib_functions.tsv`): fiecare funcție din
  `libcmt`, `libvcruntime`, `libcpmt` (MSVC 14.32) și `libucrt` (SDK 19041) comparată cu funcțiile clientului, fără
  octeții relocați: **1.384 de funcții ale clientului sunt cod de bibliotecă** (236.017 octeți; ucrt 903, libcpmt 366,
  libvcruntime 68, libcmt 47). De exemplu rva 0xf5e4f9 = `free`, 0xf59b30 = `memmove`. Pragul e de 16 octeți, iar
  funcțiile cu relocare în primii 4 octeți sunt sărite, deci numărul real e mai mare.
- *Scor*: `match_all.py` → 11 din 12 identice (cele 6 de mai sus, `LnpBuffer::Reserve` 0x2ee3a0 - numărătorul de
  referințe e `std::atomic` -, și cele 4 din `std::map`). `LNP_WriteDatagram` (0x2efe50) are structura corectă
  (aceleași apeluri, în aceeași ordine: CRC, număr, sumă, octet de steag, masca de confirmări dacă numărul e negativ,
  conținut, apoi cifru - inversare - cifru) dar încă nu e identică: 408 octeți față de 437.
- *Nume corectate*: 0x3630c0 = `Game_IsConnected` (predicat; apelantul 0x324f50 scrie „Game Server Connection
  Established"), iar funcția obiectelor de hartă începe la 0x2e8f80 (`MapObjects_AssignNetIds`), 0x2e9090 fiind doar
  bucla ei de CRC. `ApplyNames.java` știe acum să desfacă un început de funcție greșit (`unfunc`).

**Verificarea țintelor și codul de bibliotecă lărgit (2026-10-06, seara târziu).**

- `match_func.py` nu mai compară doar octeții: unde clientul apelează sau adresează ceva care are nume în
  `client-src/names.tsv` (cod de bibliotecă, importuri, funcții numite de mână), simbolul din obiectul nostru trebuie să
  fie același. Octeții relocați ascundeau greșeli reale: `Net_PerFrame` apela `__ltod3` (cu semn) unde clientul are
  `__ultod3` - contorul de timp e fără semn; `Crt_Free` al nostru era `free` din ucrt. Corectate; scorul rămâne 11 din 12.
- `match_libs.py`, lărgit: prag de 8 octeți nerelocați, candidați aleși după primii 4 octeți nerelocați (nu doar de la
  început), funcțiile din asamblare tăiate doar la simboluri de funcție, și capătul funcției trebuie să cadă pe
  umplutură sau pe începutul funcției următoare. **1.687 de funcții ale clientului sunt cod de bibliotecă** (283.158
  octeți); `lib_functions.tsv` ține și toate simbolurile care au aceiași octeți (ex. 0xf59b30 = `memcpy` și `memmove`,
  1.396 de octeți). Numele sunt în `names.tsv` (3.930 de intrări cu nume) și aplicate în Ghidra.
- `LNP_WriteDatagram` (0x2efe50): 437 de octeți ca la client, 235 identici. Ce a contat: toate adăugările trec prin
  aceeași funcție generică de octeți a tamponului (cu verificarea de lungime zero); steagul se dă prin valoare; masca de
  confirmări e copiată înainte de mărirea tamponului; criptarea e o funcție inline care primește id-ul peer-ului prin
  valoare. Rămase: copierea numărului (`mov ax` la client, `movzx` la noi) și păstrarea lungimii în registru după mască.
  La căutările pe funcții mari, scorul util e asemănarea instrucțiunilor (`difflib`), nu primul octet diferit.

**Cititorul de datagrame și fișierul comun (2026-10-06, noaptea).**

- `client-src/src/LnpDatagram.cpp` ține acum împreună suma de control, scrierea și citirea. Cu amândouă în același
  fișier, `operator[]` al `std::map` rămâne apel în ambele, ca în client, fără utilizatorul de umplutură de înainte
  (singură într-un fișier, fiecare îl primea inline): Riot le avea în același fișier.
- `LNP_ReadDatagram` (rva 0x2dceb0): **497 de octeți din 497, 493 identici**. Ce a arătat potrivirea:
  - tamponul are un cursor de citire (`u16` la +8), iar citirile sunt „dacă încape: citește, avansează, adevărat";
  - masca de confirmări este un `std::bitset<64>`: doar cu el înregistrarea temporară primește cei 8 octeți puși pe
    zero ca bloc (`movq`) înainte de atribuire, ca în client; cu un număr simplu compilatorul elimină zeroul
    (491 de octeți);
  - la +0x18 e o înregistrare de 16 octeți {`short` numărul confirmat = minus numărul datagramei, masca}, copiată
    întreagă;
  - decriptarea întoarce devreme când criptarea e oprită; rezultatele se adună cu `&=`, iar rezultatul final e o
    variabilă separată (`ReadBuffer(...) & ok`); suma se compară ca `crc == Crc()`.
  - Cei 4 octeți rămași sunt în bucla de inversare a octeților: clientul adresează `[body + index]`, noi
    `[index + body]`. Aceeași buclă e și în `Write`, cu aceeași diferență. 25 de forme de sursă ale buclei dau
    același cod; `std::reverse` nu e (devine apel de bibliotecă).
- `LNP_WriteDatagram` scrie masca direct din `ack.mask.to_ullong()` (un temporar, de aceea e citită înainte de
  mărirea tamponului). Rămâne la 235 din 437.
- Scor: 11 identice din 13. La aplicarea numelor în Ghidra, 194 de nume de bibliotecă au fost respinse (motivul nu
  e încă văzut: scriptul înghite excepția).

**Tamponul, mesajul și corecția la codul de bibliotecă (2026-10-06 spre 07).**

- `LnpBuffer::ReadBuffer` (rva 0x2ed2f0): identică, 102 octeți (`LnpBuffer_Read.cpp`; în același fișier cu `Reserve`,
  compilatorul o pune pe aceasta inline, iar clientul o apelează).
- Constructorul de copiere al mesajului (rva 0x2d5c00): identic, 151 de octeți, scris de compilator din membri
  (`LnpMessage.cpp`: `= default` în afara clasei). A fixat structura mesajului (0x34 octeți, tamponul la +0x24) și
  faptul că tamponul are constructor de copiere care împarte blocul și crește numărătorul, și destructor.
  `LnpBuffer::Release` (scade numărătorul, eliberează la zero) e folosită și de `Reserve`, și de destructor.
- `LNP_AppQueueObserver` (rva 0x2e0cd0): 114 octeți ca la client, 90 identici. Un mesaj cu conținut devine un eveniment
  de tip 2 în coada de la +0x80. Diferă ordinea în care sunt scrise primele câmpuri ale evenimentului și felul în care
  sunt puși pe zero cei doi octeți de la +0x10.
- `LNP_SetupChannels` (rva 0x2edff0): amânată; atinge patru containere ale căror tipuri nu le știm încă.
- **Corecție la codul de bibliotecă.** Din cele 1.687 de funcții găsite, doar **1.236** se potrivesc cu o funcție de
  bibliotecă întâlnită o singură dată în client. Restul de 451 sunt aceeași formă de cod la mai multe adrese (de
  exemplu `std::use_facet<...>` la 32 de adrese): cod de șablon care diferă doar prin ce indică relocările, deci
  simbolul găsit e „unul ca acesta", nu neapărat cel real. În `names.tsv` acestea poartă sufixul `__x<N>_<rva>`, iar
  `match_func.py` nu le folosește la verificarea țintelor. `lib_functions.tsv` are coloana 8 = la câte adrese apare.
- Scor: 13 identice din 16.

**Runda cu funcțiile vecine (2026-10-07).** Scor: `match_all.py` → 19 identice din 22.

- Observatorul cozii (rva 0x2e0cd0) e acum identic: funcția vecină (coada, rva 0x2ed000) copiază octeții de la +0x10 și
  +0x11 ai evenimentului unul câte unul, deci sunt două câmpuri de un octet, nu un `u16`; cu ele compilatorul scrie
  zeroul ca la client. Lecția: când o structură nu iese, citește funcțiile vecine care o copiază.
- Atribuirea prin mutare a mesajului (rva 0x2d98c0, 182 de octeți) e identică, scrisă de compilator din membri;
  mutarea tamponului: eliberează blocul propriu, ia câmpurile, apoi golește sursa (`data = nullptr` primul).
  Adresa numărătorului se formează acolo pas cu pas dintr-un pointer testat (`--count`), altfel compilatorul scrie
  `add ecx, -4` în loc de `sub ecx, 4`.
- Pompa transportului văzută de joc (rva 0x2dbdc0, 3 instrucțiuni) și trei funcții mici (`Transport_Small.cpp`: rva
  0x2dbe90, 0x2f05f0, 0x2d08d0) sunt identice. A patra, rva 0x2e4990 (obiectul are ceva la +0x74 și
  `[General] EnableReplayApi` e pus), e la 27 din 35.
- `match_func.py` compară acum și constantele: un literal de șir sau o valoare în virgulă mobilă din obiectul nostru
  trebuie să aibă aceiași octeți ca ținta din client.
- Deschise, de reluat când înțelegem mai mult: `LNP_WriteDatagram` (235/437), `LNP_ReadDatagram` (493/497), rva
  0x2e4990 (27/35), `LNP_SetupChannels`, coada de evenimente rva 0x2ed000 (memorie pe fir, coadă fără lacăt).

**Mesajele: scriere, citire și adăugarea generică (2026-10-07, continuare).** Scor: 22 identice din 26.

- `tools/callers.py <rva>` listează cine apelează o funcție (cu mărimi și nume): așa au ieșit la iveală scriitorul
  și cititorul de mesaje.
- Adăugarea generică în tampon există și ca funcție separată (rva 0x2d2d60, 62 de octeți): identică; întoarce mereu
  adevărat. `std::_Destroy_range` pentru mesaje (rva 0x2d2da0, 57 de octeți) e identică și a fixat forma
  destructorului de tampon (`Drop`: pointer testat, apoi `--count`), aceeași care potrivește și mutarea.
- **Scriitorul de mesaje (rva 0x2efcc0, 391 de octeți): identic.** Antetul de 16 biți = lungimea conținutului << 3 |
  bit 2 „același canal ca mesajul dinainte" | bit 1 „numărul e cel dinainte plus unu" | bit 0 „fragment"; urmează doar
  ce nu spune antetul: canalul, numărul, id-ul / numărul / indexul fragmentului, apoi conținutul. E exact formatul
  măsurat pe fir la transport. Antetul e scris ca octeți (adăugarea generică), câmpurile ca valori tipizate (`Put`):
  amândouă formele există în codul lui Riot. Câmpurile mesajului au acum nume: număr (+8), canal (+0xb), fragment
  (+0x18, +0x1a, +0x1b), text (+0x30).
- Cititorul de mesaje (rva 0x2dcd40): 282 din 360 (clientul are 357). Instrucțiunile sunt cele ale clientului; diferă
  ce ține compilatorul în registru (noi `previous`, clientul lungimea tamponului).
- Cele 194 de nume „respinse" de Ghidra nu erau o problemă: excepția spune că numele exista deja la acea adresă,
  adică analiza proprie a lui Ghidra recunoscuse aceleași funcții de bibliotecă - o confirmare independentă.
- `LNP_WriteDatagram` rămâne la 235: 72 de combinații între adăugarea tipizată și cea generică nu schimbă nimic.

**Reluarea celor patru funcții deschise (2026-10-07).** Scor: 23 identice din 26.

- **`LNP_ReadDatagram` (rva 0x2dceb0): identică, 497 de octeți.** Cheia: octeții dați cifrului sunt o mică
  înregistrare `LnpBytes { u16 size; u8* data; }` trecută prin valoare, nu doi parametri. Doar așa compilatorul adresează
  octeții din bucla de inversare ca `[start + index]`; cu lungimea scrisă înaintea pointerului ies și registrele
  clientului. Drumul până acolo: un fișier de probă cu 12 forme ale buclei arătat prin ce se schimbă ordinea bază / index
  (pointerul trebuie *încărcat* după ce contoarele sunt inițializate - o copie nu contează).
- `match_func.py`: o țintă care e ea însăși o funcție reconstruită (`// match:`) se verifică față de simbolul nostru,
  nu față de numele pus de mână în `names.tsv`.
- Cititorul de mesaje (rva 0x2dcd40), 282 din 360: **cauza e găsită, forma de sursă nu.** Noi ținem `previous` într-un
  registru și reîncărcăm lungimea tamponului; clientul ține lungimea și ia `previous` din stivă la fiecare folosire.
  Cu cele două folosiri înlocuite de constante, codul nostru e exact al clientului; cu `previous` citit printr-un
  pointer volatil ies 346 din 360.
- `LNP_WriteDatagram` (rva 0x2efe50): 239 din 437 (de la 235, datorită înregistrării). 144 + 72 de combinații noi
  (tipul lui `start`, cum e umplută înregistrarea, steagul, numărul, masca) dau toate același cod.
- rva 0x2e4990: neschimbat, 27 din 35; nici opțiunile de compilare nu contează (13 încercate).

**Observatorii transportului (2026-10-07, continuare).** Scor: 32 identice din 35.

| rva | Octeți | Sursă | Ce face |
|---|---|---|---|
| 0x2df4e0, 0x2df810 | 169, 172 | `LnpAppObserver.cpp` | evenimentele 0 și 1 (id de peer + unul sau doi octeți) puse în coada aplicației |
| 0x2e2a70, 0x2e2020 | 147, 97 | `LnpCompression.cpp` | comprimă / decomprimă conținutul unei datagrame (zstd din client) |
| 0x2e2b10 | 68 | `LnpTimeObserver.cpp` | ține, pe peer, maximul dintre timpul datagramei (+0x38) plus un număr al obiectului |
| 0x2df590, 0x2df9d0, 0x2e2780 | 25, 25, 118 | `LnpAddressObserver.cpp` | evenimentul 0 pune, evenimentul 1 șterge un steag al peer-ului; o datagramă îi reține adresa |
| 0x2da4d0 | 252 | `LnpAddressObserver.cpp` | `std::map<i64, LnpPeerEntry>::operator[]`, scris de compilator |

Ce s-a aflat despre date:
- **Evenimentul** (0x50 de octeți) e o structură simplă umplută pe loc (`{ tip, peer, octet, octet, mesaj }`), fără
  constructor; **mesajul** are valori inițiale pe fiecare membru (toate zero) și niciun constructor scris de mână.
- **Datagrama**: octetul de la +0x40 înseamnă „conținut comprimat" (îl pune comprimarea, îl citește decomprimarea);
  +0x38 și +0x48 sunt două numere `double` (timpi); +0x5c e adresa de unde a venit (28 de octeți).
- **Comprimarea** urmează `[Network]` din `game.cfg`: pornită (+0x468), mărime minimă (+0x46c), nivel (+0x470);
  tamponul de lucru are 0x44c octeți. Se comprimă doar datagrame cu număr pozitiv și doar dacă rezultatul e mai mic.
- **Adresa** (`LnpAddress`): 16 octeți de gazdă curățați în corpul constructorului, apoi 0, 0, 1 - ordinea se vede în
  `operator[]`. **Intrarea de peer** are 0x38 de octeți: adresa, două numere de 64 de biți, două steaguri.
- Evenimentul 0 pornește un peer și evenimentul 1 îl oprește (steagul de la +0x31): după toate aparențele
  „conectat" / „deconectat".
- Rezultatul unui observator nu e doar adevărat / fals: observatorul de adrese întoarce 3 pentru un peer necunoscut.

**Datagrama întreagă (2026-10-07, continuare).** Scor: 36 identice din 39.

Constructorul (rva 0x2d6700, 102 octeți), destructorul (rva 0x2d8ef0, 113) și atribuirea prin mutare (rva 0x2d9a40,
246) ale datagramei sunt identice. Niciuna nu e scrisă de mână: sunt `= default` în `LnpDatagram_Life.cpp`, iar
compilatorul le scrie din membri și din valorile lor inițiale (`LnpDatagram.h`). Împreună fixează toată structura
de 0x78 octeți:

| Offset | Membru | Valoare inițială |
|---|---|---|
| +0x00 | id-ul peer-ului (64 de biți) | 0 |
| +0x08 | numărul (`short`; negativ = confirmare) | 0 |
| +0x0a, +0x0c, +0x10 | un octet și două numere de 32 de biți, neînțelese încă | 0 |
| +0x18 | confirmarea: număr + mască `std::bitset<64>` | 0 și toți biții puși |
| +0x28 | `std::vector` cu elemente de 16 octeți (probabil confirmări) | gol |
| +0x38, +0x48 | doi timpi (`double`); +0x38 e pus din ceas când datagrama intră în coada firului de lucru | 0 |
| +0x40 | „conținut comprimat" | 0 |
| +0x50 | conținutul (`LnpBuffer`) | gol |
| +0x5c | adresa (28 de octeți) | zero, ultimul membru 1 |

- Masca pornește cu toți biții puși printr-un `std::bitset<64>` dat constructorului confirmării (dată ca număr de 64
  de biți, compilatorul scrie aceleași instrucțiuni în altă ordine).
- `std::vector<Ack>::_Tidy` (rva 0x2f2bb0) e identică; destructorul datagramei o are inline, mutarea o apelează, ca în
  client, fără nicio funcție de umplutură.
- Văzut, nereconstruit încă: comanda firului de lucru (0x100 octeți: peer, doi octeți, tip, o datagramă la +0x10, un
  bloc de 40 de octeți, un mesaj la +0xb0, un bloc de 24) cu constructorul la rva 0x2d5ae0 și mutarea la rva 0x2d9820;
  funcțiile rva 0x2dd660 / 0x2dd440 pun în coada de la +0x40 comenzi de tip 4 (o datagramă) și 7 (un mesaj).

**Comenzile firului de lucru și coada fără lacăt (2026-10-07, continuare).** Scor: 49 identice din 54.

- **Opțiune nouă măsurată: C++17.** Blocurile cozii sunt aliniate la 64 de octeți și clientul le alocă cu
  `operator new` aliniat (două argumente: mărime și aliniere), pe care compilatorul îl folosește doar de la C++17.
  `-O2 -std:c++17` e acum setul implicit din `match_func.py`; toate funcțiile de până acum rămân identice cu el.
- **Comanda** (`LnpCommand.h`, 0x100 octeți): id de peer, doi octeți, tipul (+0xc, neinițializat), o datagramă (+0x10),
  o parte de 40 de octeți (+0x88: peer, `u16`, `u8`, trei `double`), un mesaj (+0xb0), o parte de 24 de octeți (+0xe8:
  peer, `u32`, `double`). Constructorul (rva 0x2d5ae0, 189 octeți) și mutarea (rva 0x2d9820, 149) sunt identice,
  scrise de compilator.
- **Cele nouă funcții care pun comenzi în coadă** (`LnpWorker_Post.cpp`), câte una pe tip 0..8: construiesc comanda,
  mută în ea datagrama / mesajul / partea, o ștampilează cu ceasul (tipurile 0-4 și 6) și o pun în coada de la +0x40.
  Identice: tipurile 0, 3, 4, 5, 6, 7, 8. Tipurile 1 și 2 (rva 0x2dd220, 0x2dd2d0): 145/172 și 153/183 - aceleași
  instrucțiuni, două dintre ele în altă ordine; nicio ordine a instrucțiunilor din sursă nu o reproduce.
  Timpul mesajului e la +0x10 în mesaj; al datagramei la +0x38.
- **Coada** (`LnpQueue.h/.cpp`, șablon pe tipul elementului): `Push` e identică pentru comenzi (rva 0x2ed120, 252
  octeți) și pentru evenimente (rva 0x2ed000, 278), la fel constructorii blocurilor (rva 0x2d6a10, 0x2d69b0). Orice
  fir poate adăuga fără lacăt: fiecare fir are un bloc propriu de ~64 KiB (`static thread_local`, 244 de comenzi sau
  734 de evenimente), ia următorul nod, îl leagă după ultimul cu un schimb atomic (`last.exchange`), scrie legătura
  cu `memory_order_release` și trezește cititorul (`std::condition_variable` la +0x30, după un `std::mutex`).
- Ceasul transportului: funcția rva 0xa2c930 pe obiectul de la +0x20 al celui indicat de rva 0x18d9adc.

**Partea de joc a transportului (2026-10-07, continuare).** Scor: 49 identice din 55.

- Ce în `functions.txt` apare ca o funcție de 2320 de octeți la rva 0x2ec560 sunt de fapt trei: un ajutor de jurnal
  (0x2ec560, 151 de octeți), **`LnpAppObserver::Update` (0x2ec600, 511 octeți)** - la ea sare pompa rva 0x2dbdc0 - și
  bucla unui fir (0x2ec800, 1648 de octeți). `functions.txt` nu are începuturile 0x2ec600 și 0x2ec800.
- `Update` (firul jocului, o dată pe cadru): scoate fiecare eveniment din coadă (`LnpQueue::Pop`, inline) și îl dă
  unui callback `std::function` al obiectului: un mesaj (tip 2) → `onMessage(peer, canal, timp, octeți, lungime)` de la
  +0x1e8; tipurile 0 și 1 → `onPeer(peer, tip == 0, octet, octet)` de la +0x1c0. Semnăturile sunt citite din ordinea și
  mărimea copiilor pe care codul le face înaintea apelului (`_Do_call`, a treia intrare din tabela virtuală).
- `LnpQueue::Pop`: citește nodul de după primul, mută valoarea, avansează; blocul din care venea nodul vechi e
  eliberat când i s-au citit toate nodurile (`delete` aliniat cu mărime: 0xfd00, 0x40).
- Stare: 509 octeți față de 511, aceleași instrucțiuni, altă așezare a variabilelor pe stivă (cadrul clientului e cu
  8 octeți mai mare). Forma buclei și 26 de seturi de opțiuni nu o schimbă. `-MD` dă alt cod (apel prin import la
  `free`), deci runtime-ul static (`-MT`) e confirmat și de cod.
- Bucla de la rva 0x2ec800 e un fir care, pentru fiecare peer dintr-o hartă, scoate datagrame din cozi cu așteptare
  (`_Mtx_lock`, `_Cnd_wait`) și le dă mai departe după o întârziere configurată: nereconstruită.

**Evidența întregului cod (2026-10-07).**

- `tools/function_starts.py`: `functions.txt` fusese făcut din țintele de apel și îi lipseau funcțiile la care se ajunge
  doar prin salt sau printr-un pointer din date. Regula (țintă de `jmp` din afara funcției sau pointer relocat din
  date, aliniată la 16, precedată de `int3`) a găsit 935 de începuturi noi, dintre care 910 sunt funcții și în
  exportul Ghidra. Lista are acum **58.434** de începuturi.
- `tools/progress.py` (funcții și octeți de cod):

  | | Funcții | Octeți | Din cod |
  |---|---|---|---|
  | reconstruite, identice cu clientul | 49 | 7.402 | 0,05% |
  | reconstruite, încă neidentice | 6 | 1.696 | 0,01% |
  | cod de bibliotecă, găsit într-un singur loc | 1.244 | 215.864 | 1,35% |
  | formă de cod de bibliotecă, în mai multe locuri | 451 | 73.478 | 0,46% |
  | neatinse | 56.684 | 15.611.824 | 97,67% |
  | total | 58.434 | 15.984.696 | |

- Biblioteci străine văzute după șirurile lor: OpenSSL 1.1.x, Wwise v2019.1.10, libVorbis 1.3.6 (20180316), libvpx
  (VP9) v1.8.0, zstd, Lua 5.1, msgpack. Sunt compilate cu alte build-uri de compilator (Rich header: 30709, 27031,
  31106...) și ar trebui potrivite din sursele lor publice, nu rescrise.
- `match_all.py` scrie acum `client-src/symbols.tsv`: pentru fiecare simbol folosit de funcțiile identice, adresa din
  client pe care ar trebui s-o pună linkerul acolo. **92 de simboluri, fiecare la o singură adresă** în toate
  folosirile (de ex. `__security_check_cookie` → rva 0xf411ba): octeții relocați nu mai sunt „necomparați", ci
  verificați între ei. Tabela e harta de legare de care are nevoie o construire a surselor noastre împotriva
  clientului.

**Generatoare în loc de potrivire de mână (2026-10-07).** Scor: 9.127 de funcții identice, 2,77% din octeții de cod
(de la 141 / 0,07%). Metoda: funcțiile pe care compilatorul le repetă (inițializatorii globalelor, reflecția, destructorii
unor baze comune) sunt citite din client după tipare și sursa lor e scrisă de un program; fiecare funcție are linia ei
`// match:` și e dovedită de `match_all.py` ca orice funcție scrisă de mână.

- `tools/shapes.py` grupează funcțiile după octeți cu adresele mascate (13.800 de funcții, 1,2 MB în grupuri de 2+).
- `tools/function_starts.py` ia acum și adresele de cod împinse cu `push imm32` (callback-urile atexit): `functions.txt`
  are 66.825 de începuturi (toată zona `.text$yd` de la rva 0xf9b720 era văzută ca o singură funcție).
- `client-src/initializers.txt`: tabela CRT a inițializatorilor dinamici (rva 0xfab710, 3.815 funcții `??__E`);
  2.900+ sunt reconstruite.
- `tools/gen_sources.py [fișier]` scrie `client-src/src/gen/<fișier>`. Unele tipare sunt **speculative**: generatorul
  propune, compilatorul verifică, `prune()` scoate ce nu iese identic.

| Fișier generat | Ce conține | Funcții |
|---|---|---|
| RStringGlobals.cpp | `RString g("literal")` (RString.h: tipul de șir al lui Riot, bitul 0 al capacității = memorie proprie) | 766 |
| ElfKeys.cpp | `ElfKey g("Name")` = hash ELF (PJW) pe litere mici, prin `std::string` (ElfKey.h, rva 0x120eb0) | 610 |
| HashGlobals.cpp | `u32 g = Fnv1aLower("...")` / `Fnv1Lower` / `ElfHashLower` (Hashes.h) și tablouri de astfel de valori | 122 |
| MapGlobals.cpp | `std::map<Enum, const char*> g = {{0, "Unknown"}, ...}` (tabele enum → nume; fiecare hartă are cheia ei, de aceea constructorul e inline) | 34 |
| GlobalInstances.cpp | destructorii bazei `GlobalInstance<T>` (obiectele unice) | 343 |
| MetaClasses.h/.cpp, MetaMembers.cpp, MetaGetters.cpp, BinClasses.h, MetaFunctions.cpp | reflecția claselor `.bin` | ~6.900 |

**Reflecția (`Meta.h`, `tools/gen_meta.py`).** Fiecare clasă pe care o pot conține fișierele `.bin` are o descriere
globală `MetaClass` (0x50 de octeți; constructor rva 0x9b9a60, destructor rva 0x9bb6c0, `AddMember` rva 0x9bd410).
Hash-urile din ea sunt FNV-1a pe litere mici, deci **numele reale ale claselor și membrilor** vin din `data/hashes`
(`ContextualConditionChanceToPlay`, `mPercentChanceToPlay`...). Forma de sursă care dă codul clientului: o clasă proprie
pe descriere, cu constructor inline care face `unknown00 = 0; parent = ...; AddMember<T>(HASH("nume"), offset, 0)...`;
`AddMember<T>` sunt funcții separate în client (instanțieri explicite în alt fișier), la fel getter-ele descrierilor.
Codul de tip `.bin` al membrului dă tipul C++ (1 bool, 3 u8, 6 int, 7 u32, 0xa float, 0x10 RString, 0x11 hash,
0x82 pointer, 0x83 obiect inclus, 0x84 legătură, 0x80 / 0x81 liste, 0x85 opțional, 0x86 hartă); listele și hărțile
primesc un obiect de „elemente" (cod + mărime + tabelă virtuală). Toate cele 1.944 de descrieri sunt găsite; 1.872 au
inițializatorul refăcut. Clasele descrise sunt deocamdată schelete (bază, mărime, aliniere, virtual sau nu, constructor /
destructor unde clientul le are separat) - destul pentru `MetaCreate/Construct/Destroy/Destruct` a ~1.400 de clase.
Slotul 2 al tabelei virtuale (apelat de funcția de la +0x18 a descrierii) e gol în majoritatea claselor.

Reguli noi ale verificatorului (`match_func.py`): `// same: <rva> <simbol>` = alt nume al aceleiași funcții (plierea de
cod identic a linker-ului dă o adresă mai multor funcții); constantele adresate cu deplasament se compară de la
deplasament. Observații: placement-new trebuie să fie cel din `<new>` (al nostru adăuga un test de null); funcțiile
„ScalarDeletingDestructor" scrise de mână în ZoneB/C/D sunt imitații - forma reală e o clasă cu destructor virtual
(compilatorul scrie `??_G`), corectat la rva 0x2db8b0.

Ce nu se poate fără descărcări: bibliotecile străine (libcurl 7.78.0, zlib 1.2.11, libvpx 1.8.0, libVorbis 1.3.6,
zstd, Lua 5.1, msgpack, libyaml; Wwise 2019.1.10 fără sursă) sunt compilate cu alte build-uri de compilator (Rich header:
30709, 31106, 27031, 27702, 29333). zstd 1.5.6 cu compilatorul lui Riot potrivește doar 74 de funcții mici: trebuie
versiunea exactă și compilatorul ei.

**Continuare (2026-10-07).** Scor: 9.911 identice.
- Generatoare noi (toate verificate; `gen_sources.py` verifică acum orice fișier generat și îl rescrie fără funcțiile
  care nu ies identice): `HashTables.cpp` (`std::unordered_map<u32, int>` din liste {hash, număr}, ex. TOP / JUNGLE /
  MIDDLE / BOTTOM / UTILITY), `StringGlobals.cpp` (`std::string g;` goale: doar destructorul se înregistrează),
  `MapGlobals.cpp` și pentru valori de un octet. Funcțiile de hash: `Hashes.h/.cpp` (FNV-1a cu start, FNV-1, ELF ASCII)
  și `ElfKey.h/.cpp` (ELF prin `tolower` din CRT) - identice.
- Clasele simple ale reflecției (doar membri primitivi, fără goluri) au acum definiția completă în `BinClasses.h`, cu
  numele reale ale membrilor și valorile inițiale citite din `MetaCreate` (pentru o bază abstractă: din `MetaCreate` a
  unui descendent); `MetaCreate/MetaConstruct` inline, destructorii virtuali (`??_G`) și `GetClass` ale lor sunt
  identice. Rădăcina `BinObject` are destructorul inline și gol.
- **Lua 5.1.5 e compilat de Riot ca C++ cu propriul compilator, dar fără `-std:c++17`** (standardul implicit, C++14 -
  măsurat pe `luaZ_fill`, rva 0xc19690: cu C++17 alocarea registrelor diferă). `gen/lua515tp/*.cpp` includ sursele
  publice din `tools/third_party/lua-5.1.5` și numesc 276 de funcții identice; restul (ex. `auxgetinfo`, `luaV_execute`)
  diferă - de aflat dacă Riot a modificat Lua.
- Harta codului (cine apelează alocatorul lui Riot vs. `malloc`/`free`): codul Riot e cam rva 0x60000-0xbc0000,
  bibliotecile străine și CRT-ul restul până la 0xf40000 (~3,5 MB, ~22% din cod; OpenSSL ~0xd7d000+, curl ~0xb6e000,
  yaml ~0xb29000 / 0xb3d000, Lua 0xc16000+).

**Continuare (2026-10-07, bibliotecile precompilate).** Scor (`tools/progress.py`, toate sursele recompilate): 15.242 de funcții identice, 2.440.176 de octeți = 15,32% din cod (de la 12.086 / 7,85%); 38 de funcții scrise, dar încă neidentice (de la 135); cu bibliotecile de runtime recunoscute (1,82%) rămâne necercetat 81,93% (de la 90,26%).
- **Cheia găsită:** bibliotecile pe care clientul le-a primit gata compilate păstrează registrul de cadru (`-Oy-`); cu
  `-O2` simplu aproape nimic din ele nu ieșea identic. Măsurat pe sentry-native: 78 de funcții cu `-O2`, 247 cu
  `-O2 -Oy-`. Bibliotecile compilate de Riot odată cu jocul (zlib, zstd, yaml, curl, FreeType, LodePNG) rămân pe `-O2`
  fără `-Oy-` (curl cu `-Oy-` scade de la 256 la 17).
- Zonele rămase au fost identificate după șirurile și constantele din cod (rva 0xbb4000-0xc16500 și 0xc91c00-0xf40000).

| Bibliotecă | Dovada versiunii | Compilator și opțiuni | Funcții identice verificate |
|---|---|---|---|
| FreeType 2.10.1 | `FT_New_Library` scrie 2, 10, 1 (rva 0xbb7993) | al lui Riot, C, `-O2`, configurarea implicită, un fișier pe modul | 864 |
| LodePNG 20180611 | șirul `20180611` (singurul commit cu această versiune) | al lui Riot, C++17, `-O2` | 72 din 75 |
| sentry-native 0.4.17 (partea C) | `sentry.native/0.4.17` | MSVC 14.31.31106, `-O2 -Oy-` | 239 |
| libvpx 1.8.0 (fișierele C) | `v1.8.0`, configurare x86-win32-vs15 | Visual Studio 2017 (al nostru: 14.16.27048), `-O2 -Oy-` | 710 |
| libvorbis 1.3.6 | `20180316` | Visual Studio 2017, `-O2 -Oy-` | 100 |
| libogg 1.3.3 | fără șir; 1.3.3 și 1.3.4 dau aceleași funcții | Visual Studio 2017, `-O2 -Oy-` | 9 |
| libwebm (copia din libvpx 1.8.0) | `GetVersion` = 0.2.1.0 (rva 0xf3c940) | Visual Studio 2017, `-O2 -Oy- -EHsc` | 100 |
| OpenSSL 1.1.1m | (știut) | MSVC 14.30.30709 | 2.731 (de la 1.766) |

- **OpenSSL:** 1.372 de funcții aveau octeții identici, dar erau respinse la verificare: înregistrările de eroare poartă
  numele fișierului sursă (`OPENSSL_FILE = __FILE__`), iar build-ul OpenSSL compilează fiecare fișier după calea lui de
  la rădăcină, cu `\` (`ssl\statem\extensions_srvr.c`). Fișierele generate definesc acum `OPENSSL_FILE` cu acea cale
  (`gen_sources.py`, `file_prelude`).
- `gen_sources.py`: `library_files(..., within=(rva, rva))` ține o bibliotecă C++ în zona ei (obiectul ei aduce și
  funcții ale bibliotecii standard, pe care clientul le are în altă parte). `match_func.py`: eticheta unui spațiu de
  nume anonim (`?A0x<8 hex>`) vine din numele fișierului compilat și nu mai contează la căutarea simbolului.
- `tools/get_libsrc.py` aduce acum și FreeType 2.10.1, LodePNG (commit 9426bf43) și sentry-native 0.4.17 (arhiva de
  release, cu crashpad). `tools/third_party/libvpx-1.8.0-build/vpx_version.h` e fișierul pe care îl scrie build-ul
  libvpx pentru v1.8.0.

Rămas deschis la biblioteci:
- FreeType: 30 de funcții (45 KB) au octeții identici, dar apelează o funcție pe care editorul de legături a contopit-o
  cu una identică din altă bibliotecă (`FT_Stream_Pos` = `ZSTD_DDict_dictSize`, `ft_hash_num_lookup` = `hash_lookup`);
  le trebuie linii `// same:` scrise automat și verificate.
- libvorbis: funcțiile cu mult calcul în virgulă mobilă (smallft, mdct, codebook, floor1) nu ies încă identice
  (`-fp:fast`, `-GS-`, `-arch` încercate: mai rău). libvpx: partea scrisă în asamblare (~100 KB) cere nasm / yasm.
- libcurl: 228 din ~1.266 de funcții - configurarea lui Riot (ce protocoale sunt dezactivate) nu e încă aflată.
- crashpad (C++, rva 0xc9d970-0xcc0000, ~140 KB, sursa e în arhiva sentry-native), restul Lua. zstd 1.4.9 e practic
  complet (220 din 228 de funcții în zona lui, rva 0xc4c000-0xc91c00). Wwise 2019.1.10 (rva 0xcc0000-0xd60000,
  ~640 KB) nu are sursă publică.

**Continuare (2026-10-07, a doua parte a rundei pe biblioteci).** Scor (`tools/progress.py`): 15.981 de funcții
identice, 2.767.244 de octeți = 17,38% din cod (de la 15.242 / 15,32%); 16 funcții scrise și încă neidentice;
necercetat 79,92%.
- **Lua 5.1.5 e compilat cu `-arch:SSE`** (numerele `double` trec prin stiva x87: `lua_pushnumber` din client face
  `fld` / `fstp`, al nostru făcea `movsd`). 372 de funcții verificate (de la 276). Restul codului lui Riot măsurat până
  acum e `-arch:SSE2`; curl cu `-arch:SSE` scade (300 -> 224), deci opțiunea e a lui Lua, nu a tuturor bibliotecilor.
- **Funcții contopite de editorul de legături** (`match_func.folded`): când clientul apelează o adresă pe care o altă
  sursă a refăcut-o sub alt nume, verificatorul caută simbolul nostru în obiectele aceleiași biblioteci
  (`client-src/obj/<etichetă>/`) și îl acceptă dacă are exact octeții clientului de la acea adresă. FreeType 893 (de la
  864), OpenSSL 3.096 (de la 2.731), zlib 37 din 37, zstd 202.
- **crashpad + mini_chromium** (din arhiva sentry-native 0.4.17; MSVC 14.31.31106, C++17, `-O2 -Oy- -EHsc`,
  `_HAS_EXCEPTIONS=0`): 182 de funcții verificate. Alte ~90 au octeții identici, dar mesajele lor de log poartă calea
  completă a fișierului din build-ul Riot (`T:\p4\depot\LoL\__MAIN__\code\External\sentry\tmp\sentry-native\...`).
  `__FILE__` nu se poate redefini, iar `/pathmap` nu schimbă `__FILE__` la aceste compilatoare (`/FC /d1trimfile:` doar
  taie un prefix); ar trebui ca arborele de surse să stea chiar la acea cale (un disc T: montat). Nefăcut.
- **libcurl**: 265 de funcții (de la 228) cu `CURL_DISABLE_*` pentru toate protocoalele în afară de HTTP(S) și FILE
  (`file_done` există în client), plus zlib și zstd. Restul nu iese pentru că în client funcții din fișiere diferite
  sunt topite una în alta (`Curl_multi_handle` conține `Curl_hash_init` din `hash.c`): Riot compilează mai multe fișiere
  curl într-o unitate. Toată biblioteca într-o singură unitate nu compilează (`base64`, `protocols` definite de două
  ori), iar loturile de 8 în ordinea listei nu explică perechea multi.c + hash.c - gruparea rămâne de aflat.
- Etichetele care vin din numele fișierului compilat (`?A0x<8 hex>` la spații de nume anonime, `<lambda_<32 hex>>`)
  nu mai contează nici la căutarea simbolului, nici la compararea țintelor (`match_func.tagless`).
- Lecție: la prima generare a unei biblioteci, o funcție „geamănă" (aceiași octeți, altă țintă de apel, ex.
  `sentry_options_set_database_path` / `..._pathw`) poate trece, fiindcă ținta ei încă nu e refăcută; a doua trecere a
  generatorului o respinge (sentry 239 -> 236). După o bibliotecă nouă, `gen_sources.py` se rulează de două ori.
- Cele mai mari grupuri de cod repetat din partea lui Riot (`shapes.tsv`: 1,0 MB încă deschis în 1.843 de grupuri) sunt
  funcții de legătură pentru API-ul REST (41 de funcții a câte 1.165 de octeți la rva 0x435310...), cu multe tipuri
  încă necunoscute - nu se pot scrie mecanic deocamdată.

**Continuare (2026-10-07, codificarea câmpurilor din pachete - primul cod al lui Riot scris de un generator din zona
pachetelor).** Scor măsurat (`tools/progress.py`): 16.700 de funcții identice,
2.872.035 de octeți = 18,03% din cod, necercetat 79,27% (cu 323 + 249 + 98 funcții de câmp); după regulile adăugate
apoi (mai jos) generatorul verifică 366 + 287 + 106.
- **Ce s-a măsurat:** idiomul de inversare a biților unui octet
  (`((b * 0x0802 & 0x22110) | (b * 0x8020 & 0x88440)) * 0x10101 >> 16`) apare în 2.648 de funcții, 2,13 MB = 13% din
  cod. E codificarea câmpurilor: fiecare octet citit de pe fir trece printr-un lanț propriu câmpului, din pași de un
  octet - adună / scade o constantă, sau-exclusiv cu o constantă, rotire, inversarea biților, scădere dintr-o constantă,
  căutare într-o tabelă de 256 de octeți (ex. va 0x1b3d460), schimbarea între ei a biților vecini sau a perechilor de
  biți. Scris ca pași simpli în C++ (`client-src/src/FieldCodec.h`: `Rev`, `Rol`, `Ror`, `Swap1`, `Swap2`), lanțul dă
  exact codul clientului (prima funcție identică: rva 0x347220, apoi rva 0x778ec0).
- **`tools/gen_fields.py`** citește lanțul din codul fiecărei funcții: o rulează pentru toți cei 256 de octeți de
  intrare și, de câte ori o instrucțiune lasă în registrul ei o valoare nouă unu-la-unu, numește pasul care duce la ea.
  Trei forme de funcții sunt scrise și verificate (`gen_sources.py FieldBytes.cpp FieldVarints.cpp FieldWrappers.cpp`):

| Fișier | Forma sursei | Funcții identice |
|---|---|---|
| FieldBytes.cpp | `if (p < end) { u8 x = *p; *cursor = p + 1; <lanț> *out = x; return true; } return false;` | 366 din 403 |
| FieldVarints.cpp | `*out = 0; for (int i = 0; *cursor < end; ++i) { u8 x = *(*cursor)++; <lanț> *out \|= (T)((x & 0x7f) << (i * 7)); if (!(x & 0x80)) return true; } return false;` (T = u16, u32) | 287 din 302 |
| FieldWrappers.cpp | `bool ok = <alt cititor>(out, cursor, end); for (u8* b = (u8*)out; b != (u8*)out + sizeof(*out); ++b) { u8 x = *b; <lanț> *b = x; } return ok;` (forma din memorie a câmpului) | 106 |

- Ce a contat la formă: ramura de succes scrisă prima (`if (p < end) {...} return false;`), deplasarea varint-ului ca
  `i * 7` cu contor (cu `shift += 7` inițializarea iese înaintea primei verificări), schimbul de biți în forma clasică
  `((x >> 1) & 0x55) | ((x & 0x55) << 1)`.
- **Complementul are două codări în client**: `not cl` vine dintr-un singur pas (`x = ~x`), iar `xor cl, 0xff` din doi
  pași sau-exclusiv la rând ale căror constante dau împreună 0xff (compilatorul îi unește târziu și nu mai face `not`);
  care două constante are sursa lui Riot nu se poate ști - orice pereche dă același cod (generatorul scrie 0x0f și 0xf0).
- **Locul scrierii cursorului** (`*cursor = p + 1`) printre pașii lanțului se vede în cod; generatorul compilează toate
  pozițiile într-un singur fișier și o păstrează pe cea identică (`gen_fields.pick`).
- Deschis: restul de ~1.500 de funcții mici au peste 1.000 de forme diferite (constructori de pachete care scriu valorile
  implicite deja codificate, cititori de câmpuri compuse), iar grosul celor 2,13 MB stă în cititoarele mari de pachete,
  unde lanțurile sunt puse direct în corpul funcției - pentru ele trebuie descrisă structura fiecărui pachet
  (`server/pkt_schema.py` o știe pentru pachetele învățate).
- **crashpad**: 231 de funcții (de la 182). Sursele lui stau, pe durata compilării, chiar la calea din build-ul Riot:
  linia `// tree: T:\p4\...\sentry-native = tools/third_party/sentry-native-0.4.17` dintr-o sursă generată face ca
  `match_func.mount_tree` să lege directorul nostru acolo (joncțiune sub `client-src/obj/mount_T`, arătată ca discul
  T: cu `subst`) și să elibereze discul la sfârșit. Utilizatorul a fost de acord cu montarea (2026-10-07).

**Continuare (2026-10-07, primele cititoare de pachete scrise din structura lor).** Trei funcții, verificate identic
(`match_func.py`), în `client-src/src/`:
- `Packet.h` + `PacketBase.cpp` - cititorul antetului, rva 0x83fee0 (46 de octeți; 46 de id-uri de pachet îl au drept
  cititor întreg): `const u8* p = *cursor; if ((u32)(end - p) < 6) return false; header4 = *(const u16*)p;
  header6 = *(const u32*)(p + 2); *cursor += 6; return true;`. Obiectul: tabelă virtuală, u16 la +4, u32 la +6
  (împachetare la 1 octet).
- `Packet182.cpp` - id 182, rva 0x88d110 (105 octeți): antetul (inline), un octet de biți, apoi
  `if (!(*p & 1)) { field10 = 0; return true; } return Read_805e00(&field0c, cursor, end) != 0;`.
- `Packet72.cpp` - id 72, rva 0x884270 (154 de octeți): la fel, dar valoarea implicită vine dintr-un octet global și e
  trecută prin lanțul din memorie al câmpului, printr-o funcție inline care primește **prin referință** câmpul și
  valoarea (`SetField(u8& field, const u8& value)`); cu pointer sau cu codul scris direct în cititor ies alte registre.
- Măsurat pe drum: cititoarele de câmp întorc ceva ce nu e `bool` (cititorul de pachet face `test al, al; setne al`),
  deci `FieldWrappers.cpp` le declară acum `char`.

Structura generală a unui cititor de pachet (417 cititoare distincte, ~1,2 MB): antet, unul sau mai mulți octeți de
biți, apoi pentru fiecare câmp „pe fir" (apelul cititorului de câmp) sau „implicit" (o valoare pusă direct, un apel de
inițializare, sau o valoare trecută prin lanț). **Limita metodei:** aproape fiecare cititor are altă schemă de control
(417 cititoare, 385 de scheme) - nu se pot scrie pe tipare de formă, ca funcțiile de câmp. Pentru a le genera trebuie
refăcută întâi „biblioteca de câmpuri" a lui Riot: tipurile de câmp (octet / număr codificat, șir, vector de
sub-obiecte cu cititor virtual la slotul 1, valori implicite ținute în statice locale) cu funcțiile lor inline, astfel
încât cititorul unui pachet să fie o sursă scurtă care se desface în codul clientului. Asta e munca următoare, câmp cu
câmp, pornind de la cititoarele cele mai mici (lista lor: `server/packet_emu.table()`, câmpul `des`).

**Continuare (2026-10-07, generator pentru cititoarele de pachet cu un singur câmp).** `gen_sources.py PacketReaders.cpp`
(`gen_fields.packet_readers`) recunoaște două feluri de cititor cu un câmp după antet - (a) un bit spune dacă câmpul e
pe fir (apel de cititor de câmp), altfel ia valoarea unei globale, trecută prin lanțul din memorie; (b) bitul e chiar
valoarea câmpului - scrie câteva variante de sursă pentru fiecare și o păstrează pe cea identică. Stare: 1 cititor
identic din 7 (rva 0x840340), plus cele scrise de mână (0x884270, 0x88d110).
- **Problemă deschisă, măsurată pe rva 0x868c40 (id 179):** structura iese corectă, dar clientul ține adresa câmpului
  în `eax` (`lea eax, [edi + 0xa]`), păstrează `this` în `edi` și salvează `ebx` abia în ramura valorii implicite;
  compilatorul nostru adună deplasarea în registrul lui `this` (`add esi, 0xa`) și ia `end` în alt registru. ~45 de
  forme încercate fără rezultat (ordinea ramurilor, valoarea prin referință / valoare / pointer, câmp ca obiect cu
  metode, biții citiți printr-o funcție ajutătoare, forme de buclă). La id 72 aceeași formă iese identică - diferența
  dintre cele două e sensul bitului și un pas de lanț care cere un registru în plus.
- Capcană de metodă regăsită: într-un fișier de probă, o funcție ajutătoare `inline` folosită de multe variante nu mai
  e desfăcută în toate (rezultate false de 114 octeți); fiecare variantă își primește propria copie.
- Clasificarea cititoarelor mici (95 de cititoare între 60 și 420 de octeți) după ingrediente: 17 au o valoare implicită
  ținută într-o statică locală și un sub-obiect cu cititor virtual (187 de octeți fiecare), 9 sunt de felul (b), 8 de
  felul (a), 12 citesc un vector de sub-obiecte prin slotul 1 al tabelei lor virtuale.

**Continuare (2026-10-07, cititoare de pachet cu valoare implicită într-o statică locală).** `gen_sources.py
PacketVectors.cpp` (`gen_fields.packet_vector_readers`): 11 cititoare de pachet identice (din 24 de acest fel; restul
au mai multe câmpuri) și 2 funcții de distrugere a staticii. Prima potrivire de mână: rva 0x8b7c80 (187 de octeți).
- **Forma:** câmpul e un obiect cu tabelă virtuală proprie (cititorul lui e slotul 1), iar valoarea implicită vine
  dintr-o funcție inline care întoarce o referință la o statică locală -
  `__forceinline const T& Default() { static const T def; return def; }` - deci o statică pe tip, împărțită de toate
  pachetele cu acel tip de câmp. Scrisă direct în cititor (`static const T def;` în ramură) nu dă codul clientului.
  `__forceinline` e necesar: cu mulți utilizatori într-un fișier, `inline` simplu nu mai e desfăcut.
- **Trei feluri de valoare implicită**, după ce face codul clientului:
  1. `field.value = Default();` - valoarea (la +4 în obiectul-câmp) e un vector propriu al lui Riot
     `{date, număr, capacitate}` cu atribuire prin copiere (parcurge elementele) și destructor; statica n-are
     constructor (se înregistrează doar destructorul);
  2. `field = Default();` - tot obiectul-câmp atribuit dintr-un obiect static construit la prima folosire;
  3. `field.value = Default().value;` - valoarea sunt 3 cuvinte de 32 de biți copiate unul câte unul: tipul valorii
     are propria atribuire, cuvânt cu cuvânt (un struct simplu ar fi copiat 8 + 4 octeți).
- Funcția înregistrată la `atexit` pentru statică e, la cele mai multe tipuri, chiar destructorul vectorului pus
  inline (parcurge elementele prin slotul 3 al tabelei lor virtuale, apoi eliberează memoria dacă bitul de sus al
  capacității e 0); tipurile generate îl declară doar, deci numai cele două care sunt un simplu salt sunt revendicate.

Scor măsurat după aceste runde (`tools/progress.py`, 2026-10-07): 16.806 funcții identice, 2.884.131 de octeți =
18,11% din cod; 16 scrise și încă neidentice; necercetat 79,19%.

**Continuare (2026-10-07, compunerea tipurilor de câmp și destructorii vectorilor).**
- `gen_sources.py VectorDestructors.cpp`: **73 de funcții identice**. `PacketVector.h` descrie elementul prin
  mărimea lui și destructorul virtual la slotul 3, plus stocarea `{date, număr, capacitate}`. Destructorul parcurge
  `for (auto p = data, end = data + count; p < end; ++p) p->~Element();`, apoi eliberează datele dacă
  `(int)capacity >= 0`. Se generează și `Clear()` (aceeași distrugere, urmată de zeroarea celor trei membri).
- Destructorii obiectelor care conțin vectori sunt **destructori virtuali `= default`**, emiși de compilator;
  cu un corp gol `{}` compilatorul scrie în plus tabela virtuală a clasei. Sunt descrise și combinațiile cu
  vectori de valori triviale, șiruri `RString`, vectori cu destructor separat și baza `BinObject` (a cărei tabelă
  se scrie la sfârșitul distrugerii). `Make_<tip>()` obligă compilatorul să emită tabela și destructorul;
  aceste funcții auxiliare nu sunt revendicate în scor.
- `PacketVectors.cpp`: **22 din cele 24 de cititoare recunoscute**, plus **4 destructori de statice** (fa6c00,
  fa6c10, fa6c40, fa6c90), față de 11 + 2. Valoarea unui câmp poate avea membri de 1, 2, 4 sau 8 octeți,
  goluri între membri, un bloc de 128 de octeți, șir și alți vectori. Atribuirea valorii e scrisă membru cu membru;
  blocul are atribuirea implicită a unui agregat (compilatorul emite `rep movsd`). Două încărcări de dword înainte
  de cele două scrieri indică un membru de 64 de biți. Atribuirea mare trebuie `__forceinline`, altfel devine apel.
  Spațiul staticii până la gardă păstrează și partea tipului încă nedescrisă; constructorii / destructorii
  câmpurilor care nu au fost refăcuți rămân declarații, nu funcții revendicate.
- `FieldValidated.cpp`: **2 funcții identice**, rva 0x79c490 și 0x79c730. Un enum de un octet este citit,
  verificat (`0 < valoare < 0x34`), înlocuit cu globala 0x36f73cc dacă citirea / verificarea eșuează, apoi trecut
  prin lanțul din memorie în ambele cazuri. Sursa: `bool ok = Read(...) && *out != 0 && *out < 0x34;
  if (!ok) *out = default; <codificare>; return ok;` (funcția întoarce `char`).
- `PacketBits.h/.cpp`: funcția de extragere a biților, rva 0x91cae0, **101 octeți identici**. Argumentele sunt
  adresa octeților de biți, poziția de început (`u8`), numărul de biți (`u8`); sunt tratate și intervalele care
  trec în octetul următor. Numele `GetBits_91cae0` e al nostru.
- `match_func.py`: metadatele COFF se citesc o singură dată pe versiune de obiect, într-un cache limitat la 32
  de obiecte, cu cheia (cale, data modificării în nanosecunde, mărime). Indicii de simboluri și limitele funcțiilor
  sunt păstrați; țintele relocărilor și constantele se refac la fiecare apel. Verificat față de parserul anterior
  pe **199 de comparații** (inclusiv MetaFunctions, crashpad cu etichete anonime și OpenSSL cu constante), cu
  aceiași octeți, relocări, ținte, constante și erori de simbol ambiguu / absent; recompilarea aceluiași obiect
  invalidează cache-ul. Trei teste permanente (`python -m unittest discover -s tools -p test_match_func.py`)
  verifică delimitarea prin funclete EH, selecția exactă / ambiguă, țintele și constantele la schimbarea funcției,
  precum și rescrierea unui obiect de aceeași mărime. Regulile de acceptare a unei potriviri nu s-au schimbat.

**Rămas deschis în această rundă:** cele două cititoare rva 0x898110 și 0x8afc50 (363 de octeți), cu un enum
la +0xa urmat de un obiect-câmp la +0xb. Primul câmp și extragerea bitului celui de-al doilea sunt refăcute;
forma cea mai apropiată are 362 de octeți. Clientul încheie apelul virtual cu `test al, al; je <eșec>; ... mov al, 1`,
compilatorul nostru comprimă ultimul rezultat în `setne al`. Ramura implicită trebuie scrisă prima și aici.
Variantele `switch`, bucle cu o singură iterație, rezultat local, `goto`, lambda și întoarcere `char` nu au
rezolvat această diferență. Niciuna dintre aceste două funcții nu este trecută în scor.

**Scor final al rundei (2026-10-07, toate sursele recompilate cu `tools/progress.py`):** **16.895 funcții
identice, 2.892.642 de octeți = 18,16% din cod**, față de 16.806 / 2.884.131 / 18,11%: **+89 de funcții,
+8.511 octeți**. Cele 16 funcții scrise și neidentice au rămas 16; necercetat 79,14%. Verificarea separată a celor
102 funcții din cele patru fișiere ale rundei confirmă toate potrivirile și niciun simbol plasat la adrese diferite.
Au fost verificate și celelalte funcții revendicate: niciuna nu apelează direct funcțiile nou revendicate, deci
nu există un apel vechi rămas sub alt nume. Logul complet: `client-src/progress-2026-10-07-final.log`.
Rularea finală, cu parserul COFF optimizat, a durat aproximativ **5 minute** pe această mașină; compilarea tuturor
surselor și verificarea tuturor țintelor au rămas active. Paritatea integrală de sursă nu este încă atinsă.

**Continuare (2026-10-07, tipuri de câmp comune și constructori de pachete).**
- `tools/gen_field_classes.py`, apelat prin `gen_sources.py FieldClasses.h FieldConstructors.cpp`: schema
  constructorului vine din adresele membrilor, scrierile valorilor inițiale și limitele buclelor de codificare.
  Toate scrierile din afara buclelor trebuie explicate. Un membru codificat are propriul constructor inline,
  care inițializează valoarea, apoi îi codifică octeții. Sunt recunoscute și stocarea șirului gol `RString`,
  vectorul de valori triviale de la +0x14 în tipul construit la 0x7b8280 și antetul de pachet.
- **146 de constructori identici** (din 434 de scheme recunoscute), în clase comune definite de `FieldClasses.h`.
  Cinci sunt obiecte-câmp: 0x312be0, 0x7b8280, 0x7ba160, 0x7bb840, 0x7e91a0. Celelalte **141 sunt pachete**.
  Constructorii pachetelor folosesc baza `C2S_Base`, împachetată la un octet: tabelă virtuală, u16 la +4,
  u32 la +6; constructorul primește id-ul și valoarea implicită a net-id-ului prin referință. Membrii codificați
  se construiesc după bază. Exemplu: id 782, rva 0x13ca80, **323 de octeți identici**.
- **Cauza respingerii primelor probe de pachete era numele tabelei, nu codul.** `names.tsv` folosește etichete
  `C2S_782_vtable`, iar compilatorul scrie simbolul `??_7C2S_782@@6B@`. Clasele de pachet folosesc acum exact
  numele din hartă; `match_func.same_thing` traduce doar această formă exactă. O clasă cu alt id, alt sens C2S/S2C
  sau un nume de probă rămâne o țintă diferită. Test permanent pentru aceste cazuri negative.
- Slotul 0 al tabelei virtuale este scrierea în buffer (un argument, `ret 4` la implementările goale); slotul 1
  este citirea; slotul 2 întoarce mărimea obiectului, care stabilește și coada încă nedescrisă a clasei; slotul 3
  este destructorul de ștergere scalară, emis de compilator din `virtual ~T() = default`.
  **FieldConstructors.cpp revendică 178 de funcții distincte, 33.425 de octeți**, incluzând constructorii,
  getterii de mărime, destructorii și scrierea goală. Alte **380 de nume contopite** sunt înregistrate ca
  `// same:`: fiecare a fost compilat și verificat separat, nu numărat ca funcție nouă.
- Tipurile construite de mână în cititoarele de pachete sunt înlocuite, unde există constructorul verificat,
  cu tipul comun din `FieldClasses.h`. Cele **22 de cititoare** au rămas identice. Atribuirea clasei copiază
  membrii stocați, fără să copieze tabela virtuală; trebuie folosită sintaxa `field = Default()`.
  `field.AssignValue(Default())` calcula receptorul înaintea staticii, păstra încă un registru și nu ieșea
  identic. În C++17, atribuirea evaluează întâi operandul din dreapta.
- Destructorii impliciți ai tipurilor comune au refăcut încă **3 callbacks de statice**: 0xfa6f50 (`ret 0`),
  0xfa6e50 (salt la destructorul șirului de la +4), 0xfa6b40 (eliberează vectorul, apoi distruge șirul).
  `PacketVectors.cpp` are acum **29 de funcții revendicate** (22 cititoare + 7 callbacks), 4.840 de octeți.
- `RString`: constructor implicit inline din pointerul comun la șirul gol, lungime 0, capacitate 0;
  `Clear`, rva 0x9c01f0, **20 de octeți identici**, și `Resize`, rva 0x9da2a0, **45 de octeți identici**.
  `Clear` nu schimbă nici lungimea dacă datele sunt chiar literalul gol; `Resize` schimbă lungimea în toate
  cazurile, dar nu scrie terminatorul în literal. `Reserve` trebuie să fie într-o unitate separată: definit în
  același fișier, compilatorul îl desfăcea în `Resize`, care devenea 130 de octeți în loc de 45.

**Încă deschis:** constructorii cu primul membru u32 (ex. 0x7e5970): 185 de octeți, dar două scrieri inversate
(tabela virtuală și valoarea zero). Formele cu bază, un membru compus, constructori definiți în afara clasei,
argumente prin valoare / referință, destructori, alte numere de sloturi și opțiuni de inlining nu au rezolvat
ordinea. `RString::Reserve` a fost rezolvat ulterior în aceeași rundă (mai jos). Cititoarele obiectelor-câmp noi sunt de 651–2.192 de octeți și combină șiruri în mai multe
ordini de citire cu formate de 3 biți pentru scalari (constante speciale și cititoare de pe fir); urmează refacerea
acestei biblioteci. Cele două cititoare 0x898110 / 0x8afc50 rămân de asemenea deschise.

**Continuare în aceeași rundă: șiruri și alocare.** `RStringReserve.cpp`, rva 0x9cd2a0, **108 octeți identici**:
`proposal = available + available / 2; grown = length > proposal ? length : proposal;
grown = (grown + 1) & ~1u;`. Se alocă `grown + 1`, se copiază manual intervalul `[data, data + size)`, se scrie
terminatorul, se eliberează vechiul buffer doar dacă bitul 0 al capacității este 1 și se păstrează `grown | 1`.
Forma `if` și `std::max` aleg alte registre; expresia ternară produce exact codul clientului. Păstrat în altă
unitate decât `Resize`, care trebuie să conțină apelul.

`RStringAssign.cpp`, rva 0x9be7d0, **135 de octeți identici**: atribuirea copiază caracterele în stocarea proprie,
rotunjește capacitatea cerută la un număr par și inițializează pool-ul la prima alocare. **Operatorul de atribuire
întoarce `void`**, nu referință: forma care întorcea `*this` avea 137 de octeți, dintre care primii 129 identici,
și adăuga `mov eax, esi` la sfârșit. Dacă nu trebuie crescut bufferul și datele sunt literalul gol, operatorul
întoarce imediat, fără să modifice nici lungimea. `StringPool::Allocate`, starea pool-ului și inițializatorul său
sunt încă declarații / globale externe; nu sunt revendicate ca implementări refăcute.

**Scor complet final (2026-10-07, `tools/progress.py`, toate sursele recompilate): 17.080 de funcții identice,
2.926.421 de octeți = 18,38% din cod**, față de 16.895 / 2.892.642 / 18,16% la începutul rundei:
**+185 de funcții, +33.779 octeți**. Cele 16 funcții scrise și încă neidentice au rămas 16; necercetat 78,92%.
Log: `client-src/progress-2026-10-07-classes-strings-final.log`.

Verificarea separată a tuturor liniilor `// match:` și `// same:` din noile clase, cititoarele care le folosesc
și șiruri a trecut; nu există simboluri de relocare plasate la adrese diferite. Cele patru teste COFF / identitate
ale tabelelor au trecut. Generatorul nu acceptă inițializări numerice care sunt de fapt o tabelă virtuală a unui
sub-obiect: pentru ele trebuie descris propriul tip. Aliasurile de destructori / getteri sunt verificate în obiectul
complet înainte de a fi emise; o funcție respinsă nu poate fi strecurată ca `// same:` într-o trecere ulterioară.
Obiectivul parității integrale rămâne activ; acest scor dovedește doar partea refăcută până aici.

**Continuare (2026-10-07, cititoare scalare, booleene și enum-uri).**

`tools/gen_packet_scalars.py`, apelat prin `gen_sources.py`, folosește clasele complete din `FieldClasses.h`:
schema constructorului dă offsetul, mărimea și codificarea membrului, iar slotul 1 al tabelei virtuale dă cititorul.
Ordinea testelor formatului și constantele sunt extrase din controlul de flux. Sunt recunoscute formatele de
1 / 2 / 3 biți, două ramuri booleene și cazul enum cu valoare implicită globală. Funcțiile emise sunt metode
ale acelorași clase care au constructorii verificați.

| Fișier | Funcții distincte identice | Octeți de cod |
| --- | ---: | ---: |
| `FieldBytes.cpp` | 415 | 40.280 |
| `FieldWrappers.cpp` | 161 | 18.711 |
| `FieldInlineEnums.cpp` | 3 | 410 |
| `PacketScalars.cpp` | 12 | 4.776 |

- Filtrul pentru cititoarele de octeți acceptă acum și cursorul ținut în `ecx`, pe lângă `edx`.
  Recunoașterea acestei forme aduce **42 de funcții noi**. Ordini echivalente ale XOR-ului și permutărilor
  de biți aduc încă **3**: de exemplu `x ^= 4; x = Swap1(x);` și `x = Swap1(x); x ^= 8;` au aceeași valoare,
  dar instrucțiunile se programează diferit. `equivalent_bit_chains` încearcă ambele ordini; fiecare rezultat
  acceptat trece comparația completă. `test_gen_fields.py` verifică toate cele 256 de valori, toate măștile
  XOR, ambele sensuri de mutare și permutările relevante, inclusiv lanțuri compuse și complemente.
  O valoare temporară `u32` la citire aduce încă **4 potriviri** prin încărcarea `movzx`; indexarea tabelelor
  este trunchiată explicit la `u8`, iar helperii de permutare și scrierea rezultatului păstrează semantica de octet.
  Totalul crește de la 366 la 415, adică **49 de cititoare noi**.
- Filtrul buclelor din cititoarele de câmp acceptă și `movzx`, pe lângă `mov` într-un registru de 8 biți.
  `FieldWrappers.cpp` trece de la 106 la **158 de funcții**, adică **52 noi**. Cinci probe rămân respinse la
  comparație. Cititoarele dependente au fost regenerate cu numele cititoarelor nou reconstruite.
  Sunt recunoscute ulterior și formele care păstrează rezultatul în `ah`, încep prin `push esi` și salvează
  `ebx` doar când intră în bucla de codificare: încă **3 funcții**, total **161**, inclusiv 0x79c410 (114 octeți).
- `FieldInlineEnums.cpp`: **0x79c530, 127 de octeți**, și **0x79c870, 135 de octeți**, identici. Citirea de pe
  fir este într-un helper `__forceinline bool`, urmată de `*out != 0 && *out < 0x34`; la eșec se atribuie
  `g_36f73cc`, apoi se codifică valoarea în memorie în toate cazurile. Funcția exterioară întoarce `char`.
  Poziția atribuirii cursorului în lanțul helperului contează și se verifică prin variante de sursă.
  **0x79c7d0, 148 de octeți**, este rezolvat tot cu helperul inline, dar temporara citită trebuie să fie
  `u32`: clientul începe prin `movzx edx, byte ptr [ecx]`. Cu `u8`, proba avea aceeași mărime datorită alinierii
  buclei, dar începea prin `mov dl, byte ptr [ecx]` și deplasa instrucțiunile dinaintea buclei cu un octet.
  Apelul din `Packet72.cpp` folosește acum corpul verificat `ReadValidated8_79c530`; pachetul păstrează
  **154/154 de octeți identici**, inclusiv ținta apelului.
- Antetul care iese identic în cititoarele scalare este un **helper liber inline care întoarce `bool`** și
  primește `C2S_Base&`: verifică șase octeți, scrie `header4` / `header6`, apoi face `*cursor += 6`.
  Metoda de pachet întoarce `char`. Forma de membru care întorcea `char` producea altă actualizare a cursorului.
- Valorile implicite folosesc un setter inline cu câmpul și valoarea prin referință, urmat de bucla de codificare.
  Sunt necesare două forme pentru limita buclei: `&field + sizeof(field)` și un pointer final primit separat,
  calculat din `this + offset + size`. **S2C_305, 0x851af0, 419 octeți**, cere limita separată la constantele
  nenule și limita din câmp la zero. Cu o singură formă pentru toate constantele ieșeau 413 sau 417 octeți.
  Constantele sale reprezintă biții float pentru 1, 0, -1 și 2.
- Formatele care citesc de pe fir păstrează apeluri distincte în lanțul ordonat `if / else if`. Dacă sursa
  folosește același nume de funcție pentru toate formatele, compilatorul unește ramurile: de exemplu S2C_614
  devenea 347 de octeți, în loc de **412 identici**. `FieldFormatAliases.h/.cpp` definește **50 de corpuri
  obișnuite C++**, numite pe format, fiecare compilat și verificat separat la adresa comună din client.
  Acest comportament este compatibil cu funcții contopite de linker; numele și specializările originale nu
  sunt cunoscute. Aliasurile sunt marcate `// same:` și nu adaugă funcții distincte la scor.
- `PacketScalars.cpp` include cele șapte cititoare numerice S2C_213 / 614 / 305 / 150 / 665 / 779 / 158,
  enum-ul **S2C_183, 0x8b1d00, 208 octeți**, și booleenele **S2C_20, 0x8c8000, 285 octeți**, respectiv
  **C2S_319, 0x8d6d70, 249 octeți**. Extinderea cititoarelor de câmp aduce și **S2C_731, 0x841350,
  414 octeți identici**.
- **S2C_783, 0x8edb40, 420 de octeți identici**: pentru constante, setterul trebuie să primească
  `short& field, const short& value`. Stocarea comună păstrează biții în `u16`; setterul o accesează prin
  tipul signed corespunzător, `(short&)fielda.value`. La -1, această formă dă `or eax, 0xffffffff`, apoi
  scrierea cuvântului. Setterul unsigned avea 422 de octeți și folosea `mov eax, 0xffff`. Schimbarea doar a
  tipului argumentului valorii la u32 / int nu ajungea; contează și tipul referinței câmpului. Extractorul
  constantelor recunoaște acum și `or <reg>, 0xffffffff`. Total: **12 potriviri din 18 scheme**.
- Ordinea implicită a generatorului pune cititoarele de câmp și clasele înaintea aliasurilor și metodelor
  scalare. Regenerarea familiei: `python tools/gen_sources.py FieldBytes.cpp FieldWrappers.cpp
  FieldInlineEnums.cpp FieldFormatAliases.h FieldFormatAliases.cpp PacketScalars.cpp`.

**Verificare:** toate cele **1.239 linii `// match:` / `// same:`** din cititoarele de câmp, aliasuri, pachete,
constructori și șiruri auditate au trecut comparația; niciun simbol de relocare nu este plasat la adrese diferite.
Auditul include `Packet72` după actualizarea numelui enum-ului. Cele patru teste COFF și cele trei teste pentru
lanțuri echivalente au trecut.

**Încă deschis în familia nouă:** S2C_444 / 0x842b80, S2C_334 / 0x8b1810 și C2S_553 / 0x8db700 au dimensiunea
corectă, dar ordinea celor două produse din inversarea biților diferă. Schimbarea ordinii termenilor în expresia
  C++ a fost normalizată de compilator și nu a rezolvat diferența. S2C_605 / 0x8bc6f0 și S2C_581 / 0x8e1220
mai diferă în registrele buclelor; S2C_179 / 0x868c40 are 161 octeți în proba cea mai apropiată, față de 164 în
client, și alte registre. Cititoarele cu mai mulți membri și formate de citire în ordini diferite rămân următoarea
familie de extins.

**Limită identificată în indexul funcțiilor:** `functions.txt` include 0x89fde0 ca început separat în interiorul
`S2C_240_Read`, 0x89fcb0. Instrucțiunea de la 0x89fde0 este un salt la 0x89fdf5, unde se curăță argumentele
apelului deja pregătit în prefix; este o continuare a controlului de flux. Indexul dă astfel un prefix de
304 octeți și un segment de 352, până la următorul cititor numit, S2C_188 / 0x89ff40. Corpul contiguu are
656 de octeți și două câmpuri scalare. Generatorul actual citește numai prefixul. Extinderea trebuie să descrie
corpul complet și să verifice limitele / acoperirea înainte de a revendica această funcție.

Auditul separat al intervalelor prefixelor egale la nivel de octet nu găsește suprapuneri între revendicări.
El găsește însă **94 de adrese revendicate absente din index** și **139 de limite diferite** la adrese deja
indexate: 19 corpuri compilate depășesc limita dată de index, iar 120 se termină mai devreme. Exemple:
Crashpad `DeleteReport`, 0xc9f670, corp de 461 octeți / interval indexat de 74; FreeType `TT_Get_MM_Var`,
0xbc6ad0, 1.597 / 1.082; `Read@C2SPacket`, 0x146910, 5 / 230. Acesta este un diagnostic al limitelor;
scorul de mai jos include separat verificarea țintelor de relocare. Datele auditului sunt păstrate în
`client-src/obj/source-range-audit.json`. Corectarea indexului și evidența acoperirii intervalelor rămân deschise.

**Scor complet final (2026-10-07, `tools/progress.py`, toate sursele recompilate): 17.199 de funcții identice,
2.942.725 de octeți = 18,48% din cod**, față de 17.080 / 2.926.421 / 18,38% la începutul acestei continuări:
**+119 funcții, +16.304 octeți**. Cele 16 funcții scrise și încă neidentice au rămas 16; necercetat 78,82%.
Față de scorul inițial comunicat, 16.806 / 2.884.131 / 18,11%, progresul cumulat este **+393 de funcții,
+58.594 de octeți**. Log: `client-src/progress-2026-10-07-scalars-signed-final.log`.
Paritatea integrală de sursă rămâne obiectiv activ.

**Continuare (2026-10-07, corpuri complete de cititoare și acoperire pe intervale).**

- `FieldInline.cpp`, generat prin `gen_sources.py FieldInline.cpp`, aduce **17 cititoare de câmp distincte,
  2.252 de octeți identici**. Citirea unui octet de pe fir este într-un helper `__forceinline bool`; funcția
  exterioară păstrează rezultatul, codifică octetul din memorie în toate cazurile și întoarce `char`.
  Sunt extrase separat codificarea de pe fir și codificarea din memorie; poziția actualizării cursorului și
  tipul u8 / u32 al temporarei de pe fir sunt încercate la compilare. Exemplu: **0x7971e0, 82 octeți**.
- Emulatorul din `gen_fields.py` tratează acum și **ah / ch / dh / bh**, cu deplasarea de opt biți și
  păstrarea celorlalți biți ai registrului. În 0x795fb0 și 0x796fc0, `mov dh, 1` salvează rezultatul boolean,
  iar `dl` continuă să conțină octetul citit. Această instrucțiune bloca anterior extragerea lanțului.
  Testul verifică separat păstrarea octetului jos și a adresei de ieșire.
- `tools/gen_packet_multi.py` extrage formatele în ordinea citirii și urmărește adresele de ieșire până la
  membrii clasei. Toate valorile formatului trebuie explicate și toți membrii trebuie acoperiți o singură dată.
  `packet_instructions` urmărește ramurile locale și permite intrări fără nume ale indexului în interiorul
  corpului. Nu intră în funcțiile apelate; funcția numită următoare și limita de 16 KiB delimitează căutarea.
  Salturile indirecte și ramurile condiționale în afara acestei regiuni rămân nesuportate. Patru teste verifică
  continuarea peste o limită falsă, apelurile, limitele numite și terminarea buclelor.
- **S2C_240_Read, 0x89fcb0, 656/656 octeți identici**, în `PacketMultiScalars.cpp`. Corpul include continuarea
  de la 0x89fde0. Primul format folosește biții 3–5 și membrul de un octet de la +0xa; al doilea folosește
  biții 0–2 și membrul u32 de la +0xc. Constantele și ordinea ramurilor sunt cele extrase din client.
  Cititoarele de pe fir sunt 0x7971e0 și 0x79bfd0, cu nume separate pe format și corpuri verificate.
- Extragerea formatului trebuie să folosească forma helperului `GetBits_91cae0`, desfăcută inline.
  Expresia directă `(*presence >> 3) & 7` producea `and al, 0x38` și comparații cu valori deplasate;
  helperul produce `shr al, 3; and al, 7`, identic cu clientul. Pentru membrul u32, `RevPromoted(u32 b)`
  cu constante unsigned U rezolvă ordinea celor două produse după XOR-ul 0x89. Apelul primește explicit
  `(u8)x`; operațiile unsigned și byte-ul rezultat păstrează exact permutarea. Toate cele 256 de valori
  sunt verificate față de definiția inversării biților.
- **S2C_334_Read, 0x8b1810, 563 de octeți identici**, este rezolvat prin temporara `u32 x` în bucla
  setterului, cu indexarea tabelei trunchiată explicit la u8. `PacketScalars.cpp` are acum **13 cititoare,
  5.339 de octeți**. Tipul temporarei contează separat de tipul parametrului helperului de inversare.
- `FieldFormatAliases.h/.cpp` include și cititoarele cu helper de fir inline; copia pe format cuprinde
  ambele funcții de sursă, cu numele helperului schimbat consecvent. Sunt **72 de aliasuri**, fiecare cu
  corpul compilat verificat; rămân marcate `// same:`. Ele nu adaugă funcții distincte la scor.
- `tools/code_coverage.py` și `progress.py` atribuie acum **intervale de octeți**, în ordinea categoriilor.
  O continuare complet acoperită nu reapare la codul rămas; un prefix scurt păstrează restul intervalului
  ca neacoperit. Intervale suprapuse sunt numărate o singură dată și se exclude padding-ul deja exclus de
  inventarul vechi. Șase teste acoperă corpul 304 + 352, prefixul 5 / 230, funcția absentă din index,
  suprapunerile și padding-ul. Verificarea binară a funcțiilor și a țintelor rămâne aceeași.
  Rândurile finale sunt `uncovered (function index entries)` și `all (index + verified code)`; numărul de intrări
  în index nu este numărul de funcții reale și nu trebuie însumat cu numele reconstruite.

**Verificare:** **1.567 de revendicări și aliasuri** din cititoare, constructori, pachete și șiruri au trecut,
fără simboluri plasate la adrese diferite. Toate cele **19 teste** au trecut. Cele 22 de cititoare de vectori
și cele șapte callbacks au rămas identice.

**Încă deschis:** în familia numerică multiplă sunt recunoscute și S2C_192 / 0x88b2a0 (1.045 octeți) și
S2C_418 / 0x8f4090 (1.071), dar probele diferă în încărcările din stivă, registre și codificare.
S2C_444 / 0x842b80 și C2S_553 / 0x8db700 păstrează problema ordinii produselor. Variantele cu parametri
u8 / u32 / unsigned long / int / u64 / referință, valori întoarse u8 / u32 / int, ordine inversată a termenilor
și temporare mai largi nu au produs potriviri pentru aceste două cititoare. Booleenele S2C_605 / S2C_581,
enum-ul S2C_179 și formatele cu enum-uri inline, șiruri sau mai mulți octeți de prezență rămân de extins.
Indexul original nu a fost rescris; acoperirea în octeți este acum raportată separat de limitele sale imperfecte.

**Corecție suplimentară a inventarului de cod:** auditul a găsit un octet verificat exclus de vechea regulă
pentru padding: **0xcae022**, instrucțiunea `int3` din `logging::LogMessage::~LogMessage`, 0xcade60,
înaintea instrucțiunii `ud2`. Corpul compilat are 541 octeți și include acest `int3`; nu este padding.
Inventarul este acum reuniunea intervalelor din index și a corpurilor compilate **complet verificate**, limitată
la regiunea text cunoscută. Candidații neidentici și formele de bibliotecă nesigure nu extind inventarul.
Totalul se corectează de la **15.925.651 la 15.925.652 de octeți**. Test separat pentru acest caz.

**Scor complet final (2026-10-07, toate sursele recompilate): 17.218 funcții identice, 2.946.196 de octeți,
18,50% din inventarul de cod corectat.** Față de începutul acestei continuări: **+19 funcții, +3.471 octeți**.
Cele 16 implementări încă neidentice au rămas 16 / 2.471 octeți. Restul neacoperit este **12.687.690 octeți,
79,67%**, în 47.932 de intrări de index care mai au octeți neacoperiți. Acest rest include acum și cozile omise
de vechiul calcul pe etichete, deci nu se compară direct cu vechiul rând `not looked at` / 78,82%.
Log: `client-src/progress-2026-10-07-multi-coverage-trap-final.log`. Paritatea integrală de sursă rămâne activă.

**Continuare (2026-10-07, forme de sursă pentru transport și auditul relocărilor).**

- `PacketMultiScalars.cpp` are acum trei cititoare. **S2C_192 / 0x88b2a0: 1.045/1.045 octeți** și
  **S2C_418 / 0x8f4090: 1.071/1.071** sunt identice. Forma care elimină salvarea și reîncărcarea pointerului
  de prezență este verificarea spațiului urmată de `const u8* presence = (*cursor)++;`. Copierea pointerului
  înaintea verificării și avansarea ulterioară prin `*cursor = presence + 1` rămân forma corectă pentru
  S2C_240. Variantele const, uintptr, void*, signed char*, accesul direct și referința la header nu rezolvau
  diferența. Generatorul încearcă ambele forme de avansare și verifică rezultatul compilat.
- `Object2e30e0::IsValid`, **0x2e30e0: 24/24**, compară un singur membru `u64` cu
  `0x00000000ffffffffULL`. Două comparații C++ între membri u32 produceau 23 de octeți și alte salturi.
- `Wrapper2df320::Forward`, **0x2df320: 18/18**, primește un `long long` și întoarce referința la datele
  asociate cheii. Callee-ul 0x2df220 compară cheia pe 64 de biți și întoarce datele nodului de hartă la +0x18.
  Doi parametri u32, chiar reuniți în corp într-un u64, produceau alt cod; parametrul scalar pe 64 de biți
  reproduce secvența de apel. Variantele void, int, pointer și referință ale rezultatului au trecut proba;
  referința este forma păstrată, compatibilă cu datele nodului.
- `DatagramHandler2e1d70::HandleDatagram`, **0x2e1d70: 42/42**, este metodă de instanță.
  `HandleAck` / 0x2ed360 și `HandleSeq` / 0x2ee8a0 consumă ECX-ul instanței. Vechea funcție liberă
  `__stdcall` și helperii liberi produceau alte registre. Metoda citește numărul semnat de 16 biți și
  întoarce 4 pentru ACK, 0 pentru SEQ și 1 pentru zero.
- Aliasul **`_ZSTD_isError`, 0xc4c6c0: 14/14**, este verificat în `zstd_common.c`, cu `-O2`.
  Adresa era revendicată sub numele helperului static `_ERR_isError` din altă unitate. Aliasul funcției
  publice este susținut acum de corpul ei compilat, iar regenerarea `Zstd.txt` îl verifică și îl păstrează.
  Astfel `LnpCompression::Compress`, **0x2e2a70: 147/147**, și `Decompress`, **0x2e2020: 99/99**,
  trec și verificarea țintelor. Aliasul nu numără încă o funcție distinctă.
- `progress.py --audit <fișier.json>` salvează din aceeași rulare completă sursa, simbolul, RVA-ul,
  opțiunile de compilare și diferența fiecărei revendicări nereușite. Comanda fără argumente păstrează
  comparația și scorul obișnuite. Raport: `client-src/progress-2026-10-07-transport-audit.json`.

**Scor complet intermediar (2026-10-07): 17.225 funcții identice, 2.948.642 octeți, 18,52%.**
Față de 17.218 / 2.946.196: **+7 funcții, +2.446 octeți**, dintre care cinci diferențe vechi închise și
două cititoare noi. Rămâneau 11 implementări neidentice / 2.153 octeți; neacoperit 12.685.562 / 79,65%.
Log: `client-src/progress-2026-10-07-transport-final.log`. Auditul local al celor 46 de revendicări relevante
a trecut pentru 45; `Clone` / 0x2f2780 era singura diferență preexistentă din acest grup.

**Probe nereușite care rămân utile:** `Clone` / 0x2f2780 a fost încercat cu câmpuri u32, pointer, bool,
pointer de funcție și de membru, variante const și copiere implicită / placement new. Clientul păstrează
sursa în ESI și byte-ul în CL; probele nu reproduc ambele. `LnpWorker::Post` / 0x2dd220 și 0x2dd2d0 nu
s-au potrivit prin preîncărcarea proprietarului / ceasului sau schimbarea standardului C++14 / latest.
Aceste probe nu au înlocuit sursele revendicate.

**Continuare (2026-10-07, constructori reflectați și verificarea corpurilor aliasurilor).**

- Patru inițializări de metadate aveau octeții corecți, dar nu și ținta simbolului `MetaConstruct`:
  `SkinSummonerEmoteLoadout` / 0x950f0, `RegaliaRankedCrestEntry` / 0x96910,
  `SpellEffectAmount` / 0xb2d40 și `InputControlSet` / 0xd9100. Adresele constructorilor erau deja
  revendicate sub nume de bibliotecă; tipurile opace produceau doar un corp de cinci octeți fără inițializare.
- `SkinSummonerEmoteLoadout`, **0x223dd0: 20/20**, inițializează **primii 40 din cei 80 de octeți**.
  Constructorul inline cu `std::memset(unknown00, 0, 40)` reproduce două stocări de 16 și una de 8 octeți.
  Ceilalți 40 nu sunt inițializați. Inițializarea valorică a întregului tip producea un apel memset de 80.
- `SpellEffectAmount`, **0x509b10: 23/23**, folosește blocul de 28 de octeți; `InputControlSet` și
  `RegaliaRankedCrestEntry`, **0x24dc80: 53/53**, folosesc șapte membri u32 cu inițializatori zero.
  Un memset de 28 sau șapte apeluri memset de câte patru erau reunite în instrucțiuni SSE și nu se potriveau.
- `zero_construct` din `gen_meta.py` acceptă numai încărcarea argumentului în EAX, stocări zero într-un
  prefix contiguu și un return necondiționat. Respinge goluri, suprapuneri, stocări nenule, apeluri și depășirea
  mărimii obiectului. Păstrează separat formele cu membri scalari și cu blocuri SSE. Un index care lipește
  cod după primul `ret` nu extinde acest constructor fără ramuri. Patru teste verifică aceste condiții.
- Generatorul instanțiază acum **și șabloanele aliasurilor**, apoi compară fiecare corp. Auditul inițial al
  celor 3.905 aliasuri de șabloane din `MetaFunctions.cpp` a găsit **22 de corpuri neidentice**, ascunse
  anterior de simpla egalitate a adreselor. Raportul este `client-src/obj/meta-all-alias-audit.json`.
  Aliasurile care nu trec comparația sunt eliminate; nu sunt declarate identice numai pentru că indexul
  plasează alt simbol la aceeași adresă. Revendicările `// match:` se verifică în continuare separat.
- Eliminarea lor a expus 19 inițializări de metadate care depindeau de formele incorecte. Formele de sursă
  investigate sunt constructorii cu membri scalari, atribuirea separată a valorilor `HashValue` și destructorii
  care resetează un prefix al obiectului. Atribuirea `member.value = 0` reproduce stocările separate;
  inițializarea agregată `{0}` producea grupări SSE în `ExtraJointChainData`,
  `ItemRecommendationOverrideContext` și `ParticleEventDataPair`.

**Rezultatul corecției aliasurilor:** toate cele **3.876 de inițializări revendicate în `MetaClasses.cpp`**
trec comparația. În `MetaFunctions.cpp`, toate cele **5.770 de revendicări și aliasuri de șabloane** trec
cu corpuri efectiv instanțiate și compilate. Cele 22 de aliasuri vechi neidentice au fost reparate prin definițiile
claselor; aliasurile suplimentare încercate și nereușite nu sunt păstrate. Exemple: destructorul care șterge
primii patru octeți produce **0x127aa0: 11/11**, iar constructorul cu atribuiri separate ale celor trei membri
produce **0xf1250: 25/25**. Constructorul `DefaultStatModPerkSet` de la 0x1dba10 se termină înaintea
următorului `push 0x98`, lipit de index; cei patru membri u32 inițializați sunt descriși separat.

O măsurare intermediară după eliminarea aliasurilor greșite, înaintea acestor corecții, a dat
**17.219 / 2.947.502 / 18,51%**, cu 26 de implementări neidentice. Această scădere a expus revendicările
dependente și nu a fost ascunsă prin aliasuri noi fără corp. Log: `client-src/progress-2026-10-07-meta-final.log`;
raport: `client-src/progress-2026-10-07-meta-audit.json`.

**Verificare suplimentară:** toate cele **23 de teste** ale emulatorului de câmp, cititorului COFF,
fluxului pachetelor, acoperirii și extragerii constructorilor au trecut. Scripturile modificate trec `py_compile`.
Probe cu `__restrict`, parametru pointer, referință volatile și ipoteze de nealiasare pentru `LnpMessage::Read`
nu au rezolvat registrele; primele trei rămân la 282/360, iar ipotezele produc un corp mai lung.
Sursele revendicate nu au fost înlocuite cu aceste probe.

**Scor complet final (2026-10-07, toate sursele recompilate): 17.238 funcții identice,
2.949.462 octeți, 18,52% din 15.925.652.** Față de începutul acestei continuări,
17.218 / 2.946.196: **+20 funcții, +3.266 octeți**. Extinderea metadatelor aduce nouă funcții distincte
de creare / construire, 394 de octeți, și repară cele patru inițializări vechi, 426 de octeți.
Față de scorul inițial comunicat, 16.806 / 2.884.131 / 18,11%, progresul cumulat este
**+432 funcții, +65.331 octeți**. Log: `client-src/progress-2026-10-07-meta-verified-final.log`;
diferențele exacte: `client-src/progress-2026-10-07-meta-verified-audit.json`.

**Cele șapte implementări scrise și încă neidentice, 1.727 octeți:**

- `LnpAppObserver::Update`, 0x2ec600: 509 octeți; cadrul stivei și pozițiile temporarelor diferă.
- `LnpDatagram::Write`, 0x2efe50: 437; registrele și ordinea actualizării dimensiunii diferă.
- `LnpMessage::Read`, 0x2dcd40: 360; păstrarea argumentului `previous` ocupă registrul folosit de client
  pentru dimensiunea bufferului.
- `LnpWorker::Post1`, 0x2dd220: 172, și `Post2`, 0x2dd2d0: 183; registrele și programarea încărcărilor.
- `Object2e4990::ReplayApiEnabled` din `Transport_Small.cpp`, 0x2e4990: 35;
  încărcările argumentelor / registrelor diferă.
- `ZoneD_Small.cpp`, `Clone`, 0x2f2780: 31 în sursă, față de 35 în client; ESI / CL și ordinea copiei.

Acestea sunt numai diferențele dintre implementările deja revendicate, nu totalul muncii rămase.
Rândul neacoperit al inventarului este **12.685.168 octeți, 79,65%**, în 47.919 intrări de index;
acesta se raportează după categoriile de sursă, implementări neidentice și biblioteci. Familiile de pachete
și formatele încă deschise din secțiunea precedentă rămân de extins. Paritatea integrală de sursă este activă.

**Continuare (2026-10-08, inițializatori scalari, limite după return și constructori implicați).**

- `constant_construct` din `gen_meta.py` extrage stocările de **1, 2 și 4 octeți**, valorile constante
  și registrele ECX / EDX inițializate explicit la zero. Ordinea, intervalele neinițializate și padding-ul
  sunt păstrate. Stocările suprapuse, depășirea mărimii, registrele necunoscute, valorile care nu încap
  și instrucțiunile cu alte efecte sunt respinse. Valorile aflate în intervalul adreselor imaginii sunt
  excluse: nu sunt tratate ca inițializatori numerici fără obiectul de sursă referit.
- Pentru tipurile opace fără bază sau metode virtuale, `constant_members` produce membri de mărime
  și aliniere compatibile cu descrierea. Golurile rămân tablouri de octeți fără inițializatori. Pentru
  obiecte de trei octeți cu aliniere unu, o stocare de cuvânt este reprezentată prin doi membri u8;
  un membru u16 ar mări greșit tipul prin padding. Mai întâi se păstrează layout-urile deja cunoscute.
  Exemple identice: `StealthCharacterFadeInstance` / **0x127e80**, stocări u32 + u16 și doi octeți
  neinițializați; `SkinEmblem` / **0x223d80**, două valori u32, 0 și 5;
  `VfxAnimatedFloatVariableData` / **0xa58e90**, valori de lățimi diferite și goluri neinițializate.
- Prima extindere a adus **51 de funcții distincte noi**, fără eliminarea vreunei revendicări existente.
  Inițializările și aliasurile sunt instanțiate și comparate, iar probele care diferă sunt eliminate.
  Enumerarea formelor cu membri implicit inițializați, atribuiri în corpul constructorului sau listă
  explicită de inițializare este păstrată în `client-src/obj/meta-constant-style-audit.json`.
- Auditul a găsit corpuri complet identice până la `ret`, respinse fiindcă funcția următoare începea
  imediat, fără padding și fără intrare în index. Exemple: **0x1dba10, 0x24e1d0, 0x6d0910**.
  `straight_return` din `match_func.py` dovedește limita numai pentru instrucțiuni de date / stocări
  acceptate explicit, fără salturi sau apeluri, cu **un singur return la sfârșitul corpului** și cu toate
  instrucțiunile decodate complet. Codul următor nu poate fi atins din această intrare. Corpurile mai
  complexe păstrează verificarea veche a limitei. Nu sunt tolerate diferențe de octeți sau de ținte.
  Trei teste verifică funcții consecutive neindexate, respingerea ramurilor / apelurilor / celui de-al
  doilea return / instrucțiunilor trunchiate și păstrarea controlului octeților și relocărilor.
- Această dovadă a permis **încă 13 funcții** în `MetaFunctions.cpp`, inclusiv corpurile de 32 de
  octeți ale constructorilor reflectați. Indexul nu a fost rescris; acoperirea rămâne calculată pe octeți,
  deci codul funcției următoare nu este revendicat împreună cu constructorul.
- **`PersistentEffectConditionData`, `ItemGroup`, `LoLSpellPreloadData`:** forma corectă are membri
  cu inițializatori, fără constructor declarat separat în header. Compilatorul generează singur
  constructorul: îl apelează din `MetaCreate`, dar îl desfășoară în `MetaConstruct`. Stocările din
  constructorul membru și cel de placement trebuie să fie aceleași înainte ca generatorul să aleagă
  această formă. Încărcarea în EAX a lui `this` este urmărită; modificarea pointerului ECX este respinsă.
  Corpurile constructorilor separați sunt **0x278c60: 83/83**, **0x2b1c20: 83/83** și
  **0x510370: 86/86**. Cititoarele de placement sunt **0x26fd80: 85/85**, **0x2a8b40: 85/85** și
  **0x509700: 88/88**. Toate cele trei `MetaCreate` au rămas **24/24**. Aceste șase corpuri noi aduc
  totalul acestei extinderi la **70 de funcții, 3.324 octeți**, fără eliminări.
- **S2C_605_Read / 0x8bc6f0: 265/265** este rezolvat prin extragerea formatului cu helperul inline
  `Bits`, aceeași formă ca `GetBits_91cae0`. Expresia directă pentru bitul de prezență schimba registrele.
  Cititorul păstrează copierea pointerului înaintea verificării; setterul folosește limita câmpului și
  temporara u8. Lanț: ROR 1, inversarea biților, ROR 4, adunare 0x3f, NOT, schimbarea biților vecini.
  `PacketScalars.cpp` are **14 cititoare**; cele 13 vechi au rămas identice. Generatorul încearcă atât
  copierea / post-incrementarea cursorului, cât și extragerea directă / helper a formatului.
  Helperul `Bits` este comun cu generatorul pachetelor cu mai mulți membri.

**Verificare locală:** toate cele **3.876 de inițializări de metadate**, **5.852 de revendicări și aliasuri
de șabloane / constructori** și **14 cititoare scalare** au trecut: **9.742 în total**.
Toate cele **30 de teste** ale câmpurilor, COFF / limitelor, fluxului pachetelor, acoperirii și extragerii
constructorilor au trecut. Scripturile modificate trec și `py_compile`.

**Încă deschis:** S2C_444 / 0x842b80, C2S_553 / 0x8db700 și S2C_581 / 0x8e1220 păstrează ordinea
inversă a celor două produse ale inversării de biți. Au fost încercate forme cu tipuri de parametri diferite,
constante signed / unsigned / unsigned long, ordinea inversată a termenilor, inline / forceinline și tipuri
independente pe cele două produse, inclusiv 64 de biți cu multiplicarea finală unsigned. Aceste probe nu au
produs potriviri și nu au intrat în sursele revendicate. S2C_581 are acum aceeași mărime, 326, și
**316/326 de octeți identici** în proba cu helperul de format; diferența începe la +0x10d.
S2C_179 / 0x868c40 și cititoarele cu enum-uri, șiruri sau mai mulți octeți de prezență rămân de extins.
Cele șapte diferențe de transport / copiere din secțiunea precedentă sunt încă deschise.

**Scor complet al acestei etape (2026-10-08): 17.309 funcții identice, 2.953.051 octeți,
18,54% din cod.** Față de 17.238 / 2.949.462: **+71 funcții, +3.589 octeți**. Cele șapte implementări
scrise încă neidentice au rămas șapte / 1.727 octeți. Inventarul neacoperit are 12.681.579 octeți,
79,63%, în 47.855 intrări. Log: `client-src/progress-2026-10-08-constants-final.log`;
raport: `client-src/progress-2026-10-08-constants-audit.json`. Față de scorul inițial 16.806,
progresul cumulat este **+503 funcții și +68.920 octeți**. Paritatea integrală rămâne activă.

**Continuare în paralel (2026-10-08, contribuția Claude și agenți pe familii separate).**

Utilizatorul a autorizat explicit subagenții și a semnalat modificările făcute cu Claude între timp.
Auditul a identificat `tools/gen_small.py` și integrarea lui în `gen_sources.py`; sursele Small nu fuseseră
încă generate. Un agent a executat și verificat generatorul, unul a extins pachetele și unul transportul.
Fișierele, probele și obiectele de compilare au fost separate; `field_candidates.cpp` nu a fost folosit
concurent. Scorul complet este rulat separat după stabilizarea surselor.

- Lifterul Claude execută simbolic funcții fără ramuri și scrie C++ pentru încărcări, stocări, apeluri și
  rezultat. Numele și tipurile originale nu sunt cunoscute: `K<rva>` / `k<rva>` / `T<rva>` / `t<rva>`
  și globale `g_<va>`. Nu încorporează octeți de mașină sau assembly. Formele neacoperite de model și
  corpurile care nu ies identic sunt excluse. Scannerul este executat o singură dată pentru 23 de shard-uri.
- Auditul local inițial al `Small_*.cpp` găsește **4.181 funcții / 119.377 octeți**, recompilate și
  comparate. În plus față de verificatorul comun, `lifted_targets_match` verifică explicit RVA/VA din
  numele generate, inclusiv țintele fără nume și cele absente din index. O probă negativă respinge o
  țintă deplasată cu un octet. Nu există conflicte între țintele relocărilor din shard-uri. Aceste numere
  sunt locale, înaintea deduplicării și verificării integrării globale. Zona 0x2d0000–0x2f3000 a fost
  rezervată agentului transport; 26 de candidați au fost excluși din shard-uri pentru a nu suprapune munca.
- Integrarea a expus identități ABI care nu trebuie tratate ca simple etichete: `operator new`,
  0x9bb8d0, fusese ridicat ca `k9bb8d0`; apelurile C++ existente `??2@YAPAXI@Z` au rămas identice
  în octeți, dar au fost respinse la verificarea țintei. Definițiile reale new/delete sunt reconstruite
  cu ABI-ul standard și corpuri compilate identice, înainte de regenerarea metadatelor. Verificarea
  țintelor nu este slăbită și un alias nu este acceptat fără corp verificat.
- Transportul aduce **7 funcții / 581 octeți**: CRC `Add(const u32&)`, **0x2d2cf0: 108**;
  notificarea observatorului, **0x2ea530: 41**; temporizarea peer-ului, **0x2edca0: 93**;
  jurnalul de canal, **0x2ec560: 151**; `_Find_lower_bound<u8>`, **0x2d3e20: 73**;
  `std::set<u8>::clear`, **0x2d02b0: 67**; invocarea delegate-ului, **0x2f27d0: 48**.
  Toate sunt verificate inclusiv la ținte. `template class std::set<u8>;` în aceeași unitate păstrează
  helperul separat și reproduce forma jurnalului; `find` / `count` fără instanțiere desfășurau prea mult
  cod. Jurnalul alege textele ` reliable` / ` unreliable` și ` ordered` / ` unordered`.
  La temporizare, pointerul `inner` este păstrat local, cu ordinea state=2, time=now+timeout, byte=value.
  Delegate-ul primește trei referințe de 64 de biți și una de 32; callback-ul primește valorile copiate.
- Două apeluri vechi din 0x2ee180 și 0x2ee2f0 au fost corectate să folosească funcția liberă reală
  `k353670`, identificată de noile surse, în locul unui `GetTarget` presupus membru. Ambele rămân
  **21/21**. Thunk-urile 0x2edc90 / 0x2efcb0 sunt identice în octeți în probe, dar țintele contrazic
  etichetele existente ale thread-urilor; nu sunt revendicate.
- **S2C_734 / 0x8bf6c0: 545/545**. Cazul format=1 stochează valoarea din AL, păstrată de la
  comparație; `constant_store` urmărește acum această valoare și respinge operațiile care o modifică.
  Cititorul păstrează patru nume separate de format, cu corpuri verificate la 0x796de0; reutilizarea
  unui singur nume producea 506 octeți. Aliasurile au crescut de la 72 la **80**, iar cititoarele de
  la 14 la **15**, cu toate cele vechi păstrate. Audit local **95/95**; patru teste noi trec.
  **S2C_732 / 0x88f070** este clasificat, dar încă neidentic: 605/615 octeți, prima diferență +0x7f,
  ordinea produselor din inversare numai în prima ramură. Celelalte trei ramuri se potrivesc.
- Constructorii cu blocuri SSE și membri scalari / padding păstrat sunt extinși separat. Probele cu
  agregatele `Vector4`, `Vector2`, `Vector3` reproduc **VfxAnimatedColorVariableData / 0xa577f0: 76/76**,
  **VfxAnimatedVector2fVariableData / 0xa59100: 77/77** și
  **VfxAnimatedVector3fVariableData / 0xa59470: 84/84**. `Vector3` grupează stocările zero 8+4 și
  schimbă ordinea XORPS / XOR ECX față de Vector2 + u32. Alegerea se verifică prin compilare.

Dovezi locale ale agenților: `client-src/obj/agent_small_audit.json`,
`agent_transport_audit.json`, `agent_packet_final_audit.json`. Rezultatele locale nu înlocuiesc scorul global.

**Integrare ABI (2026-10-08).** `gen/OperatorAllocation.cpp` definește 14 operatori reali,
verificați separat, la șase adrese: new/new[] **0x9bb8d0: 5**, nothrow new **0x9bb8e0: 13**,
aligned new **0x9bb8f0: 54**, delete **0x9bb930: 5**, sized delete **0x9bb940: 11**,
aligned / sized+aligned delete **0x9bb950: 18**. Sunt verificate și variantele array / sized+aligned,
inclusiv ABI-ul folosit de `LnpQueue`. Țintele sunt `Pool_Alloc` / `Pool_Free`. Alegerea ternară a
alinierii minime produce corpul corect; forma cu if producea 54 de octeți, dar numai 40 identici.
Lifterul exclude permanent aceste adrese de operatori din numele sintetice și păstrează ABI-ul real
pentru apeluri. EAX după delete este invalidat; două destructoare aveau un retur int fictiv provenit
din registrul rezidual și au fost corectate la void, cu aceiași octeți. Patru apeluri afectate se regenerează
identic. Totalul local actual este **4.180 Small +6 operatori, 119.478 octeți**.

**Constructori cu ABI real (2026-10-08).** `tools/gen_meta_ctors.py` și `gen/MetaConstructors.cpp`
reconstruiesc constructorii declarați în `BinClasses.h` din corpurile Small deja verificate, cu numele
C++ `Class::Class()`. Return-ul sintetic al lui this este înlocuit de semantica constructorului C++;
se verifică toate instrucțiunile și țintele produse de compilator. O apelare Small spre constructorul
bazei este eliminată numai dacă receiverul și RVA-ul sunt exact constructorul declarat al bazei,
deoarece C++ efectuează acel apel implicit. **99 de ABI-uri la 98 de adrese, 14.710 octeți**, trec
compilarea și comparația finală, inclusiv **StatStoneSet::StatStoneSet(), 0x255f60: 117/117**.
Aceste corpuri susțin efectiv aliasurile constructorilor și repară apelurile metadatelor către ei;
adresele sunt deja acoperite de Small și nu se numără de două ori.

**27 de constructori încă respinși:** de regulă baza are un constructor implicit în header, iar
compilatorul emite o stocare de vptr înaintea apelului Small explicit, care o face observabilă.
Ordonarea topologică a definițiilor nu elimină problema. `MapSpotlight` poate reproduce 82/82 octeți
prin apelul implicit spre ancestor, dar constructorul `MapProjectedTexture` nu are încă un corp C++
verificat la 0xac8330, astfel ținta rămâne respinsă. Aceste cazuri nu sunt mascate prin aliasuri.
Raport: `client-src/obj/agent_ctor_audit.json`. Constructorii bazelor abstracte, ai căror callbacks de
creare / placement sunt null, trebuie identificați și definiți din apelurile descendenților.

**Verificare:** toate cele **36 de teste** locale au trecut după integrarea pachetelor și constructorilor
mixt scalar / SSE; scripturile modificate trec `py_compile`.

### 2026-10-08 — integrarea finală a lucrului în paralel

Auditul complet intermediar `client-src/progress-2026-10-08-parallel-audit.json` a măsurat
**20.678 funcții identice / 2.969.087 octeți / 18,64%**. A expus **782 funcții neidentice**,
deși majoritatea au aceiași octeți: noile corpuri Small au făcut verificabile ținte care înainte
nu aveau nume reconstruit. **740** erau inițializatori de metadate. Acest scor este intermediar;
rezultatele de mai jos se verifică din nou împreună, fără relaxarea comparației de ținte.

- Constructorii bazelor abstracte sunt identificați și declarați: **BaseLoadoutData / 0x22f580:
  140/140**, **TftCutsceneClip / 0x557440: 30/30**, **MapPlaceable / 0xa22bb0: 54/54**.
  `gen_meta_ctors.py` păstrează toate cele 99 de ABI-uri anterioare și publică acum **111 ABI-uri
  la 110 adrese, 16.118 octeți**. Cele 12 noi sunt cele trei baze și nouă descendenți:
  MapDynamicPointLight, MapProjectedTexture, MapSpotlight, TFTDamageSkin, TftCutsceneCamLerpClip,
  TftCutscenePostFxClip, TftCutsceneUiToggleClip, TrophyData și TrophyPedestalData.
  `MapSpotlight` este rezolvat: **82/82**, inclusiv constructorul bazei.
  Nu este necesar `noinline`: 105 corpuri sunt compilate împreună, iar șase în module
  `MetaCtorCalls_*.cpp` separate, când clientul păstrează apelul spre bază. Mai sunt **17**
  constructori candidați respinși. Dovezi: `agent_ctor_audit.json`, `agent_ctor_parent_probe_audit.json`.
- `gen_meta_small.py` reconstruiește **188 specializări** reale ale callback-urilor:
  69 destructori care invocă `T::~T`, 12 callbacks goale dovedite și 107 callbacks care invocă
  `ViewController::PostLoad`. Metoda comună **0xaefdb0: 39/39** este compilată separat, fără
  `noinline`; sunt dovedite globalul **0x36f6118** și apelurile **0xab1550 / 0xaf37c0**.
  Cele două servicii apelate au ABI declarat, dar corpuri încă nereconstruite.
  Auditul izolat recuperează **152/740 inițializatori, 28.998 octeți**. Restul de 588 necesită
  constructori/destructori autentici; scrierea manuală a unui vptr în obiecte polimorfe opace nu
  este acceptată ca reconstrucție de lifetime C++. `gen_meta.py` exclude instanțierile explicite
  deținute de alte module, iar generatorul păstrează și reverifică specializările deja publicate.
- `ZoneB_Small.cpp` și `ZoneD_Small.cpp`: **48/49** trec. Sized delete și cele trei aligned delete
  folosesc suprasarcinile C++ reale, iar Clone / 0x2dbff0 folosește `::operator new(8)`.
  Destructorul / 0x2dad60 apelează corpul reconstruit `K9baf90::f`. Problema veche
  Clone / **0x2f2780** rămâne. Dovadă: `agent_transport_delete_audit.json`.
- Cele două pachete **0x834580 / 0x8348b0: 197/197 fiecare**, inclusiv țintele. Headerul comun
  `FieldObjectAliases.h` definește obiectul de 48 de octeți, vectorul de 12 și elementul de 208.
  Asignarea reală C++ a obiectului este **0x7ec350: 77/77**, cea a vectorului **0x7eadb0: 161/161**.
  Vectorul distruge prin slotul virtual 3, respectă flagul de memorie externă și reconstruiește
  elementele prin constructorul de copiere de la **0x7b89e0**, încă fără corp reconstruit.
  Corpul typed al obiectului înlocuiește proprietatea Small la 0x7ec350; vectorul adaugă o adresă
  verificată nouă. `gen_fields.py` include declarația comună la regenerarea PacketVectors.
  Audit local: **31/31** (`agent_transport_fieldobjects_audit.json`).
- API-urile bibliotecilor sunt păstrate prin compilarea surselor originale și verificarea propriilor
  corpuri, inclusiv când adresa nu apare în inventarul de adrese unice. **ENGINE_get_id,
  EVP_PKEY_id și CTLOG_get0_name: 0x129c80, 7/7 fiecare**; **PKCS12_PBE_add: 0xecb40, 3/3**;
  transportul Sentry dezactivat **sentry__transport_new_default: 0xe8b80, 3/3**.
  Acestea repară apelurile din curl, SCT_LIST_print și sentry_options_new.
  Constructorii de bibliotecă care depind de `OPENSSLDIR` nu sunt revendicați prin aliasul getterului;
  compilarea fișierului CT folosește valoarea din Makefile-ul original VC-WIN32.
- Aliasul C **free / 0x9bb930: 5/5** are corp real care delegă la Pool_Free, la fel ca ordinary
  operator delete; repară destructorul unique_ptr din crashpad / **0xca2140: 14/14**.
  Thunk-ul **_stricmp / 0x9ae430: 5/5** transmite ambii pointeri către CRT / 0xf72224.
  Corpul CRT citește bytes, convertește A–Z cu +0x20 și delegă la _stricmp_l când locale-ul este
  activ; eticheta ambiguă `wcsicoll` din inventar nu descrie acest corp. Thunk-ul typed înlocuiește
  forma Small fără parametri și repară **ReplicationTable::Register / 0x19ccc0: 149/149**.
  Dovadă: `root_parallel_integration_audit.json`.

**Verificare:** toate cele **40 de teste** locale trec; `py_compile` trece pentru generatoarele și
verificatoarele modificate. Scorul complet după integrare se păstrează separat în
`client-src/progress-2026-10-08-parallel-integrated.log`, cu eșecurile exacte în JSON-ul omonim
`-audit.json`. Paritatea integrală nu este atinsă; scorul se raportează numai după terminarea acelui proces.

### 2026-10-08 — ABI placement void, șiruri și referințe UI cu lifetime real

**Descoperire ABI:** `MetaClass::ConstructFn` și `MetaConstruct<T>(void*)` returnează **void**.
La **0x188980**, construirea unui obiect cu șir de 12 octeți și scalar de 4 produce **33/33**
cu `new (p) T;`. Forma `return new (p) T;` produce 34 de octeți și numai 16 identici: forțează
pointerul obiectului în EAX, în timp ce clientul lasă pointerul șirului gol în EAX și folosește ECX
pentru obiect. Valoarea reziduală din EAX nu este rezultatul callback-ului.
Auditul izolat al tuturor formelor placement deja publicate păstrează **1.010/1.010** corpuri cu
semnătura void (`client-src/obj/root_meta_void/audit.json`). Headerul, generatoarele, instanțierile
și simbolurile sunt actualizate împreună. Rapoartele istorice cu vechiul simbol sunt convertite
la ABI-ul actual de `gen_meta_small.py`, fără a relaxa verificarea codului.

**Șiruri reale:** `MetaString` păstrează tagul de reflecție și folosește reprezentarea / lifetime-ul
deja verificat al `RString`, de 12 octeți. `simple_layout` recunoaște acum code=0x10.
`create_stores` urmărește încărcarea pointerului gol de la **0x1b467f0** prin ECX/EDX;
pointerul runtime nu este înlocuit cu o constantă. Alte globale sunt respinse.
În clasele complet descrise cu primul membru string, destructorul implicit distruge membrul real,
în locul declarației externe presupuse a unui destructor al clasei la adresa lui RString.
În probe, **CompanionSpeciesData, EsportsBannerData, HudOptionalBinData, OptionItemDropdownItem,
ShaderLogicalParameter, SkinCharacterMetaDataProperties_SpawningSkinOffset, TftMapGroupData**
au fiecare placement **0x188980: 33/33** și destruct **0xf1700: 9/9**.
`gen_meta_ctors.py` elimină din candidat numai grupul exact de trei stocări de default string
deja efectuate de un membru MetaString declarat, inclusiv moștenit. Corpul final se recompilează
integral înainte de alias. Toate cele **111 ABI-uri / 110 adrese / 16.118 octeți** sunt păstrate;
TftCutsceneArenaIntroInitializer, TftCutsceneCamVfxClip și TftCutsceneObjVfxClip rămân identice
după introducerea membrilor string reali. Numele reflectate care sunt cuvinte-cheie C++, de exemplu
`register`, sunt escapate numai în identificatorul membrului; hash-ul metadatelor rămâne cel original.

**Referințe UI:** `gen_ui_refs.py` și manifestul `tools/ui_ref_layouts.json` reconstruiesc
**52 layout-uri**: 51 tipuri cu callbacks comune și baza necesară RadialMenuButtonDefinitionBase.
La fiecare regenerare se verifică mărimea, alinierea, părintele, numele/hash-urile/offseturile
membrilor și forma integrală a callback-ului. Moștenirile RadialMenuHoverButtonDefinition și
SpellSlotSimpleUiDefinition sunt păstrate; link-ul runtime nereflexat al celui din urmă, la +0x60,
nu este inventat ca membru în metadate. Padding-ul și cozile încă neidentificate rămân opace.

`UiHashLink` are 24 de octeți: prefix de 12 și referință polimorfă de 12.
Starea referinței este o bază nepolimorfă de 8 octeți, astfel C++ inițializează control/active
înainte de vptr, conform clientului; două membre directe pe clasa virtuală dau altă ordine.
**UiResourceReference::~UiResourceReference / 0xae14d0: 79/79**; destructorul deleting
**0x31e950: 32/32**; **UiHashKey::UiHashKey / 0x9ba240: 23/23**.
Vtable-ul de **4 octeți / un slot**, la **0x1afb9bc**, este verificat explicit în COFF și client;
weak extern vector-deleting `_E` are fallback către scalar-deleting `_G`, nu către alt corp.
TU-ul nativ folosește **-O2 -std:c++17 -Ob1 -GR-**, păstrând apelul destructorului de 79 de octeți
din wrapperul deleting. Sunt verificate explicit globalul **0x37252f0**, metoda registrului
**0xafd340**, apelul virtual slot 27 și sized delete **0x9bb940**.
Corpul metodei registrului și celelalte metode ale resursei rămân nereconstruite.

**52/52 MetaDestruct** compilează prin distrugerea subobiectelor reale, cu cinci RVA-uri primare:
**0x5b7660: 12**, **0x576830: 22**, **0x576390: 30**, **0x5766e0: 38**, **0x576510: 46**.
`UiResourceRefCallbacks.cpp` deține aceste corpuri; variantele folded au fiecare propriul corp
compilat și verificat. Nu există specializări duplicate în MetaFunctions / MetaSmallTemplates.
Constructorii reali ai **AbilityPrompt / 0x710d60: 82/82** și
**CooldownEffectUiData / 0x586c00: 122/122** folosesc inițializarea implicită a membrilor.
Primul scrie numai byte-ul +0x30 și DWORD-urile +0x34/+0x38, prin operații legale pe bytes;
padding-ul +0x31..+0x33 este păstrat neinițializat. Nu se scrie manual niciun vptr.

**Lifterul consumă ABI-ul real:** destructorul 0xae14d0 este thiscall, fără argumente pe stivă,
cu rezultat void. EAX este invalidat după apel; vechile return-uri int din registrul rezidual
sunt eliminate. Apelul este calificat `p->UiResourceReference::~UiResourceReference()`, necesar
pentru apel direct: forma necalificată face dispatch virtual și nu reproduce clientul.
Patru sharde Small sunt regenerate; **780/780** corpuri trec inclusiv țintele. Cele patru vechi
revendicări Small ale callback-urilor comune sunt înlocuite de cele C++ typed; nu se dublează
acoperirea. Sunt recuperate separat **11 wrapperuri / 186 octeți**:
0x5763d0, 0x5b79c0, 0x612cb0, 0x612f50, 0x6131f0, 0x64ba90, 0x697170, 0x697e90,
0x6db300, 0x70b7d0 și 0x74bd70.

După toate aceste integrări: **MetaFunctions are 1.933 revendicări template verificate**, iar
**MetaSmallTemplates 196 specializări verificate, la opt RVA-uri**. Generatorul MetaClasses
păstrează toate cele **3.876 funcții de inițializare/teardown** ale obiectelor de metadate,
inclusiv candidații cu bindings încă nerezolvate. Eliminarea unui initializer nevalidat elimina
și teardown-ul deja identic și definiția globalului; această reducere a sursei nu rezolvă callback-ul.
Auditul local păstrează și raportează explicit **496 inițializatori încă neidentici**.

Dovezi: `root_strings_layout_probe.json`, `agent_ctor_audit.json`,
`agent_meta_small_ui_native_final_audit.json`, `agent_meta_small_ui_callbacks_final_audit.json`,
`agent_meta_small_ui_constructors_final_audit.json`, `agent_transport_ui_small_audit.json`, în
`client-src/obj/`. **53 de teste trec**, inclusiv cazurile negative pentru proveniența pointerului
gol, inițializările string complete și ABI-ul destructorului; `py_compile` trece.
Scorul complet al acestei stări este în `client-src/progress-2026-10-08-native-lifetimes.log`,
cu lista exactă a eșecurilor în `progress-2026-10-08-native-lifetimes-audit.json`.

**Scor complet verificat, după integrare (2026-10-08):**

| Categorie | Funcții / intrări | Octeți | Din cod |
|---|---:|---:|---:|
| Sursă recompilată identică | **21.038** | **3.017.660** | **18,95%** |
| Sursă încă neidentică | 503 | 60.018 | 0,38% |
| Biblioteci, adresă unică | 1.240 | 215.817 | 1,36% |
| Forme de bibliotecă la mai multe adrese | 450 | 73.466 | 0,46% |
| Neacoperit, intrări de index | 43.636 | 12.558.691 | 78,86% |
| Inventar complet | 66.825 | 15.925.652 | 100% |

Față de punctul transmis în chat, **16.806 funcții / 2.884.131 octeți / 18,11%**, creșterea
verificată este de **4.232 funcții, 133.529 octeți și 0,84 puncte procentuale**.
Față de auditul complet intermediar de integrare, 20.881 funcții / 3.004.490 octeți,
starea finală adaugă **157 funcții / 13.170 octeți**. Acest scor este cel efectiv din procesul
complet, nu suma probelor și nu numărul de aliasuri.

Cele **503** eșecuri sunt **496 inițializatori MetaClasses** cu callbacks încă nereconstruite
și cele **șapte probleme preexistente**: LnpAppObserver / 0x2ec600, LnpDatagram / 0x2efe50,
LnpMessage_Read / 0x2dcd40, LnpWorker_Post / 0x2dd220 și 0x2dd2d0,
Transport_Small / 0x2e4990, ZoneD_Small / 0x2f2780. Niciun modul Small, PacketVectors,
operator de alocare sau wrapper de bibliotecă verificat nu mai eșuează în acest audit.
Paritatea 100% rămâne obiectivul; cei 12.558.691 de octeți neacoperiți și bindings-urile rămase
nu sunt declarați finalizați. Procesul scorului s-a terminat cu exit code 0.

### 2026-10-08 — instrumente externe instalate și probate pe client

La cererea de a căuta instrumente și skill-uri mai puternice, s-au verificat
sursele upstream și s-au instalat **Ghidra CLI 0.2.2**, skill-ul său,
**objdiff 3.8.2**, **PyGhidra 3.1.0** și **Z3 4.15.4**. Ghidra 12.1.4,
JDK 21 și proiectul BA13 existau deja și sunt reutilizate. Hash-urile release-urilor,
sursele, comenzile și limitele sunt în [RECONSTRUCTIE_TOOLING.md](RECONSTRUCTIE_TOOLING.md).

`tools/ghidra_cli.py` oferă acces JSON la decompilerul persistent.
`tools/ghidra_inspect.py` exportă în lot decompilări, instrucțiuni, apeluri și P-code,
verificând fiecare instrucțiune față de imaginea clientului.
`tools/re_tooling_probe.py` verifică **36/36 bytes** Replay / 0x2e4990 și apelul
0x996470, apoi reconstruiește temporar funcția placement / 0x188980 și structura
de 16 bytes. Tiparea produce câmpurile data/size/capacity/value și ABI-ul void cdecl;
funcția și tipul temporare sunt eliminate și rollback-ul este verificat.
Z3 trece cazul pozitiv și găsește contraexemplul signed division vs arithmetic shift.

objdiff citește efectiv obiecte **MSVC COFF x86**; diferența dintre profilele Replay
de 36 și 35 bytes apare explicit în instrucțiuni, cu similaritate 87,69231%.
Comanda `function calls` din Ghidra CLI 0.2.2 întoarce incoming în proba reală;
wrapperul o respinge, iar exportatorul extrage outgoing direct din referințele CALL.
Comparația objdiff nu înlocuiește dovada candidat-vs-client din `match_func.py`.
Nu s-a rulat un nou scor complet pentru această adăugare de infrastructură.

### 2026-10-08 — constructori UI, perechi de chei și containere cu lifetime real

Generatorul `gen_ui_refs.py --constructors` reconstruiește **33 de constructori
reflected UI / opt RVA-uri / 985 bytes**, verificând fiecare corp și țintele lui.
Față de cele două entry points anterioare, cele șase corpuri native suplimentare
au **781 bytes**. Tail-urile opaque folosesc numai stocările observate; padding-ul
dintre byte-ul AbilityPrompt +0x30 și DWORD-ul +0x34 rămâne neinițializat.
Membrul **HudItemShopItemDetailsDefinition.ClickData / +0x78** are lifetime-ul
UiHashKey real și este verificat prin metadate și apelul constructorului 0x9ba240.
`UiHashKey.hash` este HashValue, fără schimbarea corpului nativ de **23 bytes**.

**JunglePathRecommendations, PerkReplacement, RecSpellRecommendations,
SummonerSpellPerkReplacement** au două chei de 12 bytes la +0 și +0xc.
`hash_pair_layout` cere cele două câmpuri reflectate HashValue, mărimea/alinierea,
lipsa părintelui și forma integrală a placement-ului și a constructorului cheii.
Cb-urile C++ sunt **MetaConstruct / 0xf1200: 21**, **MetaCreate / 0xf11d0: 40**,
**MetaDestruct / 0xecb40: 3**; aliasurile folded au corpuri proprii compilate.

Primul audit complet al acestui lot (`progress-2026-10-08-ui-hash.log` și auditul
omonim) are **21.049 funcții / 3.018.916 bytes / 18,96%**. Cele **3.871** de
amprente SHA256 ale intrărilor urmărite sunt neschimbate pe durata măsurării.
Față de auditul native-lifetimes: **+11 funcții / +1.256 bytes**, cinci eșecuri
vechi dispar. Un apel Small la constructorul recuperat 0x5894b0 devine însă
explicit nevalidat: 0x64c470 numea un `K5894b0::f` int fără implementare proprie.

Acest apel este corectat prin **UiHashLinkTriple**, cu trei subobiecte UiHashLink.
Constructorul său de **93 bytes / 0x5894b0** este verificat ca alias real, în TU-ul
constructorilor UI. Lifterul produce două placement new pentru callback-ul
**0x64c470: 21/21**, cu rezultat void; EAX rezidual nu devine contract C++.
Sunt astfel **34 de definiții native de constructor**, incluzând helperul, la
aceleași opt adrese. `Small_5e0000.cpp` păstrează **166 de corpuri verificate**.

`gen_reflected_buffers.py` și manifestul `reflected_buffer_layouts.json` introduc
**ReflectedBuffer<E>**: pointer, count u32, capacity signed, în total 12 bytes.
Destructorul încheie lifetime-urile elementelor înaintea deallocării; bitul de
semn din capacity suprimă numai deallocarea. Tipul runtime este separat de tag-ul
serializat existent. Variantele respinse nu primesc un layout nou.

Sunt publicate **25 de layout-uri / 100 de callback-uri C++ verificate** în
`ReflectedBufferCallbacks.cpp`, inclusiv liste cu MetaString, UiHashKey, UiHashLink,
elemente embedded deja definite și trei perechi de scalari pentru map-uri.
Tail-urile scalare sunt inițializate din stocările complete observate, iar cele
neidentificate rămân opaque. Toate relocările directe sunt verificate explicit.
Nu se revendică încă implementarea constructorului extern **0x6582d0** pentru
LoadingScreenSummonerNameData și LoadingScreenSummonerTitleData: cele două wrappers
stabilesc exact acest target și ABI-ul thiscall, iar corpul său cu conversii
`cvtss2si` ale culorilor rămâne de reconstruit. Nu se publică un alias de corp
pentru această declarație externă. Cele patru callback-uri ale fiecărui owner
sunt recompilate și verificate separat.

Auditul intermediar cu primele 13 containere (`progress-2026-10-08-reflected-buffers`)
are **21.048 funcții / 3.018.422 bytes / 18,95%**, cu **506 eșecuri**.
Publicarea celor șase corpuri native făcea explicit nevalidate opt inițializări
care numeau alte instanțieri la aceleași adrese; nu s-a relaxat matcherul și nu
s-au adăugat aliasuri fără corp. Layout-urile și lifetime-urile celor opt owners
au fost reconstruite în extensia de 25 de clase, iar verificarea completă a
închiderii dependențelor se păstrează în `progress-2026-10-08-buffer-closure`.

Probele celor 25 de clase sunt în `root_reflected_buffer_audit.json`; **32 de
candidați** cu alte forme rămân respinși. **111 constructori reali / 110 RVA-uri /
16.118 bytes** ai generatorului MetaConstructors rămân verificați după integrare.
**61 de teste trec**, inclusiv respingerea extinderilor de obiect, a metadatelor
schimbate și a callback-urilor lipsă. Proba celor șase funcții de rețea cu patru
profile de compilare, în `root_network_profiles_audit.json`, dă **0/24** potriviri
integrale; schimbarea profilelor nu rezolvă acele surse.

Noua opțiune PyGhidra `--verified-abis` corectează temporar ABI-uri native și
override-uri CALL_RETURN greșite, păstrând tail calls JMP. Destructorul de listă
UI **0x613110** era decompilat ca o ramură cu ieșire imediată, din cauza adnotării
noreturn a lui 0xae14d0. După corecție, bucla și ownership guard-ul sunt prezente;
**57 bytes** sunt verificați față de imagine, iar wrapperul 0x64c470 rămâne de
**21 bytes**. Schimbările în BA13 sunt eliminate prin rollback.

**Audit complet după închiderea dependențelor, 2026-10-08:**

| Categorie | Funcții / intrări | Bytes | Din cod |
|---|---:|---:|---:|
| Sursă recompilată identică | **21.067** | **3.019.945** | **18,96%** |
| Sursă încă neidentică | 498 | 59.563 | 0,37% |
| Biblioteci, adresă unică | 1.240 | 215.817 | 1,36% |
| Forme de bibliotecă la mai multe adrese | 450 | 73.466 | 0,46% |
| Neacoperit, intrări de index | 43.611 | 12.556.861 | 78,85% |
| Inventar complet | 66.825 | 15.925.652 | 100% |

Procesul `progress-2026-10-08-buffer-closure` s-a terminat cu **exit code 0**.
Cele **3.873 amprente** ale intrărilor urmărite sunt neschimbate pe durata acestui
audit. Față de native-lifetimes, rezultatul este **+29 funcții / +2.285 bytes**;
nu există eșecuri noi. Dispar Replay / 0x2e4990 și patru inițializări de metadate
la 0x894e0, 0x94a80, 0xa9940, 0xa9c20. Toate cele opt bindings puse în evidență
de auditul intermediar sunt recuperate, inclusiv cele două clase de culori.
Rămân **492 inițializări MetaClasses** și cele **șase probleme de rețea preexistente**.
Constructorul 0x6582d0, containerele respinse și corpul complet al executabilului
rămân deschise; acest audit nu dovedește paritatea integrală a fișierului .exe.


## 2026-10-08 — constructori de culori și lifetime-uri Font/Jungle/TFT/Cursor

Constructorul comun **RVA 0x6582d0** este acum o implementare C++ reală pentru
LoadingScreenSummonerNameData și LoadingScreenSummonerTitleData: **111/111 bytes**,
cu toate cele șapte relocări float la adresele native. `gen_reflected_colors.py`
publică `ReflectedColorConstructors.cpp` numai după proba ambelor corpuri.
Argumentul blue al constructorului delegat se evaluează înaintea inițializării
bufferului. `_mm_cvtss_si32` păstrează conversia rotunjită după MXCSR; un cast
obișnuit ar produce conversie cu trunchiere. Profilul măsurat este
`-O2 -std:c++17 -d2SSAOptimizer-`: profilul SSA implicit dă 109 bytes și alte registre.
Alpha este convertit de două ori, conform clientului.

`gen_reflected_buffers.py` verifică acum și destructorii reali defaulted într-un
TU separat, înainte să permită binding-ul callback-urilor la ei. Rezultatul este
**29 owners / 116 callback-uri**, plus trei corpuri în `ReflectedBufferNative.cpp`:

| Metodă | RVA | Bytes identici |
|---|---:|---:|
| FontType::~FontType | 0x2338b0 | 70/70 |
| HeroFloatingInfoIconsData::~HeroFloatingInfoIconsData | 0x58ac50 | 71/71 |
| TftMapItemList::~TftMapItemList | 0x558de0 | 70/70 |

FontLocaleType are trei MetaString la 0, 12 și 24; TftMapItemData are strings
la 0, 12 și 28, cu itemID la 24. JungleLocationMapInformation are MetaString
name la 0, Vector3 la 12 și două u8 la 24/25. CursorData are Vector2 la 0 și
patru MetaString la 8/20/32/44. `gen_reflected_lifetimes.py` și manifestul
`reflected_lifetime_layouts.json` păstrează metadatele și corpurile native complete;
`ReflectedElementLifetimes.cpp` verifică opt callback-uri de distrugere și cele
 două de creare/placement Jungle. Destructorul Jungle este implicit și distruge
stringul real; nu mai este un alias artificial al unei clase la RString.

Constructorii Jungle folosesc obiectul Vector3 global de 12 bytes zero la
**VA 0x3715f70**, nu o inițializare scalară substituită. Această formă dă
**MetaCreate 0xf1650: 71/71** și **MetaConstruct 0xf16c0: 53/53**, inclusiv ambele
referințe la global. Index și Location sunt zero; padding-ul final nu este scris.

Cele două contexte Cursor sunt **tablouri fixe CursorData[7] și CursorData[3]**,
cu sizeof 392 și 168. Tag-ul de listă din reflecție nu dovedește reprezentarea
runtime cu pointer/count/capacity: proba tuturor callback-urilor respinge acea formă.
`gen_cursor_arrays.py`, `cursor_array_layouts.json`, `CursorArrayNative.cpp` și
`CursorArrayCallbacks.cpp` publică cinci metode și opt callback-uri verificate:

| Metodă | RVA | Bytes identici |
|---|---:|---:|
| CursorData::CursorData defaulted, Vector2 zero înaintea stringurilor | 0x61b990 | 104/104 |
| CursorDataCaptureCooldownContext ctor defaulted | 0x61ba00 | 130/130 |
| CursorDataTeamContext ctor defaulted | 0x61ba90 | 130/130 |
| CursorDataCaptureCooldownContext dtor defaulted | 0x622440 | 58/58 |
| CursorDataTeamContext dtor defaulted | 0x622480 | 58/58 |

Corpurile constructorilor stau împreună, permițând inlining-ul CursorData în
bucla tabloului; callback-urile stau separat, ca în client. Generatorul
MetaConstructors exclude acum definițiile de constructor deținute de alte TU-uri:
**110 constructori / 109 RVA-uri / 16.014 bytes** rămân în generatorul vechi;
constructorul CursorData de 104 bytes este verificat acum ca `= default` în TU-ul
nou. Parserul câmpurilor MetaString acceptă și numele fără prefix `::`.
Small_560000 are **180 corpuri verificate**, cu apelul la destructorul real al
bufferului de iconițe. ABI-ul său void nu transformă EAX rezidual în valoare returnată.

Indexul `functions.txt` primește două intrări dovedite de pointerii callback din
metadate și de cele două wrappers thiscall de 9 bytes: **0x6135c0 și 0x6135f0**.
Anterior, funcția de delete de 32 bytes era concatenată cu wrapperul următor în
inventar. Nu s-a relaxat matcherul: limitele celor două funcții sunt acum intrări
explicite. Inventarul are două intrări în plus; octeții imaginii nu se modifică.

**66 teste trec**, inclusiv respingerea metadatelor suprapuse, a numărului greșit
de elemente, a modificării buclelor native și a conversiei cvttss2si sau a
referințelor float substituite în constructorul de culori. Probele izolate din
`root_more_lifetime_callbacks_audit.json` găsesc **56/59 tipuri** cu distrugere
identică; **27** aveau încă storage opaque în headerul de producție. Acest lot
este doar o probă pentru următoarea extindere; nu este publicat în surse.

Rămân deschise constructorul owned-string **0x9b78e0** folosit de localeName
implicit "en_us" în FontLocaleType, inițializările celorlalte elemente cu valori
implicite, **28 candidați buffer respinși** (inclusiv cele două tablouri fixe,
reconstruite separat), restul inițializărilor MetaClasses și cele șase funcții de
rețea. Constructorul borrowed existent al RString nu poate substitui copierea
în memorie deținută a lui 0x9b78e0.

Auditul complet `progress-2026-10-08-colors-arrays` rulează separat după această
integrare. Cele **3.982 amprente** sunt în
`obj/root_colors_arrays_progress_inputs.json`; sursele și intrările urmărite sunt
înghețate până la încheiere. Ultimul scor complet confirmat înaintea acestui audit
rămâne **21.067 funcții / 3.019.945 bytes / 18,96%**. Nu se extrapolează un termen
pentru 100% și nu se confundă acest scor cu paritatea întregului executabil.


**Primul audit colors-arrays încheiat, 2026-10-08:** 21.082 funcții identice /
3.020.328 bytes / 18,97%, 503 eșecuri; inventar 66.827 intrări și 15.925.652 bytes.
Procesul a terminat cu exit code 0, iar cele 3.982 amprente sunt neschimbate.
Față de buffer-closure: +15 funcții / +383 bytes. Diferența mică în acoperirea netă
include eliminarea din potrivirile confirmate a cinci inițializări de metadate
al căror alias vechi nu avea încă un corp real. Cele cinci bindings sunt la
0x8b7f0 (StealthVfx), 0x91df0 (AudioStatusEvents), 0x93d30 (ESportTeamEntry),
0x94790 (MasteryData), 0xa0f70 (NeutralMinionSpawnConfig); toate folosesc aceeași
formă de distrugere a trei strings ca FontLocaleType.

Extensia de închidere publică exact aceste cinci layout-uri și recompilă ambii
callback-uri pentru fiecare. `ReflectedElementLifetimes.cpp` are acum9 tipuri /
20 callback-uri de lifecycle, fiecare corp și fiecare callee verificate. Nu se
adaugă un alias fiindcă octeții par similari: aliasul folded are propria instanțiere
C++ verificată. Inițializările scalare/valorile default ale acestor cinci tipuri
rămân de stabilit separat. Generatorul verifică și că fiecare offset reflectat
este exact offsetul dat de alinierea naturală C++, fără gap-uri neexplicate.
**67 teste trec** după această verificare suplimentară.

Auditul `progress-2026-10-08-colors-arrays-closure` este pornit separat pentru
această extensie; amprentele sunt în
`obj/root_colors_arrays_closure_progress_inputs.json`. Probele owned-string și
lotul mai larg de 27 layout-uri rămân izolate până la încheierea auditului.


**Audit colors-arrays-closure încheiat, 2026-10-08:**

| Categorie | Funcții / intrări | Bytes | Din cod |
|---|---:|---:|---:|
| Sursă recompilată identică | **21.088** | **3.021.259** | **18,97%** |
| Sursă încă neidentică | 498 | 59.563 | 0,37% |
| Biblioteci, adresă unică | 1.240 | 215.817 | 1,36% |
| Forme de bibliotecă la mai multe adrese | 450 | 73.466 | 0,46% |
| Neacoperit, intrări de index | 43.590 | 12.555.547 | 78,84% |
| Inventar complet | 66.827 | 15.925.652 | 100% |

Procesul a terminat cu exit code 0 și toate cele **3.982 amprente** sunt
neschimbate. Față de buffer-closure: **+21 funcții / +1.314 bytes**. Nu există
eșecuri noi față de acel audit. Cele cinci bindings expuse de auditul intermediar
sunt recuperate prin layout-uri și corpuri C++ reale, recompilate separat.
Rămân aceleași **492 inițializări MetaClasses și șase funcții de rețea**.

Paritatea întregului executabil rămâne deschisă. Următoarea țintă este
constructorul owned-string 0x9b78e0 și extinderea verificată a elementelor cu
strings; probele lor nu intră încă în scor. Instrumentele Ghidra/PyGhidra,
objdiff COFF și solverul Z3 rămân disponibile; identitatea față de client se
acceptă numai prin matcherul integral și verificarea adreselor referite.


## 2026-10-09 — owned-string, baze Map și experiment separat de căutare

MetaString are acum constructorul de copiere a textului **0x9b78e0: 88/88**,
folosind baza RString(UninitializedTag{}) și lambda cu captură prin valoare.
Apelul unic Pool_Alloc este la **0x9d4570**. Constructorul de copiere din alt
MetaString este **0x9b7840: 79/79** și folosește aceeași alocare reală, capacitate
cu bitul de ownership și bucla de copiere plus terminatorul. Destructorul comun
RString rămâne activ prin moștenire. FontLocaleType cu localeName{"en_us"} are
MetaCreate **0xa35610: 82/82**, MetaConstruct **0xa35760: 63/63**, și ambii
callback-uri de distrugere identici. Literalul "en_us" este verificat la
VA 0x1ae5498; pointerul empty la VA 0x1b467f0.

ABI-ul constructorilor din lifter este corectat: expresia placement-new produce
pointerul obiectului, pe care apelanții îl pot folosi în EAX. Destructorii au
în continuare rezultat void. Argumentele constructorilor sunt const char* sau
const MetaString& real (dereferențierea pointerului, nu cast integer la reference).
Proba celor cinci apelanți păstrează 23/30/30/63/40 bytes integral identici.

GenericMapPlaceable are constructorul **0xa21380: 60/60**, cu MapPlaceable
**0xa22bb0: 54/54** vizibil în același TU. MapBehavior are constructorul
**0x349ce0: 139/139** în TU separat și MetaConstruct **0x3427f0: 9/9**.
Prefixul de inițializare al unui ancestor poate fi eliminat din corpul candidat
numai dacă baza intermediară nu face decât apelul ancestorului și store-ul vptr.
O inițializare suplimentară de membru este respinsă. Acest guard păstrează
MapAudio **0xa22520: 110/110**. Generatorul are acum **112 constructori /
111 RVA-uri / 16.233 bytes**, cu toate corpurile acceptate verificate.
`gen_lifecycle_aliases.py` publică șapte instanțieri reale pentru cele patru
forme triviale și callbackul MapBehavior, fără aliasuri lipsite de corp.
**70 de teste tools trec**.

Auditul owned-font intermediar are **21.104 funcții / 3.021.285 bytes / 18,97%**,
503 eșecuri; toate cele 3.983 amprente sunt neschimbate. Recuperarea FontLocaleType
0xdbbe0 este reală. Regenerarea shard-urilor Small cu ambele ABI-uri de constructor
și cu modele mai precise face însă explicite și alte bindings de metadate înainte
necunoscute matcherului. Lotul normal înaintea experimentului este astfel:
**21.105 funcții / 3.017.924 bytes / 18,95%, 536 eșecuri**. Din acestea530 sunt
MetaClasses și 6 rețea; față de colors-arrays-closure, sunt 39 bindings noi și
FontLocaleType recuperat. Acest lot încă necesită închiderea dependențelor.
Nu se ascunde scăderea de acoperire prin eliminarea corpurilor Small identice.

**Experimentul solicitat de utilizator este exclusiv în
experiments/reconstruction_search/**. Motorul de căutare are maximum 16 încercări
per caz, păstrează eșecurile într-o bază SQLite, clasifică diferențele și ordonează
regulile cunoscute după rezultate. Nu modifică matcherul, generatoarele, header-ele
sau lista M.sources; nu publică surse, layout-uri ori aliasuri. Obiectele sunt
scrise în directorul experimental. Seed-urile semantice și constrângerile de tip/
ownership sunt furnizate; acesta nu este un decompiler autonom general.

Măsurarea curată din runs/measured-v1.sqlite3:

| Caz | Origine | Compilări inițiale | Rezultat |
|---|---|---:|---|
| Owned-string 0x9b78e0 | Control deja reconstruit |2|72/88→88/88 prin lambda-value|
| Probability owners 0xa64c90 | Neacoperit în producție |3|ipoteze1/2/3 pointeri, ultima79/79|
| Clock Now 0xa2c930 | Holdout neacoperit |5|rămâne38/46, nu este acceptat|

Holdout-ul nu antrenează prioritățile. Repetarea celor trei cazuri folosește
**zero recompilări**; căutarea tabloului trece direct de la ipoteza 1 la 3,
reducând trei încercări la două. **Șase teste de guard** trec, inclusiv targets
greșite, extent incomplet, captură de reference, separarea holdout și refuzul
scrierii în producție. Această evidență demonstrează reutilizarea căutării pe
un domeniu delimitat, nu automatizarea unei proporții din întregul executabil.

Auditurile COMPLETE înainte și după experiment, search-isolation și
search-isolation-after, sunt **identice integral**: 21.105 funcții, 18,95% și
aceeași listă de 536 eșecuri. Cele **3.986 amprente** și lista surselor sunt
neschimbate; raportul este experiments/reconstruction_search/runs/isolation_audit.json.
Regresiile de bindings aparțin lotului normal anterior înghețării, nu experimentului.
Probele izolate au deja 31 MetaDestroy triviale 15/15, opt alte callback-uri și
closure-urile lor reale; acestea nu sunt publicate încă în lotul auditat.

Bundle-ul vfx_candidate rămâne experimental: **12/12 corpuri / 808 bytes**,
cu 5 layout-uri tipizate, destructori/pointer ownership naturale și două TU-uri
separate. Constructorii nu sunt revendicați. Contorul QPC **0x9cbbc0: 33/33**,
precum și ceasul Now 38/46, rămân în probe. Paritatea integrală a executabilului
și un termen credibil până la 100% rămân neîndeplinite.


### 2026-10-09 — închiderea normală a bindings, separată de experiment

După cele două audituri identice ale experimentului, reconstrucția normală
publică 31 de instanțieri MetaDestroy triviale, cu corpuri reale de 15 bytes.
LifecycleAliases are acum 38 corpuri verificate. Acestea închid dependențe
expuse de regenerarea Small, nu sunt rezultate publicate de motorul experimental.

Noul generator normal tools/gen_meta_placements.py verifică 13 corpuri complete:

| Corp | RVA | Bytes identici |
|---|---:|---:|
| ILogicBoolDriver constructor separat | 0xa21cf0 | 9/9 |
| std::map Find_lower_bound pentru registry | 0xf95b0 | 73/73 |
| std::map Insert_node | 0x124b60 | 489/489 |
| std::Throw_tree_length_error | 0x125680 | 10/10 |
| SummonerRegistry::Register | 0x63c7c0 | 133/133 |
| Class_bafabcc8 placement | 0x26f0c0 | 72/72 |
| CollectiblesEsportsTeamData placement | 0x2d0b90 | 77/77 |
| GDSMapObjectBannerInfo placement | 0x2d09e0 | 18/18 |
| HasReceivedAnimEmoteEventBoolDriver placement | 0x2d0a90 | 20/20 |
| IsLocalPlayerBoolDriver placement | 0x2d0ae0 | 20/20 |
| IsMovingBoolDriver placement | 0x2d0b30 | 20/20 |
| SummonerIconData placement | 0x2d0c40 | 66/66 |
| SummonerIconData post-load registry | 0x2d0d00 | 19/19 |

MetaPlacementSupport.h păstrează globalele ca pointeri reali: singletonul la
VA 0x36ed6c0 și registry-ul la VA 0x2aa7460. Baza goală LevelSingleton înregistrează
obiectul înaintea inițializării BinObject și a membrilor; Class_bafabcc8 are
ReflectedBuffer<u32> la +4 și std::list<u32> la +16. Link-urile serializate din
SummonerIconData și BannerInfo au storage nativ de patru bytes, fără ownership.
Registry-ul are std::map la +0x1c; Register și Find stau în același TU pentru
forma de inlining dovedită. Nu se adaugă atribute pentru a forța codul.

Generatorul probează înaintea publicării, păstrează metadatele, descriptorii,
corpurile tuturor callback-urilor și verifică lungimea completă și fiecare țintă.
Rerularea este verificată: headerul temporar folosește o singură definiție a
suportului. Generatorul vechi de constructori omite declarațiile scalar extern
int ale celor două globale tipizate, păstrând 112 corpuri / 111 RVA-uri /
16.233 bytes. MetaFunctions este regenerat cu instanțierile deținute de noile TU-uri.
Cele 70 teste existente și două teste noi trec; acestea resping drift-ul de
size/offset/corp, un prefix scurt identic și un target greșit.

Auditul complet progress-2026-10-09-placements-closure rulează cu 3.993 intrări
înghețate în obj/root_placements_closure_progress_inputs.json. Rezultatul net al
acestui lot trebuie luat din auditul încheiat, nu din suma probelor (mai multe
corpuri împart adrese deja acoperite). Bundle-ul experimental VFX și clock-ul
rămân nepublicate; constructorii VFX și ceasul 38/46 sunt încă deschise.


**Audit placements-closure încheiat:** 21.143 funcții / 3.022.732 bytes /
18,98%, 499 eșecuri. Toate cele 3.993 amprente și lista surselor sunt
neschimbate. Față de search-isolation: 38 bindings închise și un eșec nou Small
la 0x2d0d00. Acesta are 19/19 bytes, dar callee-ul generic T63c7c0 nu este ABI-ul
void SummonerRegistry::Register verificat. Corpul este transferat către
MetaVirtual2<SummonerIconData> real, cu verificare integrală de 19 bytes și două
ținte exacte. NATIVE_OWNERS previne regenerarea vechiului corp generic; callback-ul
primește revendicarea primară, fără pierdere sau substituire a funcției din scor.

Review-ul independent a verificat identitatea fișierelor regenerate. Lacuna de
fingerprint a helperilor nativi este reparată: manifestul fixează acum și
ILogicBoolDriver, Find_lower_bound, Insert_node, Throw_tree_length_error și
Register. Cele 20 probe de drift pe cele patru layout-uri sunt respinse, inclusiv
schimbarea numai a corpului Register; toate cele 72 teste tools trec.
Auditul final placements-closure-final rulează cu același set de 3.993 intrări,
actualizat după acest transfer și gardurile noi.

Investigație izolată în timpul auditului: două callback-uri VFX de placement
ies integral din layout-urile candidate: AnimatedVector3fVariableData 0xa59470
84/84 și FlexShapeDefinitionData 0x24e3b0 67/67, fără relocări. Restul constructorilor
candidate încă diferă sau au limită de index neconfirmată; aceste probe nu sunt
publicate și nu intră în scor. Raport: obj/root_vfx_creation_probe_audit.json.
Default-ul FlexValueVector3 copiază vectorul global zero de la VA 0x3715f70,
pe când ValueVector3 implicit scrie trei scalari zero. Cele două forme nu se
substituie doar fiindcă valoarea finală este aceeași.

Inventarul metadatelor indică 301 callback-uri / 259 adrese unice absente din
functions.txt; raportul obj/root_metadata_missing_boundaries.json păstrează
proveniența clasei și a initializerului. De exemplu, 0x24e3b0 este adresa
construct a FlexShapeDefinitionData și limita imediat următoare corpului create
0x24e360 de 80 bytes. Limitele încă nu sunt adăugate; următoarea etapă este
validarea lor independentă și verificarea efectului asupra inventarului complet.
Nu se relaxează matcherul ca să accepte un corp cu ramuri la o limită ambiguă.


**Audit placements-closure-final încheiat:** **21.144 funcții identice /
3.022.751 bytes / 18,98%**, 498 eșecuri (492 MetaClasses și șase rețea).
Procesul a încheiat cu exit code 0; cele **3.993 amprente** și lista surselor sunt
neschimbate. Față de search-isolation: **+39 funcții / +4.827 bytes**, 38 bindings
închise și **zero eșecuri noi**. Transferul primar al lui 0x2d0d00 păstrează
corpul și adresele exacte, eliminând incompatibilitatea vechiului callee generic.
Față de colors-arrays-closure: +56 funcții / +1.492 bytes; FontLocaleType este
recuperat, dar bindingul VfxFlexShapeDefinitionData 0xddc90 rămâne nou expus și
nerezolvat. Nu se pretinde lipsa tuturor regresiilor față de acel reper mai vechi.

Ultimul inventar rămâne 66.827 intrări / 15.925.652 bytes, dintre care
43.535 intrări / 12.553.953 bytes sunt neacoperite. Raportul de închidere este
obj/root_placements_closure_final_audit_summary.json. Prototipul și VFX candidate
rămân separate, cu șase teste experimentale trecute; câștigul de mai sus aparține
reconstrucției normale, nu publicării automate a vreunui candidat experimental.
Paritatea întregului executabil rămâne obiectiv activ; următoarele probe sunt
limitele de funcții dovedite de metadate și constructorii VFX încă neidentici.


### 2026-10-09 — VFX complet și ipoteza pachetului istoric

Generatorul normal gen_vfx_runtime.py și vfx_runtime_layouts.json validează acum
nouă layout-uri și dependența FlexTypeFloat. Fiecare create/construct/destroy/
destruct are propriul corp verificat, inclusiv specializările folded. Trei
helperi reali sunt în TU-uri separate: ProbabilityOwners destructor 79,
FlexValueVector3 owned-pointer destructor 92, allocator fastcall 97.
MetaCreate<AnimatedVector3fVariableData> este thunk-ul de 7 bytes care trece null
în ECX și sare la allocator, nu new inline de 97 bytes. Probabilitatea are două
bool-uri la +0x1c/+0x1d; inițializarea u16 dădea alte instrucțiuni. ValueVector3
implicit construiește un vector scalar zero înaintea pointerului; Flex copiază
vectorul global măsurat. Alinierea și toate dimensiunile sunt probate.

Intrarea functions.txt 0x24e3b0 este adăugată numai după validarea independentă a
PUSH-ului callback în initializerul 0xddc90, octeții imaginii țintă fiind
neschimbați. Este limita create 0x24e360 de 80 bytes și începutul construct de 67 bytes.
Batch-ul de 259 adrese a fost validat read-only: intrări reale, CFG complet,
fără reachability din intrarea precedentă. Preview-ul celorlalte 258 păstrează
discovery/facts 1944; numai ItemRecOverrideRange și CollectiblesEsportsTeamData
au fingerprints normale scurtate care cer revalidare. Lista întreagă încă nu
este adăugată în inventar.

Auditul intermediar vfx-runtime: **21.132 / 3.021.896 bytes / 18,98%, 529 eșecuri**,
66.828 intrări de inventar. Toate cele 4.003 amprente sunt neschimbate. Acesta expune
33 eșecuri noi și închide 2: 20 apelanți Small ai ILogicBoolDriver folosesc încă
Ka21cf0, opt destructori triviali de 16 bytes și MapAudio construct, plus patru
layout-uri VFX care împart destructorii nou verificați. Regresia netă este
raportată; nu se ascunde prin eliminarea numelor din matcher.

Închiderea normală folosește NATIVE_CALLS pentru constructorul ILogicBoolDriver,
transferă callback-urile placement către TU-ul tipizat verificat și regenerează
cinci shard-uri Small. Constructorul MapAudio 110 este păstrat de extensia strictă
thin_base_inline_prefix: parentul trebuie să fie exact prefixul ancestorului plus
un singur store vptr; un membru suplimentar este respins. Constructorii reali:
113 constructori / 112 RVA-uri / 16.343 bytes. LifecycleAliases are 47 corpuri verificate, inclusiv cei
opt destructori 15/15 și callback MapAudio 9/9. Patru noi layout-uri VFX au toate
16 callback-uri integrale: Acceleration 49/36/94/77, Orbital 49/36/94/77,
ParentInheritance 50/36/94/77, Trail 65/52/94/77.

**Ipoteza utilizatorului privind pachetul istoric este investigată efectiv.**
RiotLOL_Client_AB.pdb corespunde EXE AB prin GUID/age; clienții publici sunt
1.0.0.131/1.0.0.132, nu patch 13.1/13.2. Readerul read-only historical_pdb.py
extrage 68.122 publics, 40.627 function publics, 17.994 tag records complete și 3.592 căi
sursă. Refuză PDB-ul AB la EXE 132. Nu sunt schimbări de registry sau execuții de
binare istorice. Există 20 nume scurte nominal comune; familia ValueVector3 este
verificată prin câmpuri PDB și 13 funcții disasamblate, dar ABI/layout-urile diferă.
Detaliile și limitele se află în docs/PROBE_ISTORICE_LOL.md.

Primul callback modern ghidat de aceste ancore este Probability post-load
**0xa581b0: 93/93**, cu patru targeturi float exacte: zero în jur de +/-1e-6 și
unu între 0.9999989867210388 și 1.0000009536743164. Vector2 local al celor două chei
reproduce ordinea SSE; variantele scalarilor separați rămâneau 79/93. Generatorul
normal VFX verifică acum **40 corpuri / 2.593 bytes**. Cele **78 teste tools trec**.
Aceste probe și un audit global încheiat sunt evidențe distincte; paritatea
întregului executabil rămâne obiectiv activ.


**Audit vfx-runtime-closure încheiat:** **21.169 funcții / 3.022.665 bytes /
18,98%, 510 eșecuri**, cu inventar 66.828 intrări. Toate cele **4.003 amprente**
și lista surselor sunt neschimbate. Față de auditul intermediar: +37 funcții și
+769 bytes; cele 33 eșecuri expuse acolo sunt închise, dar regenerarea a expus
13 bindings UI noi. Față de placements-closure-final: +25 funcții, -86 bytes,
VfxFlexShapeDefinitionData recuperat și cele 13 bindings UI noi. Nu se declară
absența tuturor regresiilor față de acel reper. Rămân 504 MetaClasses și șase
funcții de rețea. Raport: obj/root_vfx_runtime_closure_audit_summary.json.

Cele 13 callback-uri UI sunt probate separat: fiecare are 9/9 bytes, dar
callee-ul real de constructor nu are încă numele C++ verificat. Două baze
abstracte nu au construct în metadate și le lipsește declarația de constructor:
UiElementData → 0xadfd20, UiElementAsset → 0xadfc40. La cei 12 derivați
Class_a34b6ba4 este o bază intermediară: după apelul UiElementData,
constructorul copilului inițializează prefixul intermediar și suprascrie vptr. Constructorii derivați apelează
aceste baze, în locul inițializării implicite care dă primul mismatch la +3.
Probele sunt în obj/root_ui_effect_placements_audit.json. Următoarea închidere
este reconstrucția acestor două baze și revalidarea celor 13 constructori reali;
nu se publică aliasuri numai pentru cei 9 bytes similari ai wrapperelor.

Raportul istoric este în docs/PROBE_ISTORICE_LOL.md; pachetul și experimentul
rămân neatinse. Callback-ul Probability post-load 93/93 este primul câștig modern
concret ghidat de noile ancore, fără a presupune același layout sau ABI între ani.


**Clarificarea scorului, 2026-10-09:** procentul are două zecimale, dar
placements-closure-final are 18,98039088%, iar vfx-runtime-closure 18,97985087%.
Ambele sunt afișate 18,98%. Față de reperul anterior: +25 funcții, -86 bytes
confirmați, cu 13 bindings UI noi și VfxFlexShapeDefinitionData recuperat.
Rezultatul local Probability post-load 93/93 este real; încă nu justifică un
câștig net de acoperire față de acel reper. Constructorul 0xadfd20 alocă un obiect
runtime de 32 bytes și apelează helperul 0xae0ac0; trebuie reconstruit și verificat
acest callee pentru închiderea sigură a familiei UI. UiElementAsset 0xadfc40
apelează constructorul UIElement 0xadfb60 și folosește constantele/vectorii
măsurați din imagine. Aceste corpuri rămân următoarea țintă normală.

### 2026-10-09 — constructorii și proprietarii UI integrați normal

Identificarea prin vtable → GetClass → descriptor corectează eticheta inițială:
`0xadfd20` este **UiElementData**, nu UiElementAssetData. UiElementAssetData
este intermediarul abstract de 36 bytes, fără câmpuri reflectate proprii.

`tools/gen_ui_elements.py`, manifestul `tools/ui_element_layouts.json` și
`UiElementOwners.h` reproduc proprietarii nativi. Manifestul verifică baza,
dimensiunea, alinierea, toate câmpurile reflectate și wrapper-ele lor, corpurile
callback-urilor/constructorilor, constantele și corpul extern Release folosit.
Înainte și după publicare se verifică lungimea independentă a fiecărui corp
și toate țintele relocărilor; un prefix identic nu este suficient.

Auditul local `obj/root_ui_elements_audit.json` confirmă **26 de corpuri / 1.205
bytes** (suma include callback-uri pliate și nu reprezintă câștigul global):

- UiElementData ctor `adfd20`: **107/107**; UiPositionRect ctor `ae0ac0`: **111/111**.
- UIElement ctor `adfb60`: **220/220**; UiElementAsset ctor `adfc40`: **153/153**.
- Deleting destructors: UiElementIData **48/48**, UiElementData **61/61**,
  UiPositionRect **46/46**, AnchorSingle **33/33**, UIElementI **49/49**,
  UIElement **71/71**, UiElementAsset **92/92**.
- AnchorSingle placement **37/37**, create **50/50**; UiPositionRect create
  **24/24**, placement **9/9**; șapte GetClass de **6/6** și wrappers virtuali
  **15/15** și **11/11** pentru cele două clase concrete de poziționare.

Forme de sursă importante: AnchorSingle are constructor implicit, placement
`new(p) AnchorSingle`, dar în UiPositionRect alocarea este **`new AnchorSingle()`**;
value-init produce cele două zero-stores înaintea copiei din constante.
UiElementIData are MetaString și link cu destructor care resetează scalarul.
UiElementData deține UiPositionRect, iar acesta deține AnchorBase prin delete
virtual. UIElement deține la +0x30 o alocare trivială de 12 bytes, eliberată cu
standard sized delete necondiționat. UiElementAsset deține la +0x80 o referință
nullable cu Release. UIElementI destructor trebuie defaultat în prima
declarație; constructorii UIElement/Asset sunt în TU-uri separate, iar
destructorii derivați sunt defaultați într-un TU comun. Flags standard, fără
atribute artificiale. Flag-ul Asset +0x84 și vectorul +0x98 sunt inițializate
în corp după inițializările scalare ale membrilor.

Generatorul constructorilor reali confirmă acum **126 corpuri / 125 RVA-uri /
17.544 bytes**, cu 4 candidați respinși; cele **13 placements UI de 9 bytes**
care blocau bindings sunt acum integral exacte, inclusiv țintele către
constructorii reali. `obj/root_ui_effect_placements_closed_audit.json` păstrează
verificarea. Regenerarea MetaFunctions păstrează 1.924 claims și 3.934 aliases
pliate verificate din 3.978 candidați. **80 de teste trecute**.

Auditul complet `progress-2026-10-09-ui-elements` pornește cu **4.013 amprente /
901 surse** înghețate. Scorul anterior rămâne reperul până la terminarea auditului.

Probleme deschise: Release `aaa4c0` are ABI ECX/no stack args/EAX demonstrat,
dar corpul de 231 bytes nu este reconstruit sau revendicat. Modelul virtual
generic BinObject este incomplet: slotul 2 UiElementIData/UiElementData și
Class_a34b6ba4 este `_purecall`, în timp ce UIElement/Asset folosesc la slotul 2
o metodă cu parametru vector și `ret 4`. Potrivirea corpurilor și adreselor
vptr nu dovedește încă toate sloturile/data vtable sau executabilul complet.
Aceste diferențe rămân explicit parte a obiectivului de paritate bit cu bit.

**Închiderea legăturilor UI și binder, aceeași zi:** auditul complet intermediar
`progress-2026-10-09-ui-elements` a terminat cu **21.175 / 3.022.424 bytes /
18,98%, 528 eșecuri**. Cele 4.013 amprente și setul de surse au rămas stabile.
Cele 18 eșecuri noi sunt apeluri Small care încă declarau constructorii UI sub
ABI generic `T<rva>::f`; cele 13 bindings metadata nu erau încă recuperate,
fiindcă wrapper-ele exacte existau numai în probe, fără claims normale.

Corecția normală adaugă cele patru ABI-uri constructor în NATIVE_CALLS și
regenerarea Small_a60000 cu placement-new tipat. `gen_meta_ctors.py` elimină
apelul bazei numai pe receiverul exact `this`, tipul corect și ABI-ul demonstrat
fără argumente; țintele și corpurile ctor rămân verificate după transformare.
`UiElementPlacements.cpp` publică acum cele 13 wrapper-e numai după verificare.
NATIVE_OWNERS le exclude din liftarea generică, iar claims sunt promovate
`same`→`match` după eliminarea vechiului proprietar Small. Auditul UI local
final are **39 corpuri / 1.322 bytes** (sumă cu folding), iar verificarea directă
`obj/root_ui_elements_bindings_closed.json` confirmă **13/13 inițializări metadata**.
Generatorul păstrează cele 126 ctor-uri exacte și **81 de teste trecute**.

Investigația rezidualului ZoneD Clone `2f2780` găsește la `2dc743` construcția
reală a unui callable MSVC `std::bind(&Context::Method, context,
std::placeholders::_1)`: octetul de la +8 este placeholder-ul gol copiat, nu un
bool de stare. `client-src/src/LnpBoundCallback.cpp` instanțiază explicit
`std::_Func_impl_no_alloc`, fără funcție auxiliară artificială. Flags
`-O2 -std:c++17 -GR-`, `_HAS_STATIC_RTTI=0`. Copy și Move sunt ambele **35/35**
la `2f2780`, Invoke **10/10** la `2f2a00`, TargetType **5/5** la `125630`
cu abort `f5e535`, Delete **21/21** la `2f27b0` cu sized delete `9bb940`, Get
**4/4** la `10aa40`. **75 bytes unici de funcții și 24 bytes vtable / șase
ținte COFF** sunt controlați de `python tools/verify_bound_callback.py` și
`tools/bound_callback_layouts.json`, inclusiv amprenta locului de construcție.
Vechile blocuri manuale Clone/Invoke/Delete au fost înlocuite cu familia
standard. Tipul canonic/cv al argumentului rămâne opac; proba demonstrează
ABI prin referință, fără a revendica metoda sau funcția originală de construcție.

Probele virtuale suplimentare identifică `fb3474` ca root de **două sloturi /
8 bytes**; tabelul de trei sloturi începe la `fb347c`. Getterul de bounds
`aedc20` este **16/16**, cu Vector4 real la +0x54; ctor220 și dtors49/71/92
rămân exacte. Rădăcina UIData de două sloturi și tabelele sale pure de trei
sloturi sunt probate separat. Tabelele runtime au 28/40/40 intrări, dar ABI-ul
sloturilor rezervate nu este demonstrat; scheletele de probă rămân în obj.
Class_a34 deține la +0x44 un AtlasData de 44 bytes; destructorul și layout-ul
Atlas sunt următoarele probe. PDB-ul AB nu oferă corespondență nominală/ABI
directă pentru ierarhia modernă; `obj/historical-lol/ui_concordance_report.md`
consemnează respingerea getterelor GFx/HudRect cu struct-return/alte argumente.

Auditul complet final al lotului `progress-2026-10-09-ui-bound-closure` pornește
cu **4.017 amprente / 903 surse** înghețate. Acoperirea netă rămâne de stabilit
prin acel audit, fără a însuma probele locale sau datele vtable în procentul
de cod.

## 2026-10-10 — UI Atlas complet, layout-uri din callback-uri, căutător de variante, audit în 1–3 minute

**Familia UI Atlas (surse de mână, `client-src/src/UiAtlas*.cpp`).** Cele patru clase care furnizează
texturi sunt identice cu clientul: AtlasData, AtlasData3SliceH, AtlasData3SliceV, AtlasData9Slice —
constructori (`aded90` 114, `adee10` 114, `adee90` 142, `adef20` 86), destructori, callback-urile de metadate,
`GetTexture` (`ae6850` 318, `ae6700` 104, `ae6770` 90, `ae67d0` 120) și calculele `CalculateThreeSliceH`
`ae63e0` 300/300, `CalculateThreeSliceV` `ae6510` 288/288, `CalculateNineSlice` `ae4e40` 347/347,
`CropAtlasUV` `aecd80` 192/192. Moduri: 0 / 1 / 2 / 3. Lecții de formă: codul vectorial al lui Riot este scris pe
componente (bucle `for i < n: c[i] *= s`), forma cu `.x` / `.y` separate dă altă ordine a instrucțiunilor;
constructorii la care callback-urile sar (în loc să-i aibă inline) sunt declarați în clasă și `= default`
în alt fișier; `TextureBorders` are doi `Vector2` (`first`, `second`): 9Slice le scrie pe amândouă, 3Slice
doar pe primul. Intrarea `0xadc5a0` a fost adăugată în `functions.txt` (callback împins în inițializatorul
`0xe1ab0`; fără ea funcția `adc570` părea mai lungă). Opt revendicări generice din `Small_a60000.cpp` au
fost cedate surselor tipizate prin `NATIVE_OWNERS`.

Deschis: destructorul clasei intermediare `Class_a34b6ba4` (`ae1160`) este 85/85 într-o probă cu destructor
implicit și `UiDataOwner<ui_native::AtlasData>` la +0x44; nu este publicat, fiindcă layout-ul clasei stă în
`BinClasses.h` generat (cinci destructori derivați îl apelează: `ae26d0`, `ae2720`, `ae27e0`, `ae2810`,
`ae2850`). Regulă măsurată: destructorul implicit sau defaultat la prima declarație nu scrie vptr;
cel definit de utilizator îl scrie.

**Layout-uri din callback-urile de plasare (`tools/gen_poly_placements.py`).** 487 din cele 492 de eșecuri
erau inițializatori de metadate al căror callback era ridicat generic (`?k<rva>@@`). Pentru clasele polimorfe al
căror `MetaConstruct` doar stochează constante, stocările + membrii reflectați dau direct membrii clasei.
Manifest: **114 clase** (frunze, fără constructor propriu), `gen/PolyPlacementCallbacks.cpp`: **216 callback-uri
identice** (114 `MetaConstruct` + 102 `MetaCreate`; 12 `MetaCreate` neidentice lăsate afară). Corectat în
același timp un defect vechi din `gen_meta.create_stores`: testul „pointer de vtable” era `v > BASE`, deci
lua și un float (1.0f) drept vtable și pierdea inițializatorul primului membru la clasele nepolimorfe.
Rămase pe categorii (proba de după integrare): 257 de callback-uri care apelează constructori de membri,
67 care scriu în baza fără layout, 80 nepolimorfe, 10 care iau un vector dintr-o variabilă.

**Căutătorul de variante (`tools/permute.py`)** și **cache-ul de compilare** sunt descrise în
`docs/RECONSTRUCTIE_TOOLING.md`. Măsurat: `CalculateNineSlice` de la 332/347 la identic în 26 de variante /
3 secunde; `LnpWorker::Post1` negăsit în 1.584 de variante / 5 minute.

**Audit `progress-2026-10-10-poly-placements`: 21.468 funcții / 3.043.754 bytes / 19,11 %, 424 eșecuri**
(de la 21.208 / 18,98 % / 496 la începutul zilei; auditul intermediar `ui-atlas`: 21.234 / 19,02 % / 492).
68 de eșecuri închise, niciunul nou. Durata auditului: ~35 de minute înainte, **2 min 32 s** cu compilare
în paralel și **59 s** cu obiectele din cache; cele două rulări dau același raport JSON. 92 de teste trec.

### 2026-10-10, seara — ramificații în lifter, pilotul de ciorne cu agenți, căutătorul lăsat pe rețea

**Lifter-ul generic (`tools/gen_small.py`) reface acum funcții cu ramificații simple.** Până azi orice salt
condiționat oprea liftarea (616 funcții respinse cu „branch” numai în regiunea 0x100000–0x180000). Forma
adăugată: un salt condiționat înainte sare peste un bloc → `if (condiția inversă) { bloc }`; blocul fie cade
în ținta saltului (registrele pe care le-a schimbat devin necunoscute de acolo), fie se termină cu propriul
`ret` (`if (..) { ..; return x; }`). Blocurile se pot îmbrica. Rezultat pe cele 23 de shard-uri:
**4.156 → 4.964 funcții Small identice**. Două corecții cerute de rulare: (1) un candidat care nu compilează
(un global declarat cu tip real în alt header) nu mai anulează tot shard-ul — `compilable()` citește liniile
de eroare ale compilatorului și lasă afară doar vinovații; (2) callback-urile descrierilor de clase și
constructorii/destructorii pe care ele îi apelează NU sunt ridicați generic când au ramificații
(`gen_poly_placements.callbacks()`): sub nume generic ar lua numele de care are nevoie inițializatorul
descrierii (prima rulare a produs astfel 112 eșecuri noi de legare; după regulă: zero).
Forma `if/else` (blocul se termină cu `jmp` peste ce urmează) este și ea liftată, dar pe shard-ul de probă
nu a dat nicio funcție identică în plus: compilatorul așază altfel cele două ramuri. Rămâne în cod, fără câștig.

**Audit `progress-2026-10-10-branches`: 22.279 funcții / 3.080.873 bytes / 19,35 %, 421 eșecuri**, niciun
eșec nou față de auditul `poly-placements` (21.468 / 19,11 % / 424). Față de dimineață (21.208 / 18,98 % / 496):
+1.071 funcții, +0,37 puncte procentuale.

**Căutătorul pe cele 5 funcții de rețea (20 de minute fiecare):** `LnpMessage::Read` `2dcd40` — IDENTIC după
39 de variante / 6 secunde (rescrierea „valoare ținută într-un local”), aplicat în `LnpMessage_Read.cpp`;
era deschisă din runda a șaptea, după 16 forme încercate de mână. `LnpDatagram::Write` a coborât de la 36 la
18 instrucțiuni diferite în 10.117 variante, fără identitate; `Post1` (6.067 variante) și `Post2` (4.441)
negăsite.

**Pilot de ciorne scrise de agenți (măsurat și oprit).** `tools/draft_batch.py` pregătește pentru fiecare
funcție deschisă un pachet (dezasamblare, pseudo-C Ghidra, numele obligatorii ale țintelor) și verifică
ciorna cu matcherul. 6 agenți Sonnet pe 48 de funcții alese la întâmplare: până la oprire 29 încercate,
19 identice = 1.210 bytes = 0,0076 % din cod (33–64 bytes: 12 din 15; 65–128: 7 din 13; 129–256: 0 din 1),
pentru aproximativ 10 % din cota de 5 ore a utilizatorului. Concluzie: tehnic merge, dar ca metodă de masă
este de ordinul a o mie de asemenea rulări pentru 10 % din cod; nu se mai pornesc loturi de agenți fără
cerere explicită. Cele 19 ciorne identice sunt în `client-src/obj/draft/<rva>/f.cpp`, nepublicate.

**Ce ar putea prinde o unealtă mecanică, măsurat pe funcțiile deschise din codul lui Riot:** funcții cu bucle
5,89 MB (37,0 % din cod), peste 4096 bytes 1,28 MB (8,0 %), virgulă mobilă + cadru de stivă 0,98 MB (6,2 %),
cadru de stivă cu ramificații 0,80 MB (5,0 %), fără ramificații 0,32 MB (2,0 %), o ramificație 0,29 MB
(1,8 %), două 0,13 MB, trei 0,10 MB, patru sau mai multe 0,32 MB. Obiectivul „+10 % într-o zi” nu este
atins și nu poate fi atins cu uneltele existente: pârghiile mecanice rămase sunt de ordinul 1–3 %.

Proba `tools/permute_small.py` (căutătorul peste funcțiile ridicate de lifter care nu ies identice): 30 de funcții la întâmplare din shard-ul e0000, 20 de secunde fiecare — **0 găsite**. Diferențele acolo țin de tipuri, lățimi și convenții, pe care rescrierile de formă nu le ating; nu merită rulat așa.
