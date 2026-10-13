# Serverul de joc — ce merge, ce nu (stare la 2026-10-11, 05:30)

Scop: un meci co-op vs AI jucabil cap-coadă pe clientul 13.3, cu serverul nostru (`server/lnp_server.py` = campionul
jucătorului, `server/world.py` = restul lumii). Forma pachetelor se ia din replay-ul 13.3; regulile simple sunt ale
noastre, valorile din datele jocului și din replay. LeagueSandbox (`tools/third_party`) a fost citit doar ca model de
logică; codul este scris de noi.

## Cauzele găsite pe 2026-10-11 (toate confirmate în client)

1. **Starea completă a unei unități noi.** Serverul real trimite la crearea unui minion TOATE cele 58 de valori
   replicate (ce are voie să facă: `ActionState 0x200000f`; „poate fi țintit” 1 / steaguri de echipă 4; viață), iar la
   0,132 s statisticile (daune, rază, viteză 325). Noi trimiteam doar viața: clientul avea o unitate care nu are voie să
   meargă și care nu poate fi țintită. `world.minion_values()` scrie acum ambele blocuri, identice cu ale replay-ului.
2. **Turnurile nu sunt țintibile în starea de început.** Serverul real le deschide la 10,094 s (cele exterioare: steaguri
   4; restul 2, apoi 4 când cade turnul din față).
3. **Antetul pachetului de mișcare (552) spune câte unități mută.** Clientul muta doar atâtea unități câte spunea
   antetul împrumutat din replay. Antetul se construiește acum din părți (`sync552.next_head(…, count)`).
4. **Proiectilul unui atac are id-ul lui de rețea** (05:00, măsurat cu „recensământul” de mai jos). În pachetul de atac
   al unui minion (286) puneam ca id al proiectilului chiar id-ul minionului. La minionii de distanță (casteri, tunuri)
   clientul face din proiectil un obiect cu acel id — și minionul nu mai era „el” în tabela clientului de la primul lui
   atac: rămânea pe loc pentru totdeauna, nu mai primea nici drum, nici viață, nici moarte. Asta erau **„minionii blocați
   pe mijlocul culoarului, cei din spate nu continuă”** și **„apăs pe un minion de distanță: arată săbiuța, dar nu îl
   atacă / nu îi scade viața”** (pe server acel minion era deja mort sau în altă parte). Serverul Riot dă fiecărui
   atacator un id separat pentru proiectil, același la toate atacurile lui; la fel face acum `World.attack_net`.
   Măsurat: înainte, TOȚI minionii de distanță dispăreau din tabela clientului la 20–35 s de la apariție, deși trăiau pe
   server (`match_census1`); după, 0 din 96 de unități moarte pe server au mai rămas vii în client, casterii uciși de erou
   pierd viață, mor și dispar (`match_census2`).

## Abilități — ce s-a schimbat pe 2026-10-11 (văzut în client cu Caitlyn și Ashe)

Campionii din replay (Darius, Jax, Lee Sin, Azir, Jhin, Blitzcrank, Nidalee, Alistar, Talon, Kalista) folosesc lansările
reale extrase din replay. Toți ceilalți (≈150) trec prin lansarea generică, unde erau trei greșeli:

1. **Pozițiile din pachetul de lansare (49).** Scriam ținta și în locul „unde stă eroul”, iar poziția eroului o luam
   din cererea clientului, unde la abilitățile țintite e de fapt punctul țintit: plecare = sosire, direcție zero. Acum,
   ca în replay: eroul la poziția lui de pe server, ținta = erou + direcție × raza abilității (proiectile în linie),
   locul țintit (abilități pe sol), poziția unității (abilități pe țintă, cu unitatea numită în pachet); înălțimile sunt
   ale terenului (`navgrid.height`: culoar 53,7, râu −70, fântână 183,6 — exact valorile din replay).
2. **Plecarea proiectilului (779).** Când se termină timpul de lansare, serverul real trimite 779 cu id-ul lansării
   (88 din 88 la Q-ul lui Lee Sin, 145 din 146 la Q-ul lui Nidalee). Noi nu îl trimiteam la abilități, deci proiectilul
   nu pleca niciodată. Regula din date: abilitatea are propriul proiectil (`mMissileSpec`) → 779. **76 de abilități**
   (Caitlyn Q, Ezreal Q/W/R, Morgana Q, Ashe E/R, Lux E, Jinx R …).
3. **Proiectilul e o abilitate separată** (RocketGrab → RocketGrabMissile, Volley → VolleyAttack; ≈220 de abilități).
   Serverul real îl creează cu un pachet pe care încă nu îl putem scrie (117). În locul lui, abilitatea-proiectil este
   lansată ca una care își are propriul proiectil (259 + 49 dintr-un slot în plus + 779) — soluție a noastră, care se
   vede corect în client: plasa lui Caitlyn (E), glonțul de la R care zboară până la țintă, cele 7 săgeți ale lui Ashe
   (W, în evantai). Care abilitate e „proiectilul” când sunt mai multe cu nume asemănător e o alegere a noastră
   (`spell_engine.missile_spell`); la unele poate ieși cea greșită.
4. Abilitățile pe țintă lovesc unitatea pe care a dat clientul click (înainte: cea mai apropiată de punctul țintit).
   Unghiul conurilor se citește corect (în date e jumătatea unghiului: Annie W 24,76 → 49,52°).

**Ce NU fac încă abilitățile** (nu există script de abilitate în client; fiecare mecanică trebuie scrisă sau dedusă):
salturi / dash-uri, efecte de control (stun, slow, root), buff-uri și stive (doar Garen are câteva), abilități în mai
multe părți (a doua apăsare), efecte fără proiectil care nu vin din animație, costul de mană și pasivele. Daunele vin din
formulele din date (aproximare: care formulă e „dauna” și tipul ei). Boții nu folosesc abilități.

## Confirmat în client (capturi în `data/exe133/match_world1 … world4`, `match_census2`, `match_spells1`, `match_spells2`)

- Minionii pleacă din bază pe rând, în coloană, se luptă pe culoar; cei de distanță trag, pierd viață, mor și dispar.
- Clientul trimite ordine de atac pe minionii, monștrii și turnurile noastre; uciderea unui minion dă aur și experiență.
- Turnul trage (raza de la vârf până la țintă, număr de daune), viața eroului scade în HUD.
- Jungla: taberele apar la 1:28–1:41 (crabii la 3:29, dragonul la 4:53, heraldul la 7:57), pot fi atacate,
  lovesc înapoi; eroul omorât de Red Buff → ecran gri „executed” → înapoi la fântână.
- Boții: cei 9 campioni pleacă pe culoare, stau în spatele valului, atacă minioni și campioni.
- Experiență → nivel 2, 3 (portret, statistici, punct de abilitate); cumpărarea unui obiect.
- Proiectilele abilităților: Caitlyn Q / E / R, Ashe W / E / R (săgețile, șoimul, săgeata de cristal).
- Sfârșitul meciului: după ce cad turnurile de nexus și nexusul → ecranul VICTORY, clientul se închide singur.

## Făcut și verificat doar offline (`tools/check_world.py`: toate pachetele citite înapoi prin cititorul clientului)

- Căderea unui turn (310 + animația „Destroyed”), deschiderea turnului următor; aur 250 pentru erou.
- Moartea și întoarcerea boților (780 / 417 / 440 / 568, 128), retragerea la fântână sub 30 % viață.
- Întoarcerea taberelor din junglă după 135 s (300 s buff-urile) cu id-uri noi.
- Minionii atacă turnurile și, la capătul culoarului, nexusul; minionii fără alt inamic atacă un campion foarte aproape.

## Nefăcut

1. Mecanicile proprii ale abilităților (vezi mai sus) și pachetul 117 (crearea reală a proiectilelor).
2. Super-minionii, turnul din fântână; boții nu folosesc abilități, nu cumpără, nu cresc în nivel.
3. Când câștigă echipa roșie: pachetele de final poartă echipa corectă (137 / 766), dar ecranul DEFEAT nu a fost văzut.
4. Runele dinaintea meciului, răsplata de la dragon / herald / buff-uri.
5. Regulile boților sunt simple (fără „last hit”, fără combo-uri); daunele turnului pe minioni sunt procente fixe.
6. Clientul ține minionii care merg cu ≈0,5–1,5 s în urma poziției de pe server (măsurat cu recensământul); nu s-a
   căutat încă de ce.

## Cum se verifică

- Fără client: `python tools/check_world.py 300` — rulează lumea 300 s și citește fiecare pachet înapoi prin cititorul
  clientului. Orice pachet refuzat apare aici, nu într-un client închis.
- Cu client: `bash tools/run_match.sh <secunde> <nume> python server/lnp_server.py --replay-574 --slot 1 --own-574
  --set574 "1.champion=Ashe;1.champion_id=22;1.skin=0;1.name=X" --hero 4000001e --own-79 --set79
  "1.champion=Ashe;1.skin=0" --start-only --stream data/rofl/KR-6363178603_13.3.rofl` (comanda launcherului).
  Ajutoare de test: `--teleport "88:7050,6950"`, `--auto-attack "99:4000101d"`, `--auto-cast "96:1:7750,7750"` (slotul
  1 = W lansat spre acel loc, fără apăsări), `--world-do "20:xp=300;40:raze"`, `--shots-game "96.4,96.6"` (cadre).
- **Recensământul** (ce crede clientul despre fiecare unitate, față de server — sfârșitul ghicitului):
  `python tools/probe.py "29d4f0:900=census 40001000-400013ff,4000001e-4000001e 500 0:4,218:10,224:c,e7c:4"` scrie
  sonda (DLL-ul nostru din client notează de două ori pe secundă, pentru fiecare id, steagul „mort”, poziția și viața
  din obiectul clientului → `game/ba_census.log`); serverul pornit cu `WORLD_STATE_LOG=<fișier>` își scrie starea;
  `python tools/census.py data/exe133/match_<nume>` le compară. După test: `python tools/probe.py` (fără sonde).
