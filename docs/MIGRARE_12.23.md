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
