# Serverul 16.20 — arhitectura dedusă din meciul live

Sursa: meciul custom 5v5 jucat live pe 2026-10-11 (`data/live/4013831789`, Garen + 9 boți, 2146 s, până la nexus).
Este fluxul exact pe care serverul Riot l-a trimis unui jucător, cu cererile clientului care l-au provocat
(433.118 pachete server→client, 244 de tipuri; 60.239 client→server, 29 de tipuri). Replay-ul (.rofl) e alt dialect
(spectator): 62 de tipuri din replay nu ajung niciodată la un jucător, 37 există doar live.

Unelte: `tools/live_digest16.py` (fiecare tip citit de cititorul clientului → `digest.txt`), `tools/live_life16.py`
(tot ce se spune despre o unitate, în ordine, decodat), `tools/live_pairs.py` (cerere → răspuns),
`tools/live_check16.py` (formatele învățate pe pachetele live), `server/codec16.py` (citire/scriere pe câmpuri).

## 1. Conexiunea și cele trei părți

| când (cerere client) | răspuns server | ce e |
|---|---|---|
| handshake 500 B | accept 100 B | transport (Blowfish + CRC, `lnp16.py`, `net16.py`) |
| 1 + 64 | 213, 804 + 371 (×2), 618 | ceas + **game info** (lista jucătorilor: campion, nume, poziție, echipă, mod, hartă) |
| 197 (progres încărcare) | 1095 | bara de încărcare a fiecărui jucător |
| al doilea 64 | **starea de start**: 4.784 pachete într-o rafală | tot ce există la secunda 0 |
| al treilea 64 | 664 744 278, apoi „prima stare a lumii” (~965 pachete în 1 s), apoi meciul | |
| 841 la 2 s (canal 4) | 1007 | ping: {nr, timp client} → {nr, timp server la primire, timp client, timp server la trimitere} |

### Starea de start (partea 1), în ordine
1. 1095 278 1086 (Game Start) 804/371 ×4 1169 1187 522 1051 1002
2. **per campion** (10×): 222 creare (net id, loc, campion, jucător) · 905 (rune: arborii 8000–8400) · 227 · 832 ×376
   (același set de 376 de hash-uri la toți; un octet diferă per campion — tabelul magazinului) · 290 · 444 (1260 B,
   același per echipă) · 810 ×4 (nivelul celor 4 vrăji) · 8 · 605
3. 263 ×5, 86, apoi **clădirile**: 502 + 381/333 + 1170 (58 de unități: turnuri, inhibitoare, nexus, …)
4. 826, 1200 ×24 + 41 ×24 (taberele din junglă), 755 ×32, 824/674 ×18, 239/684 (intră în vizibilitate),
   769/1224/1078/788/794/861 (×8), 998/1201/279 ×49, 904/710/557/382/683/294, 325 ×75, 663, 995 ×120, 731 ×8, 984 …

## 2. Tipuri de unități (după pachetul care le numește prima dată)

| naștere | câte | ce sunt | secvență tipică |
|---|---|---|---|
| 905 | 10 | campioni | 905 227 832… |
| 502 | 58 | clădiri (turnuri, inhibitoare, nexus) | 502 381/333 1170 239 684 |
| 1200 | 24 | junglă (tabere/monștri) | 1200 769 998 1201 279 |
| 239 (+684) | 4.865 | **minioni** (și orice unitate care intră în vizibilitate) | 239 684 294 294 1112 1090 |
| 743 (+118) | 4.965 | proiectile de atac (creare / distrugere) | 743 118 |
| 223 | 2.032 | proiectile de vrăji (cu loc de start / țintă) | 223 743 118 |
| 680 | 30 | warduri | 680 947 1112 1090 |
| 568, 802, 1088, 754, 236, 769, 998 | puține | efecte / obiecte de hartă (de clasificat) | |

**239 este un container**: o listă de lungimi + un blob cu alte pachete întregi înăuntru. Un minion nou =
239{439 spawn} + 684 (viață, viață maximă, drumul de ieșire din baracă) + 287 (toate valorile replicate) + 294,
primul drum (61) la ~4,2 s. Înăuntrul lui 239 apar în meci: 439, 626, 16, 894, 584, 794, 881, 1149, 515, 88, 1224, …

## 3. Cerere → răspuns (client → server)

| client | ce e | serverul răspunde |
|---|---|---|
| 1032 | ordin (mișcare / atac: loc, țintă, fel) | 61 drum (canal 2), atacul (906/972…) |
| 707 | cast vrajă | 1215 cast, 635 cooldown, 10 |
| 544 | level-up vrajă | 810 |
| 1135 | cumpără item | 1122 + 63 |
| 745 / 1249 | vinde / undo item | 1237 + 1122 (+ 63) |
| 1084 | ? (la 10 s) | 665 |
| 448 | ? | 164 |
| 921 | ? | 340 |
| 167 | recall | 331 (RecallChannelingUpdate) |
| 807 (20/s), 1042 (10/s) | rapoarte constante ale clientului (cameră / input) | nimic |

## 4. Fluxul de meci (partea 2): sistemele serverului

| sistem | pachete server (măsurate) |
|---|---|
| ceas / ping | 804 371 / 1007 |
| mișcare | 61 (grupuri de intrări waypoint, canal 2) |
| replicare | 287 (valori pe nume, canal 2; clase AIHero, AIMinionCommon, AITurretCommon, …) |
| vizibilitate (ceață) | 239+684 intră, 1090 iese/șters, 658 |
| minioni | 239{439} 684 287 294 61; luptă 390 515 938 150; moarte 1112 1090; aur 818 |
| turnuri | 390/938 (atac), 515, proiectile 743/118 |
| campioni: atac | 906 972 515 447 |
| vrăji | 1215 (cast) 635 (cooldown) 78 (vrajă în slot) 223 (proiectil) 10 |
| buff-uri | 435 (adaugă) 430 (număr) 262 (scoate) |
| iteme | 63 (cumpărat) 1122 1237 |
| aur / XP / nivel | 818 (aur pe kill), 287 (mGold, XP), 810 (nivel vrajă) |
| moarte / respawn | 1112 (moarte) 1090 … |
| anunțuri | 210 (game_announcement_…), 984 (SOG_…, RUNETIMER_…) |
| sfârșit | 384 853 62 258 (la 2138 s) |

## 5. Serverul nostru: `server/main16.py` + `server/core/`

Rescris pe 2026-10-11 ca simulare generală din datele jocului (orice campion din cei 174), cu pachetele în formele
măsurate pe meciul live. Primul server (`match16.py`, `bots16.py`, `spells16.py`, `shop16.py`) e în `server/attic16/`.

```
python server/main16.py --champion Ahri --bots random --seed 7 [--skin 1] [--summoners SummonerFlash,SummonerDot] 5119
python server/main16.py --sim 1500 --quiet            # meciul singur, fără client: rezumat (2,5 ms pe cadru)
python tools/run_match16.py 120 nume python -u server/main16.py ... --shots "90,96" --shots-dir data/exe1620/match_nume
"Joaca 16.20.cmd"                                     # pagina de lobby -> champion select -> joc
```

### Module
| modul | ce face | de unde vine regula |
|---|---|---|
| `gamedata.py` | harta (lane-uri, barăci + valuri, 32 structuri, 18 tabere, tabele XP / moarte), unități, campioni, 131 de obiecte plasate cu net id-ul lor, hash-ul de pachet | bin-urile jocului (Map11.wad, Champions/*.wad, Global.wad) |
| `packets.py` | singurul loc unde se fac octeți; fiecare pachet = o funcție cu nume | forme decodate din înregistrarea live (`forms16.json`, `recipes16.json`) |
| `game.py` | cadrul de 30 Hz, daune, moarte, recompense, structuri, sfârșit | ordinea și momentele măsurate live |
| `units.py`, `heroes.py` | statistici din record + nivel + modificatori, drumuri, atacul de bază, aur / XP / scor / valoare | CharacterRecord, DeathTimes, seriile 437 / 1168 / 189 |
| `ai.py` | minioni de lane, turnuri, monștri | BarracksConfig, acquisition ranges |
| `vision.py` | ceața de război pentru ambele echipe + ce pachete pleacă despre unități nevăzute | măsurat pe toate pachetele live |
| `spells.py`, `summoners.py` | orice vrajă Q/W/E/R din SpellDataResource + BotData; vrăji de invocator; recall | datele jocului; valori wiki pentru invocator |
| `effects.py` | efectele vizuale ale scripturilor (pachetul 10 / 584) | resourceMap-ul fiecărui skin + ce a făcut serverul real |
| `shop.py`, `jungle.py`, `bots.py` | iteme, tabere, creierul boților | bin-ul de iteme, forma live a taberelor, recomandările din datele campionilor |
| `session.py`, `c2s.py` | pornirea în trei părți cu lista noastră de jucători, cererile clientului, ceasul, heartbeat | conexiunea live |

### Cadrul (33 ms), în ordinea pachetelor reale
1. ce era programat pentru acest moment (proiectile care ajung, unități scoase, reveniri)
2. scriptul hărții: valuri (BarracksConfig), tabere
3. cine vede pe cine (`vision.look`): intrări / ieșiri din vedere
4. campioni (ordine, atac, regenerare, aur), boți
5. minioni, monștri, turnuri
6. vrăji în zbor, zone, buff-uri, efecte care expiră
7. toată lumea merge
8. pachetele cadrului: intrări/ieșiri din vedere, 61 (drumuri), evenimentele în ordinea lor, 287 (valori schimbate),
   ștergerile — fără ce nu are voie jucătorul să știe

### Reguli generale deduse (toate cu sursa în comentariile din cod)
- **Ceața de război** (măsurat: fiecare pachet despre un campion / monstru / minion inamic, în vedere sau nu):
  intră = 239 (container: prima dată spawn-ul 439 / nivelul 16 / pachetele campionului) + 684 + valorile replicate
  (toate prima dată, apoi doar ce s-a schimbat); iese = 658. Nevăzut NU se trimite: mișcare, atacuri, cast, daune,
  buff nou, cooldown, level-up, cumpărături, moartea unui minion. Se trimite oricum: crearea și moartea monștrilor,
  moartea (166 + 421) și revenirea (158) campionilor, nivelul vrăjilor (810), 78, sfârșitul unui buff anunțat (262).
  Doar jucătorului: 818, 1050, 1122; XP (1024) doar echipei lui. Vederea: raza din record (1350 / 1200), ziduri =
  celulele blocate fără flag-ul „see through", tufiș = flag-ul de iarbă (39 de petice). Boții, minionii și turnurile
  țintesc doar ce vede echipa lor.
- **Blob-ul 684 al unui campion**: lista sloturilor de iteme schimbate de când a fost văzut ultima dată (33 de
  octeți pe slot), unitatea / locul la care se uită, contoare de buff-uri, mișcarea.
- **Heartbeat**: la 10 s clientul trimite 1084 pe canalele 2 și 1 cu un contor; răspunsul e 665 pe același canal
  (octetul de antet ^ 0xc0; 426 din 426 perechi). Fără el clientul ignoră sfârșitul meciului.
- **Sfârșitul meciului**: rețeta nexusului, +3,5 s 365 {echipa care a pierdut, 2.0}, +3,74 s 673; clientul arată
  emblema VICTORY / DEFEAT și se închide singur.
- **Inhibitor**: 693 (jos / sus), 716, 984 (grupurile de particule ale hărții `SOG_<ECHIPĂ>_<LANE>` și
  `RUNETIMER_...`), 502 + 1170 (efectul „ruină" plasat de hartă, cu net id-ul lui), revenire la 300 s (984 ×3, 693,
  543). **Net id-ul obiectelor plasate** = 0x40000005 + rangul hash-ului cheii printre șabloanele de entități.
- **Kill**: 437 = scor {assisturi, morți, kill-uri}; 577 {1, ucigaș} și {0} după 10 s; 1168 = bounty (+15 % din aurul
  de farm); 189 = valoarea pierdută după o moarte; 166 / 421 moartea; 1166 = recapitularea morții. Clientul arată
  singur FIRST BLOOD, killing spree, scorul.
- **Hash-ul de pachet** al oricărei unități: sdbm("[character]" + nume) · 65599^11 + 0xaef9ccfa.
- **Efecte vizuale**: cheia = FNV-1a a numelui din `resourceMap`-ul skin-ului (ex. „garen_e_spin"); ce numește
  campionul în datele lui (animații, mHitEffectKey) redă clientul singur; restul sunt ale scripturilor → pachetul 10.
  Pentru cei 10 campioni din înregistrare se folosește exact ce a făcut serverul real (`tools/fx_learn16.py`), pentru
  restul reguli pe nume (`_Cas` la cast, `_Tar` la lovitură, `_Slow/_Stun` cât ține efectul, `_AoE` la țintă).
  Efectele comune (stun, slow, Ignite, recall) se adresează prin numele particulei.
- **Recall**: cast (slot 13, 0,5 s), apoi 8 s: 612, 794 (animația), 331 „RecallLeadIn" + „RecallChannelingUpdate"
  la 0,26 s, buff, particula TeleportHome; la final 584, 794 gol, 262, teleport.

### Confirmat în client (capturi în `data/exe1620/match_*`)
orice campion cu modelul, HUD-ul și vrăjile lui · ecranul de încărcare cu lista noastră · valuri pe lane-urile reale ·
ceața de război (minioni, campioni, monștri) · turnuri, inhibitor cu ruină, nexus, VICTORY și ieșirea clientului ·
kill-uri cu FIRST BLOOD / killing spree / scor / recapitularea morții · efecte scriptate (Garen Q/W/E, Lux E/R) ·
recall (cerc, animație, buff) · magazin · junglă · skin ales și vrăji de invocator alese · champion select cu
selector de skin și de vrăji.

### Ce lipsește
rune (pachetul 905 nu e învățat: cititorul structurii 0xe7ea00 nu trece de sonda de varint a învățătorului; se trimit
runele înregistrate), plăcile turnurilor, structurile inamice în ceață (la noi mereu vizibile), tabela octetului de
slot la vânzare (2 din 7 sloturi), pasivele campionilor și efectele lor, scripturile exacte ale vrăjilor (regulile
pe nume acoperă ~60 % din ce a arătat serverul real la cei 10 campioni măsurați), reglajul boților.
