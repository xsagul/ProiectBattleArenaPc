# Ecranul de încărcare și ce se încarcă în spatele lui

## Ce face clientul League (dovezi)

**Ordinea reală, din jurnalul clientului Riot.** Clientul 4.20 de pe Desktop (`Desktop\4.20\Client\...\Logs\Game - R3d Logs\
2026-10-02T02-30-23_r3dlog.txt`, rulat pe 2026-10-02) își scrie singur pașii (rezumat în `research/lcu141/r3dlog420_load.txt`):

| t (s) | pas din jurnal | ce înseamnă |
|---|---|---|
| 0,7–4,2 | `Started System Init`, `Maestro Init`, `InitRenderer`, `SetMode 1280x960` | pornirea, legătura cu clientul din afara jocului (Maestro), fereastra |
| 2,8–4,6 | `Waiting until connection...`, `Hard Connect`, `Received client ID`, `Waiting for server response` | **se conectează la serverul de meci înainte să încarce** |
| 4,7 | `Initializing GameModeComponents for mode=CLASSIC`, mutatorii `LoadingScreenBackground`, `Clouds`, `FOWTexture`, `HudSkin`, `NavigationMesh`, `MiniMapTexture`, `MapMusic` | modul de joc, din care vine și fundalul ecranului de încărcare |
| 5,2–6,3 | `PlayGame Entered`, `gRenderPipeline`, `CreateParticleSystemManager`, `CreateAudioManager` (Wwise) | motorul |
| 6,3–9,7 | texturile hărții (nexus, inhibitor, iarbă), apoi buff-urile turnurilor (`TurretShield`, `TurretBonus`, ...), apoi monștrii (`Lizard`, `Dragon`, `AncientGolem`, `Worm` = Baron) | **nivelul și obiectele lui** |
| 9,7–10,0 | `Begin/End Game Object Update` | |
| 10,0–11,6 | turnurile fântânii, apoi **toate itemele** (`DATA/Items/1054.lua` ... `3418.lua`, enchantments) | magazinul |
| 11,6–14,5 | (fără erori în jurnal) | campionii meciului și vrăjile lor |
| 14,6–14,8 | `PreloadGlobalEffects` | efectele globale |
| 14,8–17,6 | (interfața) | HUD |
| 17,6 | `Start Main Loop`, `Waiting for all players to connect` | gata: așteaptă ceilalți jucători |
| 18,3–19,0 | `Spawning heroes/minions`, `Creating Hero...`, `Spawning champion (Ezreal) ... (is HUMAN PLAYER)` | serverul pune jucătorii în meci |
| 22,3 | `GAMESTATE_GAMELOOP Begin` | meciul |

Valorile de timp sunt din 2014 (clientul 4.20); ordinea și arhitectura sunt ce folosim, nu cifrele.

**Ecranul însuși, în 14.1** (UI.wad.client, `research/m141/loading/`):
- `loadingscreen.bin`: starea de client „LoadingScreen”; pentru CLASSIC / PRACTICETOOL / ARAM ... încarcă trei
  view controllere: `LoadingScreenClassic`, `PlayerCards/PlayerCardsClassic`, `PlayerCardSwitcher`.
- `loadingscreen.loadingscreenclassic.bin` (LoadingScreenClassicViewController): fundalul (al modului), bara de progres și
  textul ei, latența (5 praguri: 0 verde, 150 galben, 250 portocaliu, 350 roșu, 10000 gri, fiecare cu iconiță și culoare
  de text), sfaturile, textul versiunii. Scena: `clientstates/loadingscreen/ux/loadingscreenclassic/uibase` (spinner-ul:
  flipbook de 32 de cadre, 30 pe secundă).
- `loadingscreen.playercardsclassic.bin`: șablonul cardului (scena principală, trei fețe: LSPC0 joc / LSPC1 maestrie /
  LSPC2 jucător), splash-ul, numele campionului și al jucătorului, iconița, vrăjile de summoner, runele, ramele pe
  rang (Unranked = ramă implicită), cele două regiuni (sus Order, jos Chaos).
- map11.bin, GameModeMapData CLASSIC: `LoadingScreenBackground: ASSETS/UX/LoadingScreen/SRBackground.tex`;
  `LoadScreenTipConfiguration` (mShowPBITipsOnLoadingScreen 1, 60 s).
- skin0.bin al campionului: `loadscreen: CensoredImage image` (de ex. `GarenLoadScreen.dds`).
- textele: „@MS@ ms” (latența), „@NUMBER@%” (progresul), `game_character_displayname_<Campion>`.

## Ce face clientul nostru (client.exe)

1. Fereastra, apoi **imediat** ecranul de încărcare (`client/src/LoadingScreen.{h,cpp}`, desenat din datele de mai sus).
2. **Se conectează la server înainte să încarce** (ca League), dar intră în meci abia la final: `Connection::connect(...,
   hold)`, `ready()`. Cât timp încarcă, legătura e ținută vie de un fir al ei (`Connection::pump`), ca latența afișată
   să fie a rețelei, nu a pauzelor dintre pașii de încărcare.
3. Etapele, în ordinea jurnalului Riot (`--load-log fișier` scrie cât a durat fiecare):

| etapă | ce încarcă | durată pe PC-ul țintă (UHD 620) | cotă din bară |
|---|---|---|---|
| nivelul | geometria, materialele, shaderele Riot, texturile, grila de navigare | ~15 s | 0–83 % (avansează pe materiale și modele) |
| efectele nivelului | sistemele de particule ale hărții și locurile lor | ~0,5 s | 83–86 % |
| obiectele nivelului | turnurile, inhibitorii, nexusurile, minionii ambelor echipe, manechinul din Practice Tool (MapGame din datele hărții) | ~1,4 s | 86–94 % |
| itemele și interfața | itemele, textele, scenele HUD-ului, minimapa | ~0,6 s | 94–97 % |
| campionii | modelul, animațiile, vrăjile, efectele și iconițele campionului | ~0,3 s | 97–98 % |
| efectele globale | Global.wad, FXAA | ~0,4 s | 98–100 % |

   Cotele barei nu sunt în niciun fișier: sunt timpii măsurați pe PC-ul țintă (**de măsurat** la League: cum își
   calculează procentul). Câștig secundar: personajele hărții nu se mai citesc de pe disc în mijlocul meciului.
4. La 100 %: trimite `Hello` (= „gata”), ecranul rămâne până când serverul îl pune în meci (`Welcome`), apoi jocul.

**Ce nu e încă:** sfaturile (care set și când; textele sunt citatele „narrative”), fețele 2 și 3 ale cardului (comutatorul
PlayerCardSwitcher), vrăjile de summoner și runele pe card (jocul nu le are încă), cardurile celorlalți jucători și
progresul lor (vin odată cu meciurile cu mai mulți jucători: League trimite procentele prin server), iconița de profil
(implicit 29, iconița unui cont nou). Așezarea cardurilor una lângă alta, centrate în regiune, e dedusă (**de măsurat**).
