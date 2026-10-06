# De unde vine fiecare piesă

**Regula:** ProiectBattleArenaPc nu preia nimic din proiectul web BattleArena (acela a fost construit cu aproximări).
Fiecare comportament vine dintr-una din sursele de mai jos, în ordinea asta:

1. **Datele jocului:** fișierele League (`.bin`, `.anm`, `.skl`, `.skn`, `.mapgeo`, `.aimesh_ngrid`, `.tex`), citite de parserele noastre,
   plus **metadatele claselor** (numele, tipurile și valorile implicite ale câmpurilor din `.bin`), extrase din joc de
   comunitate (lol-meta-classes, servite de meta-api.leaguetoolkit.dev; copiile folosite sunt în `research/meta/`).
2. **Shader-ele jocului:** bytecode-ul DX11 compilat de Riot din `ShaderCache.dx11`. Fie îl dezasamblăm și reproducem formula, fie îl rulăm ca atare.
3. **Măsurători pe jocul real:** înregistrări sau capturi din LoL, comparate cadru cu cadru.
4. **Alegere proprie:** doar unde 1–3 nu spun nimic, marcată în cod și în tabelul de mai jos, cu motivul.

**Clienți vechi (fișiere Riot, alt patch):** clientul original 4.20 (arhive RAF, citite cu `tools/raf.py`) are scripturi Lua
compilate ale hărții și ale minionilor (`LEVELS/map11/Scripts/LevelScript`, `NeutralMinionSpawn`, `DATA/Scripts/*AI`), cu
logica Riot din 2014. Se folosesc pentru arhitectură (cum e organizată logica). Valorile se iau din datele de acum sau din
documentație, iar diferențele se marchează. Scripturile vrăjilor din 4.20 sunt tot doar steaguri. Serverul LeagueSandbox
din același folder e ghicit de comunitate și **nu** e sursă. Clientul 14.1 (arhivă) e tot dată Riot, bună de comparat.

**Patch-ul țintă: 14.1** (alegerea utilizatorului, 2026-10-02). Jocul citește datele din folderul numit în
`data-path.txt` (clientul original 14.1.5527117); `game-data/` (un patch mai nou) rămâne doar pentru comparații.
Cititoarele acceptă ambele formate acolo unde diferă: statisticile simple (`baseHP`) față de `baseHPModifiable`,
`mapgeo` v15 față de v17/v18, eșantionatoarele `samplerName`/`TextureName` (14.1) față de `TextureName`/`texturePath`,
texturile `.dds` (14.1) față de `.tex`. Harta e desenată cu **shader-ele compilate Riot** (vezi „Materialele hărții” mai jos).

Codul jocului (executabilul) nu se dezasamblează. Licența Riot o interzice, iar proiectul citește doar formate de date.

Ce nu se poate afla din 1 și 2 rămâne „neverificat” până la o măsurătoare (3). Nu se înlocuiește cu ce făcea proiectul web.

---

## Inventar (actualizat 2026-10-01)

| Piesa | Sursa | Stare |
|---|---|---|
| Harta (geometrie, materiale, formula pixelilor) | date + shader Riot (`defaultenv`, `vertexdeform`) | fidel |
| `TERRAIN_XFORM` (unde cade harta de nuanță a ierbii) | date: `MapContainer` boundsMin..boundsMax; verificat prin potrivirea tufișurilor din textură cu grila | fidel (în zgomotul potrivirii) |
| Personaje: mesh, schelet, skinning | date + shader Riot (`lit_uber_vs`) | fidel |
| Graful de animație (Sequencer, ConditionBool/Float, Parametric, Parallel, `mFlags` 2 = buclă) | date | fidel |
| Selector, Parametric, amestecare | — | neimplementate, deocamdată primul copil / cel mai apropiat |
| Tabelul de tranziții (`mBlendDataTable`) | date | fidel |
| Timpul de tranziție implicit 0,2 s | meta: `TimeBlendData.mTime` implicit 0,2 | fidel pentru intrările fără `mTime`; pentru perechile absente din tabel, presupus același |
| Rotirea unității spre direcția de mers (acum instantanee) | alegere proprie | **neverificat → măsurătoare** |
| Lumina personajelor (ambient cube, `SELF_ILLUMINATION`) | shader Riot + `MapSunProperties` | formula fidelă; `LIGHTGRID_SCALE` = (1,1) neverificat |
| Înălțimea terenului, grila de navigare | date (`aimesh_ngrid`, din `MapContainer`) | fidel |
| A* + îndreptarea traseului | alegere proprie (algoritmul jocului e în executabil) | **neverificat → măsurătoare pe trasee** |
| Raza de pathfinding, viteza | date (`CharacterRecord`) | fidel |
| Pozițiile clădirilor | date (amprentele `StructureWall` din grilă) | fidel |
| Etichetele clădirilor (echipă, bandă, nivel, tip) | date: octeții de regiune ai grilei (banda cea mai apropiată, inelul, regiunea) + mărimea amprentei | fidel (32/32) |
| Orientarea clădirilor | alegere proprie | **neverificat → măsurătoare** |
| Skin-urile clădirilor | date: `objectcfg_srx.cfg` (Order skinID 0, Chaos 3, pentru turnuri, inhibitori, nexus); `MapSkin` Default fără înlocuiri | fidel (32/35 din web erau greșite) |
| Submesh-uri ascunse, texturi pe submesh, graful din legătura skin-ului | date | fidel |
| Particule: citirea definițiilor | date | fidel |
| Particule: câmpuri citite, nume, valori implicite | meta (`VfxEmitterDefinitionData` etc.) | fidel (rescris; web-ul avea implicite greșite: durata 1 în loc de 3, rata 1 în loc de 0, lookup 0/3 în loc de 1/0, nume greșite `boxSize`, `period`) |
| Particule: legile simulării (rezistență exponențială, unitatea vitezei orbitale, câmpurile de forță, tabelele de probabilitate, momentul primei particule, orientarea quad-urilor, întinderea după viteză, înțelesul `colorLookUpType`) | lectura noastră a numelor | **neverificat → măsurătoare** (marcate `[de măsurat]` în `Vfx.cpp`) |
| Particule: formula pixelilor, culoarea pe 8 biți, flipbook | shader Riot (`quad_ps`, `quad_vs`) | fidel |
| Particule: moduri de amestec | statistică pe date (1.109 emițătoare) | dedus, de confirmat |
| Tragerea spre cameră a particulelor | shader `quad_vs` + meta: câmpul `DepthPushPull` | fidel; `depthBiasFactors` citit, dar nefolosit (sens necunoscut) |
| Decalurile de pe sol (deplasarea de adâncime) | alegere proprie | **neverificat** |
| Controlorii de vizibilitate ai hărții | date; `ParentMode` interpretat | parțial |
| FXAA | shader Riot rulat ca atare; pragurile = valorile implicite NVIDIA | pragurile neverificate |
| Server: tick 30 Hz, ordine, WaypointGroup, ENet | cercetare publică (`CERCETARE.md`) | conform cercetării |

Unelte care nu definesc comportament (descărcarea wad-urilor prin `lolcdn.py`, verificarea pozelor oaselor cu `lolchar.py`) pot rămâne. Nu decid ce face jocul, doar aduc date sau verifică.

## Jocul (lobby și intrarea în meci)

| Piesa | Sursa | Stare |
|---|---|---|
| Lobby-ul ca serviciu local HTTP + pagină web, care pornește serverul și clientul | arhitectura League (LCU, `CERCETARE.md`) | conform arhitecturii |
| Champion select: stiluri, fonturi, poze, sunete, texte, structura elementelor | fișierele clientului 14.1 (pluginurile `rcp-fe-*` arhivate de CommunityDragon, layout-urile citite din scripturi; `docs/CLIENT.md`) | fidel ca aspect; comportamentul e al nostru, parțial; duratele fazelor **de măsurat** |
| Ecranul de încărcare | date: `loadingscreen*.bin` și scenele lor din UI.wad, `LoadingScreenBackground` din map11.bin, `loadscreen` din skin0.bin (`docs/INCARCARE.md`) | fidel; așezarea cardurilor **dedusă**, sfaturile lipsesc |
| Ce se încarcă și în ce ordine | jurnalul clientului Riot 4.20 (r3dlog) | ordinea fidelă; cotele barei = timpii noștri măsurați |
| Iconițele campionilor | date: `iconSquare` din skin0.bin al fiecărui campion | fidel |
| Locul de apariție | date: locatorii `__Spawn_T1` / `__Spawn_T2` din `base_srx.materials.bin` | fidel (un singur jucător, în centrul locatorului) |
| Viteza și raza campionului ales | date: `CharacterRecord` | fidel |
| Animațiile vechi `r3d2anmd` v3 (Lux) | format citit și verificat față de pyRitoFile (1e-4) | fidel |
| Abilități, HUD | — | **nu există încă** (faza 3 continuă, faza 4) |

## Lupta: atacul de bază (faza 3)

| Piesa | Sursa | Stare |
|---|---|---|
| Viața, AD-ul, armura, raza de atac, viteza de atac de bază, raportul AS (nivelul 1, fără obiecte) | date: `CharacterRecord` (`baseHP`, `baseDamage`, `baseArmor`, `attackRange`, `attackSpeed`, `attackSpeedRatio`) | fidel; verificat cu valorile cunoscute (Garen 69 AD / 0,625 AS, Ashe 59 / 0,658, Lux 54 / 0,669, Tryndamere 66 / 0,67, Zed 63 / 0,651) |
| Sloturile de atac (`basicAttack`, `extraAttacks`, `critAttacks`), probabilitățile, decalajul de windup | date: `AttackSlotData` | fidel |
| Alegerea slotului după `mAttackProbability`, din fluxul aleator al meciului | lectura noastră | **neverificat → măsurătoare** |
| Clipul atacului, momentul autorat al loviturii, proiectilul și viteza lui | date: `SpellObject` al slotului (`mAnimationName`, `spellCastTime`, `mMissileSpec`, `missileSpeed`) | fidel |
| Cronometrul atacului = 1 / AS; plafon 3,003, prag 0,2 | documentat (LoL Wiki) | conform documentației |
| Windup = timpul atacului × (0,3 + `mAttackDelayCastOffsetPercent`) sau `mAttackCastTime` / `mAttackTotalTime` | documentat (LoL Wiki) + date | conform documentației; modificatorul de windup nu contează la nivelul 1 (fără AS bonus) |
| Raza de atac de la margine la margine (rază + ambele raze de joc, implicit 65) | documentat (LoL Wiki) + date (`overrideGameplayCollisionRadius`) | conform documentației |
| Dauna fizică × 100 / (100 + armură) | documentat (LoL Wiki) | conform documentației |
| O comandă nouă anulează windup-ul; după windup unitatea se poate mișca, cronometrul continuă | documentat (LoL Wiki) | conform documentației |
| Rotunjirea timpilor la tick-uri (în sus, deci Garen atacă la 49 de tick-uri = 1,617 s, nu 1,600 s) | alegere proprie | **neverificat → măsurătoare** (`Match.cpp`, `ticks()`) |
| Zborul proiectilului pe server: tick cu tick, cu viteza `FixedSpeedMovement` `mSpeed`, după țintă (`mTracksTarget`); lovește la atingere (`CastOnMovementComplete`) și dispare (`DestroyOnMovementComplete`) | date (`mMissileSpec`) + meta | pleacă din centrul unității și țintește centrul țintei: **de măsurat** |
| Efectul proiectilului: `mMissileEffectKey` rezolvat prin `ResourceResolver`-ul skin-ului, pornit din osul `mStartBoneName`, spre ținta ridicată cu `mTargetHeightAugment` (`mUseGroundHeightAtTarget`) | date | fidel; `mOffsetInitialTargetHeight` necitit (sens necunoscut) |
| Orientarea proiectilului: axa verticală (+y) a efectului pe direcția vitezei (`VeritcalFacingMatchVelocity`) | dedus din date: săgeata lui Ashe e rotită pe y, dâra ei pornește din -y, semiluna lui Lux merge pe +y | dedus, de confirmat vizual |
| Efectul de lovire: `mHitEffectKey` pe osul `mHitBoneName` al țintei, la momentul trimis de server | date | fidel; orientarea (`mHitEffectOrientType` 1/2) și dacă urmează osul: **de măsurat** |
| Particulele rămase după oprire (`RenderParticlesAfterDestroy` implicit adevărat) | meta | fidel |
| Dârele (`VfxPrimitiveArbitraryTrail` / `CameraTrail`): panglică prin particule în ordinea nașterii, lățimea din scara x, textura repetată la `mBirthTilingSize.x` | date + meta | sensul lui u, `mCutoff`, `mMode`: **de măsurat** |
| `colorLookUpType`: 1 = viața particulei, 3 = aleator, 0 = niciuna, 2 = viața emițătorului | dedus din date (`research/lookup_stats.py`: emițătorii în buclă cu tipul 1 folosesc curbe de apariție-dispariție; tipul 3 apare la texturi „RandomRamp”) | corectat (înainte era 0 = viața, 1 = emițătorul, 2 = aleator, 3 = niciuna); tipul 2 **de măsurat** |
| Viteza de redare a clipului de atac = `spellCastTime` / windup (momentul autorat al loviturii cade la sfârșitul windup-ului) | lectura noastră a câmpurilor (`useAnimatorFramerate` implicit fals sugerează scalarea) | **neverificat → măsurătoare**; `castFrame` (Garen: 10) nu e folosit încă |
| Clipul de atac rulează până la capăt, apoi unitatea revine la Idle/Run | date (lungimea .anm, fără `EndFrame`) | fidel la date; legătura cu cronometrul atacului **de măsurat** |
| Moartea: clipul `Death` ținut pe ultimul cadru; păpușa moartă rămâne moartă | numele din graf; comportamentul după moarte e alegere proprie | **neverificat → măsurătoare** (în Practice Tool) |
| Păpușa de antrenament: modelul, viața 1000, armura 0, clipurile `Spawn`, `Idle1` (3 variante 34/33/33), `Hit`, `Death` cu sunetele lor | date: `PracticeTool_TargetDummy` din `Map11.wad` | fidel |
| Când se redau `Spawn` (la apariție) și `Hit` (la scăderea vieții) | lectura noastră a numelor și a sunetelor | **neverificat → măsurătoare** |
| Tasta T pentru păpușă (în Practice Tool e un buton) | alegere proprie | temporar, până la interfața Practice Tool |
| Alegerea țintei cu click dreapta: cilindrul `selectionRadius` × `selectionHeight`, cel mai apropiat de cameră | date + lectura noastră | forma exactă și prioritățile **de măsurat** |
| Viața afișată în titlul ferestrei | provizoriu | până la HUD (faza 4) |
| Reluarea meciurilor cu atacuri (`server.exe --replay x.basr --combat-log 1`) | — | verificat: reluările ies identice, tick cu tick |


## Materialele hărții: shader-ele Riot rulate ca atare (patch 14.1)

| Piesa | Sursa | Stare |
|---|---|---|
| Codul shader-elor (VS + PS, toate cele 20 de `srx_blend_*`, `defaultenv*`, `vertexdeform`) | `ShaderCache.dx11.wad.client` din 14.1, rulat ca atare | fidel: nicio formulă rescrisă |
| Alegerea variantei compilate | cuprinsul `TOC3.0`: cheia = XXH64 al definițiilor `NUME=VALOARE` sortate, lipite (găsită prin căutare, `research/toc_hash_search.py`; 4.096/4.096 chei decodate, 12.288 de verificări pe conținut fără nepotriviri, `tools/shader_toc.py`) | fidel |
| Definițiile: `featureDefines`, comutatoarele statice (`onByDefault`, suprascrise de `StaticMaterialSwitchDef`), `shaderMacros` ale materialului și ale pass-ului | `data/shaders/shaders.bin` (Shaders.wad) + materialul | fidel |
| Starea motorului în definiții: fără ceața vederii (`DISABLE_FOW`) și fără hărți de umbre (`DISABLE_SHADOWS`), calitate maximă (fără `LOW_QUALITY_MODE`) | alegere proprie, până le implementăm | **temporar** |
| Parametrii: `ParameterN` din definiție, cu valorile numite ale materialului puse în componentele măștii `fields` (1 x, 2 y, 4 z, 8 w, în ordine) | date + lectura noastră a măștii | dedus |
| Constantele pe cadru: `TERRAIN_XFORM` (limitele `MapContainer`), ceața (`fogColor`, `fogAlternateColor`, `fogStartAndEnd`, `fogEmissiveRemap`), soarele (`sunDirection`, `sunColor`, `lightMapColorScale`, `HdrEnvDiffuseScale`), `WORLD_MATRIX` (matricea modelului), `MESH_CENTER` (centrul cutiei) | date (`MapSunProperties` din 14.1) | fidel; `ENV_FOG_…`.z și `TIME`.yzw **de măsurat** |
| `TransitionFactorAndDirection` = (0, 1): Rift-ul fără transformare elementală | dedus din shader-ele `srx_blend_*` (cu (0, 1) nu aruncă nimic și desenează aspectul simplu; (x, 0) crește terenul elemental în cercuri de x·8500…15000) | dedus |
| `GRASS_TINT_MAP`: `mGrassTintTexture` al `MapSkin` „Default”, din `levels/map11/info/` (Map11LEVELS.wad); `GRASS_TINT_MAP_ALTERNATE` = aceeași, `GRASS_INTERP` = 0 | date + lectura noastră (alegerea skin-ului „Default”) | dedus |
| `TERRAIN_BLEND` = textura `MapTerrainPaint` | dedus din nume și din eșantionarea prin `TERRAIN_XFORM` | dedus |
| `GrassDistortSpheres` / `GrassVelocities` (unitățile care trec prin tufișuri) | — | 0 până la implementare |
| Stările de randare: amestecul (factorii 0, 1, 6, 7 = ZERO, ONE, SRC_ALPHA, INV_SRC_ALPHA, ordinea GL), `depthCompareFunc` 3 = LEQUAL, `writeMask` 16 = scrierea adâncimii, cull | meta (valori implicite) + statistică pe date | dedus; `windingToCull` **de măsurat** |
| Eșantionatoare: `addressU/V/W` 1 = clamp, 0 = wrap; filtrare liniară cu mip-uri | statistică pe date / alegere | filtrarea **de măsurat** |
| Intrările vârfurilor: semanticile VS legate de elementele `mapgeo` (`TEXCOORD n` = elementul 7+n) | date | fidel (tufișurile folosesc `TEXCOORD5`) |
| Cititorul DDS: formatul pixelilor la octetul 72 (era greșit la 76), BC2 (`DXT3`), texturi BC mai mici de 4×4 decodate în RGBA | format DDS | corectat |
| Texturile `.dds` ale particulelor din 14.1: nivelurile mip refăcute din nivelul 0 | `Garen_Base_AA_slash.dds` are un dreptunghi alb în mip-urile 1–5 (`.tex`-ul de mai târziu are mip-uri corecte); jocul evident nu îl arată | **de măsurat**: ce făcea 14.1 cu ele |
| Datele noi (`game-data`) | shader-ele lor cer umbre (`SHADOW_COLOR`) | rulează cu `--riot-shaders 0` până la umbre |

## Valurile de minioni, turnurile și sfârșitul meciului (faza 3, 2026-10-02)

Regulile serverului nu sunt în client. Ordinea surselor a rămas aceeași: întâi datele 14.1, apoi documentația **de la data patch-ului 14.1**
(LoL Wiki, reviziile din ianuarie 2024, citite prin `api.php?...&rvstart=2024-01-20`; paginile de azi descriu alt joc), apoi alegeri proprii marcate.

| Piesa | Sursa | Stare |
|---|---|---|
| Constantele modului de joc: rapoartele de daune între eroi, unități și clădiri (`dr_UnitToHero` 0,5, `dr_UnitToBuilding` 0,5), limitele întârzierii de atac (`gcd_AttackMinDelay` 0,4 s, `gcd_AttackMaxDelay` 5 s, deci viteza de atac 0,2–2,5), procentul de windup (`gcd_AttackDelayCastPercent` 0,3), viața inhibitorului (`bar_MaxHP` 4000), vindecarea platformei (`sp_*`) | date: `GameModeConstants` ale modului CLASSIC din `map11.bin` (141 de constante, lista în `research/m141/constants_classic.txt`) | fidel; plafonul de 3,003 pentru viteza de atac era din documentația de azi, acum vine din date |
| Clădirile: poziții, benzi, niveluri (exterior, interior, de inhibitor, de nexus), înregistrarea fiecărui tip de turn | date: obiectele hărții (`GdsMapObject`), blocurile `SpawnAiTurret` ale scriptului de nivel, `objectcfg_srx.cfg` | fidel; turnurile de nexus iau înregistrarea `SR_Nexus` (dedus), cele de fântână `SRUAP_Turret_Order5/Chaos5` (dedus) |
| Valurile: primul la 13 s, apoi la 30 s, 0,8 s între minioni, tunul la fiecare al 3-lea val (de la 850 s la al 2-lea, de la 1500 s la fiecare), super-minionii după inhibitori | date: `BarracksLevelController` | fidel; de la ce moment se numără cele 13 s (aici: intrarea primului campion) **de măsurat** |
| Câți minioni corp la corp și cu baghetă are un val: datele spun `SpawnCount` 2, valul are 3 | documentat (3 de fiecare) + scriptul de nivel 4.20 (`DefaultNumPerWave` 3) | folosim 3; ce numără `SpawnCount` **de măsurat** |
| Creșterile minionilor la fiecare 90 s: viață, daune, armură | date (`MinionUpgradeConfig`) + formulele documentate; verificat: corp la corp 477, 499, 521, 544, 568, 601 | fidel (înainte valorile târzii înlocuiau în loc să se adune, iar plafoanele se aplicau totalului) |
| `MagicResistanceUpgrade` al minionilor | în date există, documentația spune rezistență magică 0 | neaplicat, **de măsurat** |
| Drumul minionilor pe bandă | date: punctele `__NAV_L/C/R` ale hărții | fidel ca traseu; când trec la punctul următor (150 de unități) e alegere proprie |
| Pe cine atacă minionii (cele 7 priorități, „call for help”) | documentat (LoL Wiki, Minion) | conform documentației; cât de des se uită în jur (8 tick-uri) și cât ține „atacă pe cineva” (2 s) **de măsurat** |
| Constantele `ai_Target*` și `ai_MinionTargetingHeroBoost` | date | citite, nefolosite: formula în care intră nu e publică |
| Coliziunea între unități | documentat că există („minion block”); algoritmul e în executabil | **alegere proprie**: cercurile de `pathfindingCollisionRadius` care se suprapun sunt împinse, cel care merge îi face loc celui care stă; `[de măsurat]` |
| Turnul lovește minionii cu o parte fixă din viața lor maximă: corp la corp 45%, cu baghetă 70%, tun 14%, super 5% | documentat (ian. 2024) | conform documentației |
| Dauna turnului crește pe minut: exterior 182 + 12/min de la 0:30 (350 la 13:30); interior, de inhibitor și de nexus + 16/min de la 3:00 | date (valoarea de bază din înregistrare) + documentat (creșterea) | conform documentației |
| Turnul: 30% penetrare de armură; „Warming Up” (+40% la fiecare lovitură pe campion, până la +120%, se resetează după 3 s) | documentat (obiectele turnului, ian. 2024) | conform documentației |
| Ținta turnului: o păstrează cât e în rază; alege tun/super, apoi corp la corp, apoi baghetă, apoi campion; trece pe campionul care lovește un aliat la cel mult 1400 de turn | documentat | conform documentației |
| Protecțiile turnului: plăcile (+40 armură la fiecare 1000 de viață pierdută, până la 14:00; apoi 40 armură), „Fortification” (turnurile exterioare de sus și de mijloc, −50% în primele 5 minute), „Reinforced Armor” (−80% fără minioni inamici în apropiere) | documentat | conform documentației; „în apropiere” = 1000 de unități e **alegere proprie**; „Bulwark”, aurul plăcilor și regenerarea turnurilor de bază lipsesc |
| Ordinea în care pot fi atacate clădirile | documentat | conform documentației |
| Inhibitorul reapare după 5 minute; super-minionii se opresc cu două valuri înainte; valul cu super-minioni nu are tun | documentat | conform documentației |
| Moartea campionului: timpul pe nivel (6 s la nivelul 1) și creșterea cu durata meciului | date: `DeathTimes` + formula documentată | fidel; `mScalingStartTime` / `mScalingPercentIncrease` nu apar în formula documentată, neaplicate |
| Reapariția la punctul echipei, vindecarea de la fântână (2,1% din viața maximă la 0,25 s, pe 1100 de unități) | date (`sp_HealthRegenPercent`, `sp_RegenTickInterval`, `sp_RegenRadius`) | fidel; centrul razei (punctul de apariție) **de măsurat** |
| Sfârșitul meciului la căderea nexusului | — | lumea se oprește; ecranul de final vine cu HUD-ul (deocamdată în titlul ferestrei) |
| Nivelurile, experiența, aurul | date | făcute (vezi „Nivelurile, experiența, aurul” mai jos) |
| Daunele între minioni după avantajul de nivel și de turnuri (`mvm_*`) | date | **neaplicat** (are nevoie de niveluri) |

### Ce arată clientul

| Piesa | Sursa | Stare |
|---|---|---|
| Evenimentele clipurilor: `SubmeshVisibilityEventData` (ce bucăți de model se văd), `ParticleEventData` (efecte pe oase) | date (graful de animație) + meta (valorile implicite) | citite din date; când pornește și când se oprește un efect (`mIsLoop`, `mIsKillEvent`, `mIsDetachable`) e lectura noastră a numelor: **de măsurat** |
| Pistele de animație (`mTrackDataName`) și măștile (`mMaskDataName`): `Attack1` al turnului se joacă peste starea lui | date | fidel pentru două piste; amestecul după prioritate lipsește |
| Stările turnului: `State2_seq`, `State3_seq` (turnul crăpat), `Destroyed_seq` (prăbușirea, apoi molozul) | date (clipurile și evenimentele lor) | clipurile sunt fidele; la ce viață trece în starea 2 și 3 (două treimi, o treime) e **alegere proprie, de măsurat** |
| Efectele comune ale jocului (ruperea turnurilor ș.a.) | date: `GlobalResourceResolver` și sistemele din `Global.wad` (`shared`) | fidel |
| Efectele permanente ale skin-ului (`idleParticlesEffects`) | date | fidel pentru cele cu `effectKey` |
| Efectele vechi `.troy` (proiectilele și loviturile minionilor, explozia inhibitorului, apariția minionilor, laserul turnului) | date: `data/particles/*.troybin` din `DATA.wad` (3.453 de fișiere) | **necitite încă**: e nevoie de un cititor pentru formatul vechi |
| Turnurile nu se rotesc spre țintă | serverul trimite orientarea odată cu atacul | corectat (clientul le rotea) |
| Cititorul `.anm`: două piste pentru același os | format | corectat (strica memoria la animațiile minionilor) |

## Interfața (faza 4, începută 2026-10-02): barele de viață de deasupra unităților

| Piesa | Sursa | Stare |
|---|---|---|
| Ce bară primește fiecare unitate (minion mic / mediu, structură, turn, campion) | date: `unitHealthBarStyle` din skin → `InfoBarStyleSourceMap` (`gameplay.lolfloatinginfobars.bin`, `UI.wad`); implicit 0 (meta) | fidel |
| Forma barei: rama, contorul de viață, punctul de ancorare, straturile | date: elementele din `clientstates/gameplay/ux/lol/lolfloatinginfobars/uibase` (dreptunghiuri într-un layout de 1600 × 1200 + decupaje din `spotlighthealthbaratlas.tex`) | fidel; desenate 1 : 1 în pixeli (`IgnoreGlobalScale`, `DisableResolutionDownscale`), cum se scalează peste 1200 de linii **de măsurat** |
| Culoarea contorului la campioni: verde pentru jucător, albastru pentru aliați, roșu pentru inamici | date: texturile `Green` / `Blue` / `Red` din `AdditionalBarTypes` | fidel |
| Culoarea contorului la minioni și clădiri (în atlas e alb) | datele nu numesc nicio culoare | **dedus**: culorile medii ale contoarelor albastru și roșu ale campionilor; **de măsurat** |
| Înălțimea barei: `healthBarHeight` (implicit 100; minion 47; turn 525–625 cu `healthBarFullParallax`) | date + meta | la turnuri e înălțime în lume; la restul bara urcă pe ecran cu cât ocupă acea înălțime la adâncimea unității, fără scurtarea dată de înclinarea camerei (**dedus**: ca înălțime în lume ar sta la pieptul unității; **de măsurat**) |
| Liniuțele de viață, scuturile, estomparea la lovitură, nivelul, numele, iconițele de stare, mana de pe barele plutitoare | date (există în aceleași fișiere) | **nu sunt încă desenate** |

### Sistemul de interfață și restul HUD-ului (2026-10-02)

| Piesa | Sursa | Stare |
|---|---|---|
| Scenele și elementele (`UISceneData`, `UiElementIconData`, `UiElementTextData`, regiuni, efecte, grupuri de contoare) cu stratul, dreptunghiul, ancora, decupajul din atlas | date: `clientstates/gameplay/ux/lol/<parte>/uibase` din `UI.wad` + meta | fidel la date; **așezarea** (layout de 1600 × 1200 scalat cu înălțimea ecranului, fiecare element păstrându-și distanța față de ancoră) e **dedusă, de măsurat** |
| Ce element are ce rol (portret, nivel, contor de viață, text de aur ...) | date: controlerele `gameplay.<parte>.bin` numesc elementele pe roluri | fidel; ce face controlerul cu ele e codul jocului, scris aici după numele rolurilor |
| Elementele fără `Enabled` stau ascunse până le arată controlerul | lectura datelor (doar ramele statice au `Enabled: 1`) | dedus |
| Culorile din fișierele de interfață sunt în ordinea albastru, verde, roșu | dedus din date: aurul butonului de magazin e `[153, 247, 255]`, turnul aliat pe minimapă `[239, 199, 72]` | dedus (altfel aurul ar fi turcoaz) |
| Fonturile: descrierea (culoare, contur, umbră), fișierul și mărimea la o înălțime de referință | date: `ux/fonts` + fișierele `.otf` / `.ttf` ale jocului din `UI.wad` | fidel; literele le desenează Windows (GDI) din fișierele jocului; conturul e textul repetat în jur (**alegere proprie**) |
| Rama jucătorului: portretul (`iconCircle`), nivelul, contoarele de viață și de resursă cu valorile lor, bara de experiență, iconițele celor 4 abilități (`mImgIconName`) și a pasivei (`passive1IconName`), tastele | date | fidel; abilitățile apar gri („neînvățate”) până există |
| Panoul de statistici (AD, AP, armură, rezistență magică, viteză de atac, viteză) | date + valorile de pe server | fidel; cele avansate rămân închise |
| Inventarul: rama, sloturile goale, aurul | date | fără obiecte încă |
| Antetul: scorul echipelor, K/D/A, minionii omorâți, timpul, FPS | date | fidel |
| Minimapa: imaginea și pătratul de lume pe care îl acoperă (14.850), iconițele pe tip de unitate cu mărimea și culoarea pe echipă, ce vede camera | date: `mMinimapBackgroundConfig` al skin-ului hărții, `MinimapData.mIcons` | fidel; pătratul începe în originea lumii (dedus, turnurile cad pe benzile din imagine); mărimea iconițelor folosește `mMinScale` (**de măsurat** scara implicită) |
| Click pe minimapă, cadrul țintei, tabela de scor, magazinul, ecranul de final, anunțurile | date (`UI.wad`) | **nu există încă** |

### Nivelurile, experiența, aurul (server)

| Piesa | Sursa | Stare |
|---|---|---|
| Statisticile pe nivel: bază + creștere × suma factorilor nivelurilor | date: `hpPerLevel`, `damagePerLevel` ... din `CharacterRecord` și `mPerLevelStatsFactor` din `Global.wad` (`globals`): 0,72 la nivelul 2, +0,035 pe nivel | fidel (e formula documentată 0,65 + 0,035 × nivel) |
| Viteza de atac pe nivel: procent din `attackSpeedRatio` | date + documentat | conform documentației |
| Pragurile de experiență pe nivel (280, 660, 1140 ...) și împărțirea între campionii din apropiere (0,95 singur, 0,58 în doi ...) | date: `ExperienceCurveData`, `ExperienceModData` ale modului CLASSIC | fidel; nivelul maxim 18 e documentat |
| Raza de experiență 1400 | date: `BarracksConfig.ExpRadius` | fidel |
| Experiența și aurul unui minion: corp la corp 65 / 21, cu baghetă 32 / 14, tun și super 100 / 57 + 3 pe creștere (cel mult 90) | documentat (ian. 2024); înregistrările hărții au `expGivenOnDeath` 0 | conform documentației |
| Aurul de start 500, aurul în timp 10,2 la 5 secunde de la 1:50 | date: `ai_StartingGold`, `ai_AmbientGoldAmount`, `ai_AmbientGoldInterval`, `mission_AmbientGoldStartTime` | fidel |
| Regenerarea vieții și a resursei: pe secundă din înregistrare (`baseStaticHPRegen`, `arBaseStaticRegen` + creșterea pe nivel), dată la fiecare jumătate de secundă | date + documentat (pasul de 0,5 s) | fidel |
| Resursa (mana): `arBase`, `arPerLevel`; campionii cu `arBase` 0 nu au | date | fidel |
| Experiența și aurul pentru campioni omorâți, asistările, aurul turnurilor | date parțiale (`mExperienceGrantedForKillPerLevel`, `GameModeConstants` de recompense) | **nu există încă** |

## Abilitățile campionilor (faza 5, 2026-10-02)

Regula: **cifrele vin din datele vrăjii** (`mDataValues`, `mEffectAmount`, `mSpellCalculations`, `cooldownTime`, `mana`,
`castRange`, `mMissileSpec` din `data/characters/<campion>/<campion>.bin`), **comportamentul din documentație** la
data patch-ului 14.1 (LoL Wiki, reviziile paginilor `Template:Data <Campion>/<Abilitate>` dinainte de 20 ianuarie
2024), iar **efectele vizuale** sunt cele ale jocului, numite prin cheile din `ResourceResolver`-ul skin-ului. Unde
datele și documentația spun altceva, câștigă datele și diferența e notată mai jos.

### Motorul de vrăji (server, C++)

| Piesa | Sursa | Stare |
|---|---|---|
| Vraja pe slot (`spellNames` din `CharacterRecord`), rangul, costul, timpul de reîncărcare, timpul de aruncare `0,5 × (1 + delayCastOffsetPercent)`, `flags & 4` = fără timp de aruncare | date + meta | fidel la date; formula timpului de aruncare e **dedusă** |
| Calculele (`GameCalculation`: număr, valoare numită, statistică × coeficient, pe nivel, produs, sumă, calcul în calcul) | date + meta | fidel; calculele fără nume în fișiere se cer prin hash, scris `{dc63b617}` |
| Punctele de abilitate: ultima la nivelurile 6 / 11 / 16, celelalte cel mult jumătate din nivel rotunjit în sus | documentat | conform documentației |
| Țintirea (`mTargetingTypeData`): pe sine, zonă în jurul său, țintă, loc, direcție, con; la țintă și la loc în afara razei campionul merge întâi în rază | date + documentat | fidel la tipuri; mersul în rază e documentat |
| Proiectilele vrăjilor: viteza din `movementComponent` (`mSpeed`, sau `mInitialSpeed` + `mAcceleration` până la `mMinSpeed` / `mMaxSpeed`), raza din `castRange` | date | fidel; se mișcă în linie dreaptă pe sol (înălțimea e doar a efectului) |
| Lățimea proiectilului: `mMissileWidth` e **jumătatea** lățimii | **dedus**: lățimile documentate la Light Binding (140), Razor Shuriken (100) și Enchanted Crystal Arrow (260) sunt dublul celor din fișiere (70, 50, 130) | dedus |
| Efecte de stare (buff-uri): viteză, viteză de atac, AD, armură, rezistență magică, scut, prag minim de viață, șansă de critică, stun, root, silence, disarm, cârlige la atac și la expirare | documentat (regulile fiecărui efect) | motor propriu, în stilul „building blocks” al scripturilor Riot (**alegere proprie** ca formă) |
| Lovitura critică: 175% din atac, la șansa din statistici; zarul e al meciului (determinist) | documentat (175%) | conform documentației |
| A doua aruncare a unei vrăji (`SetRecast` + `OnRecast`): fără cost, fără timp de aruncare, peste timpul de reîncărcare | documentat (Zed W / R, Lux E) | conform documentației |
| Manechinul din Practice Tool contează drept campion pentru vrăji | documentat (așa e în Practice Tool) | conform documentației |

Protocolul are versiunea 13 (mesaje noi: `SpellCast`, `BuffChange`, `SkillMissile` cu accelerație, `Dash`, `Effect`,
`GroundEffect`, `Animation`); înregistrările `.basr` au versiunea 5.

### Scripturile (Lua 5.1, `server/scripts/<Campion>.lua`)

| Campion | Ce face fiecare abilitate (cifrele din date) | Abateri și lucruri de măsurat |
|---|---|---|
| **Garen** | Pasiva: regenerare din `RegenCalc` după `DamageTimer` fără lovituri. Q: scapă de încetiniri, viteză, următorul atac dă `TotalDamage` și tăcere. W: reducere de daune `DRPercent` și scut `TotalShield`. E: `NumberOfStrikes` lovituri în raza 325 pe `Duration`, a doua aruncare oprește. R: `BaseDamage` + `ExecuteDamage` × viața lipsă, daune adevărate | lipsesc stivele pasive ale lui W și spargerea de armură a lui E |
| **Lux** | Pasiva: vrăjile marchează `DebuffDuration` (6 s); atacul și R aprind marca pentru `TotalDamage`. Q: primii doi inamici, `TotalDamageTT` și imobilizare 2 s. W: scut `TotalShieldTT` 2,5 s la plecarea și la întoarcerea baghetei (proiectil care încetinește: 2200 → 500). E: zonă cu raza 310 timp de 5 s care încetinește 25 .. 45%, explodează la a doua aruncare sau la final pentru `TotalDamageTT`. R: după 1 s de stat pe loc, raza lovește tot ce e în linie pentru `TotalDamage` | W nu apără încă aliații. R: lungimea 3400 și lățimea 200 sunt **documentate** (fișierele au `castRange` 3500 pe `LuxRMis` și `mLineWidth` 190 pe `LuxR`, niciuna limpede a razei). Drumul de întoarcere al baghetei e oglinda celui de dus (**dedus**). E: timpul de reîncărcare curge de la prima aruncare (**de măsurat**) |
| **Ashe** | Pasiva: atacurile și vrăjile pun Frost `SlowDuration` (2 s), încetinire `SlowAmount` (20 .. 30% pe nivel); atacul pe o țintă cu Frost dă `DamageBonus` (120%). Q: 4 stive de Focus din atacuri (4 s, apoi scad una pe secundă); 6 s cu viteză de atac 25 .. 55% și atacuri de `DamagePerStrike` × AD; timpul de atac repornește. W: `NumberOfArrowsTooltip` (7 .. 11) săgeți, fiecare se oprește la primul inamic, `TotalDamage` o singură dată pe țintă, încetinire critică `EmpoweredSlowAmount`. R: săgeată pe toată harta (1500 → 2100, accelerație 200), se oprește la primul campion: `RMainDamage`, stun `MinStunDuration` .. `MaxStunDuration`, `RAoEDamage` în `SlowRadius` | W: 4,625° între săgeți e **documentat** (`castConeAngle` 20 din fișiere nu e evantaiul); viteza 1500 e din date (documentația spune 2000). R: stunul maxim după 2800 de unități e **documentat**. E (Hawkshot) zboară, dar nu arată nimic nou: nu există încă ceață de război. Critica lui Ashe (încetinire dublă în loc de daune) nu are încă de unde veni: nu există obiecte |
| **Tryndamere** | Furia (resursă care pornește de la 0): 5 pe atac, 10 pe critică, 10 pe ucidere, scade cu 5 pe secundă după 8 s fără luptă (**documentat**); șansa de critică = furie × calculul `{dc63b617}` (0,4% pe punct). Q: AD pasiv `FlatAD` + `ADPerOnePercentMissingHP` pe procent de viață lipsă; activ: vindecare `BaseHeal` + `HealPerFury` × furie. W: campionii inamici din rază pierd `ADReduction` AD 4 s; cei întorși cu spatele sunt încetiniți cu `SlowPotency`. E: salt de cel mult 660 la viteza 700 (vraja `slash`), `TotalDamage` în raza `DamageAoE` de-a lungul drumului, furie pe fiecare lovit, timpul de reîncărcare scade la fiecare critică. R: 5 s viața nu coboară sub `TryndRMinHealth`, + `TryndRFuryGain` furie | raza lui W e `castRadius` 830 din date (documentația spune 850) |
| **Zed** | Pasiva: atacul pe o țintă sub 50% din viață dă `{6a1a62e9}` (6 .. 10% pe nivel) din viața maximă, o dată la `PerUnitCD` (10 s) pe țintă. Q: shuriken de la Zed și de la fiecare umbră (`ZedQMissile`): `TotalDamage` primului lovit, `PassThroughDamage` celorlalți. W: umbra (`ZedShadow`, personaj din arhiva lui Zed) stă 5,25 s; a doua aruncare schimbă locurile; lovitura comună Zed + umbră dă înapoi energie (al treilea `mEffectAmount`). E: `TotalDamage` în `ZedRadius` / `ShadowRadius`, o singură dată pe țintă; tăietura umbrei încetinește (`MoveSpeedMod`, `MoveSpeedModBonus` la două tăieturi); −`ShadowHitCDR` s la W pentru fiecare campion lovit de Zed. R: apare lângă țintă, lasă o umbră `RCanSwapBuffDuration` (7,5 s), marca explodează după `RDeathMarkDuration` (3 s) pentru `RCalculatedDamage` + `RDamageAmp` × ce a încasat ținta | R: fără cele 0,6 s în care Zed e de neatins (**de măsurat**); marca numără daunele primite efectiv, documentația numără daunele dinaintea armurii (**de măsurat**). Q: o țintă lovită de mai multe shurikene le încasează întregi (**de măsurat**). W nu verifică încă dacă Zed e imobilizat la schimbul de loc |

### Ce arată clientul

| Piesa | Sursa | Stare |
|---|---|---|
| Animația vrăjii (`mAnimationName`), efectele pornite de scripturi pe o unitate / pe un os / într-un loc, proiectilele cu efectul lor | date (cheile skin-ului) | fidel la chei; înălțimea de 100 a proiectilelor deasupra solului e **aleasă** |
| `VfxPrimitiveBeam` (raza lui Lux): o fâșie de la locul efectului la ținta lui, cu `mLocalSpaceSourceOffset` / `mLocalSpaceTargetOffset`, lată cât scara X a particulei | date + meta | **de măsurat**: direcția texturii, `mBirthTilingSize`, `mSegments` |
| Emițătoarele cu distorsiune și `VfxPrimitiveAttachedMesh` | date | **nu sunt desenate încă** (zona E a lui Lux se vede slab din cauza asta) |
| Texturile personajelor: nivelurile mici (mip) sunt generate la încărcare, nu luate din fișier | **dedus**: textura lui `SRU_OrderMinionSiege` are în fișier nivelurile 1 .. 6 aproape albe (media 252 .. 163 față de 46 la nivelul întreg), iar jocul nu arată niciodată minionul alb | dedus |
| Butoanele de nivel, punctele de rang, timpii de reîncărcare și costurile pe iconițe | date (`UI.wad`) | fidel |

Verificat pe fiecare campion cu meciuri scriptate (`shots/minions/run.sh`, serverul cu `--level 6 --start-x X --start-z Z`,
opțiuni doar de test, ca „level up” și „teleport” din Practice Tool) și cu jurnalul de luptă al reluării
(`server.exe --replay … --combat-log 1`): fiecare reluare a ieșit „identical”.

## Scripts.wad din 14.1 (inventar, 2026-10-02)

`DATA/FINAL/Scripts.wad.client` are 29.747 intrări: un manifest cu 18.924 de căi (`DATA/...lua`, intrarea de 1 MB; hash-ul căii =
XXH64 al căii cu litere mici și extensia `.luabin64`), 18.924 de scripturi Lua 5.1 pe 64 de biți și 10.821 de fișiere `PreL`.
Citire: `tools/wadx.py`, listare: `build-tools/luac51_x64.exe -l -l -p`; listările scripturilor de AI și de nivel sunt în `research/lua141/`.

- **Vrăji și buff-uri** (`Characters/<Campion>/Spells/*.lua`, 11.882 de scripturi): doar steaguri și chei de efect (`BuffName`,
  `AutoBuffActivateEffect[N]` + `AutoBuffActivateAttachBoneName[N]`, `SpellFXOverrideSkins`, `PersistsThroughDeath`...). Doar 5 trec de 1000 de
  octeți. **Logica abilităților nu e în pachet** (rulează în serverul Riot). Efectele buff-urilor cu os de atașare SUNT date.
- **Logică reală Riot**: `DATA/Scripts/{Minion,Turret,Hero,Aggro,Leashed,Idle,Pet,RiverCrab,BaronMinionAI,...}.lua` (starea AI-ului; căutarea
  țintei e funcție de motor), `DATA/Shared/Scripts/SR_LevelScript.lua` (valori: prima undă la 65 s, upgrade 90 s, rază XP 1400 / aur 1250,
  aur minioni 21/14/57, +25 viteză la 600 s apoi la 300 s, tun la 850/1500 s...), `SR_NeutralMinionSpawn.lua` (junglă: tipuri de tabere,
  `START_OF_GAME_MONSTER_SPAWN_DELAY` 22, dragon/herald/baron la 300/360/360 s), `Mutators/PracticeTool.lua`.

## Inventarul complet al pachetului 14.1 (2026-10-02)

Toate cele 365 de wad-uri, fiecare fișier după semnătura lui: ~400.000 de texturi DDS, 40.660 `.scb`, 38.602 `.anm`, 32.100 binuri,
18.996 scripturi Lua, 15.272 `.tex`, 8.303 schelete + mesh-uri, 5.412 bănci de sunet Wwise, ~700 `.inibin`/`.troybin` vechi (DATA.wad),
fișiere de comportament ale boților (`DATA/Characters/<C>/Scripts/<C>Bot.dat`, DATA2.wad), bytecode de shader DX9/DX11.
Recensământul claselor din toate binurile (509 clase, 274.496 de intrări) e în `research/m141/class_census_141.txt`.
Nume pentru câmpuri și clase: `research/hashes/` (din baza meta `research/meta/db.json`); `bainfo bin <wad> "{hash}" "" research/hashes`.

Date de gameplay găsite și încă nefolosite (lista de lucru):
- **Iteme**: binul de 4,9 MB din Global.wad (`{1d720f4f42640c18}`): 501 `ItemData`, 424 `SpellObject` ale itemelor, 224 `ItemGroup`;
  `GameModeItemList` + `ItemShopGameModeData` (map11.bin); magazinul: `ItemShopViewController`, `HudItemShopData` (UI.wad).
- **Rune**: 99 `Perk` + `PerkStyle`/`PerkSlot` (Global.wad).
- **Reguli**: `GameplayConfig` (crit, lethality, minion death delay, blocaje ale atacului, haste maxim), `CcBehaviorsConfig`,
  `BuffStackingSettings`, `DamageSourceSettings`, `GlobalPerLevelStatsFactor`, `CharacterStealthData`, `SurrenderData`.
- **Camera**: `CameraConfig` (4 intrări în binul global: zoom 1000..2250 / 2600 / 3000, accelerații, trapezele de clamp) — zoom-ul aplicat.
- **Interfață**: `TargetFrameViewController`, `ScoreboardViewController`, `EndOfGameViewController`, `DeathRecapViewController`,
  `AnnouncementsViewController` + 74 `AnnouncementDefinition`, `KillCalloutsViewController`, `FloatTextFormattingData` (numerele de damage),
  `HudFeedbackDamageData`, `MouseOverEffectData` (conturul la hover), `CursorConfig`, `MinimapPingData`, `NeutralTimerViewController`.
- **Hartă**: `FogOfWarProperties`, `ScriptCheat` (comenzile Practice Tool), legăturile modului CLASSIC din `GameModeMapData`.

## Orientarea clădirilor și caseta camerei (2026-10-02)

- Fiecare obiect al hărții apare în `base_srx.materials.bin` în două containere, cu aceeași poziție dar alte rotații: `{2ad5bf8e}`
  (containerul la care trimit `RequiredLocations` / scriptul de spawn) și `{c6babea2}` (chunk al `MapContainer`-ului hărții 14.1).
  Rotația se ia din chunk: turnurile privesc spre benzi (roșu top exterior −115°, albastru top exterior 5°). **Confirmat de utilizator**
  pe randări comparative (variantele A/B din primul container și C/D din chunk; C ales). `objectcfg.cfg` `Rot=` e un sistem vechi, nefolosit.
- Caseta camerei pe minimap: dreptunghi alb aliniat cu harta, = cutia care încadrează cele 4 colțuri ale ecranului proiectate pe sol.
  **Măsurat** pe un replay 14.1 (raport înălțime/lățime 0,548; cutia dă 0,545, trapezul mediu 0,678). Grosimea liniei: de măsurat.
- Skin-urile turnurilor: cele din `map11.bin` (32 Order / 35 Chaos), confirmate de utilizator. Atenție: replay-urile pot avea skin-uri de eveniment.
- Calitatea mediului: implicit **Low** (setarea utilizatorului în LoL): fiecare shader al hărții primește `LOW_QUALITY_MODE=1` (cele care nu-l
  declară îl ignoră). În 14.1, variantele low ale `vertexdeform` (0–11 din 28) nu citesc `TIME` și n-au `sincos`: tufișurile stau nemișcate.
  `client.exe --env-quality high` = variantele normale. Ce trepte din meniul jocului pornesc `LOW_QUALITY_MODE`: de măsurat.
  FPS măsurat pe UHD 620 în mijlocul hărții: ~25 și pe Low și pe High (low schimbă doar tufișurile; costul e în altă parte).

## Itemele și magazinul (2026-10-02)

- **Date**: `common/ItemData` citește binul de iteme din Global.wad (501 `ItemData`, 224 `ItemGroup`); lista modului = `itemLists` ale
  `GameModeMapData` CLASSIC (273 de iteme). `price` = costul de combinare (total = price + componentele; IE 525 + 1300 + 875 + 600 = 3300).
  Textele: `common/StringTable` (RST v5, 39 de biți de hash) din `Localized/Global.en_US.wad.client` `data/menu/main_en_us.stringtable`.
- **Server**: cumpărare (componentele deținute se consumă, limitele `mMaxGroupOwnable` — o pereche de cizme, un singur tip de poțiune —,
  stivele `maxStack`, slotul trinket-ului din grupa lui), vânzare (`sellBackModifier`, implicit 0,7), doar lângă fântână sau mort
  (wiki „Shop” 2023-11; distanța = `sp_RegenRadius` 1100 [de măsurat]). Statisticile itemelor (HP, AD, AP, armură, MR, AS%, crit, MS
  plat și %, mană, ability haste) intră în `refresh_stats`; haste scurtează cooldown-urile (100/(100+AH), documentat); AP intră în calculele
  vrăjilor. Pasivele și activele itemelor: **încă nu** (sunt cod de server la Riot). Undo: încă nu.
- **Client**: inventarul din HUD (iconițe, stive, taste), magazinul pe tasta P din scena 14.1 `clientstates/gameplay/ux/itemshop/uibase`:
  grupele pe raritate, cartea de item clonată din `AllItemsIconDefinition` în celulele 57×76 ale panoului (597×538), titlurile și butoanele
  traduse (`TRAKey`), derulare cu rotița. Click stânga = selectează, dreapta = cumpără; dreapta pe inventar = vinde. Așezarea exactă a
  rândurilor e dedusă din geometria șablonului (codul de layout al jocului nu e în date).
- Verificat: `server --start-gold G` + `client --moves "b:t,id;x:t,slot"`; reluările ies identice.

## Verificări vizuale (2026-10-03)

| Piesa | Sursa | Stare |
|---|---|---|
| Liniuțele barelor de viață | date: `TickStyle` al fiecărui stil din `gameplay.lolfloatinginfobars.bin` (campioni: `HealthBarTickStyleHero`, liniuță mare la `HealthPerstandardTick` 1000, liniuțe mici după `MicroTickPerStandardTickData`, 9 sub 3000 HP [meta]); unități: `HealthBarTickStyleUnit` spațiat de `hpPerTick` din `healthBarData` al skin-ului [meta default 0 = fără liniuțe: minionii și turetele nu au] | fidel; liniuțele fără textură (ale campionilor) desenate negre, ca o tăietură în bară (**dedus**) |
| Plăcile turetelor exterioare | LoL Wiki, Turret (revizia 2024-01-13): 5 plăci de 1000, segmente ale vieții, până la 14:00 | bara arată 5 segmente până la 14:00; aurul și rezistența plăcilor nu sunt încă pe server |
| Ce efecte ale hărții se desenează | frustumul camerei cu sfera `visibilityRadius` a fiecărui sistem (toate rulează mereu) | înainte: un cerc în jurul țintei camerei, care făcea nuferii și alte efecte să apară/dispară la margine |
| Modelele hărții cu controler de vizibilitate | mapgeo v15+: `VisibilityControllerPathHash` pe fiecare model (citit greșit ca „bucket grid hash”); evaluat ca la efecte | 40 de modele ascunse (variantele gropii Baronului, terenurile elementale): clipirea mov de la Baron venea din ele, suprapuse pe sol (măsurat: salt maxim între cadre 8659 → 144 pixeli mov, `shots/baron/flicker.sh`) |
| Plasele (mesh) de particule culcate pe sol | geometria lor (înălțime ≤ 1% din lățime) | desenate cu decalurile solului (același depth bias, **alegere proprie**) |
