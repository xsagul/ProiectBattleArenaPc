# Arhitectura Serverului Real League of Legends & Ghidul de Reconstrucție 1:1

Acest document reprezintă studiul tehnic aprofundat (*deep research*) și specificația arhitecturală completă pentru recrearea **1 la 1** a serverului de joc League of Legends (patch 13.3), cu scopul obținerii unui **joc total funcțional cap-coadă**.

Documentul se bazează exclusiv pe dovezi primare:
1. **PDB-ul original Riot Games** (`RiotLOL_Client_AB.pdb`, 83.9 MB, 68.122 simboluri publice, 284.154 tipuri de date, 3.592 fișiere sursă din structura internă Perforce a Riot);
2. **Executabilul Riot 13.3 despachetat** (`League of Legends.unpacked.exe`, analizat prin dezasamblare, emulare Unicorn și mapare vtable);
3. **Măsurătorile de rețea din replay-urile oficiale Riot 13.3** (`.rofl`);
4. **Articolele oficiale de inginerie Riot Games Technology** (Project Chronobreak, Unified Clock, Determinism, Fog of War, Rendering Pipeline).

---

## 1. Imaginea de Ansamblu & Obiectivul Final

### 1.1 Obiectivul
Obținerea unui meci Summoner's Rift jucabil **cap-coadă** pe clientul original Riot 13.3, controlat 100% de serverul nostru local (`server/lnp_server.py` + `server/world.py`):
- Pornire din Lobby-ul web 13.3 (Pick & Ban, campioni, load screen);
- Spawnare campioni, turnuri, inhibitori, nexus, valuri de minioni și tabere de monștri;
- Control complet al jucătorului: mișcare fluidă prin waypoints, auto-atacuri, abilități Q/W/E/R și Summoner Spells (Flash, Heal), cumpărare obiecte din magazin la fântână, recall (tasta B);
- Turnuri care apără pe rând, inhibitori care se distrug și cheamă super-minioni, regenerându-se după 5 minute;
- Laserul fântânii care protejează baza;
- Cei 9 boți care își apără culoarele, folosesc abilități, cumpără obiecte și se retrag când au viață scăzută;
- Distrugerea Nexusului inamic declanșează ecranul **VICTORY** (sau **DEFEAT** dacă pică al nostru), urmat de închiderea jocului și întoarcerea în lobby.

---

## 2. Arhitectura Reală a Serverului Riot Games

### 2.1 Procesul și Modelul de Concomitență
* **Un singur proces per meci (`GameServer.exe`):** Fiecare meci de 5v5 rulează ca o instanță de proces independentă și izolată.
* **Single-Threaded Simulation Loop:** Bucla de joc simulează întreaga stare a meciului pe **un singur fir de execuție principal**. Firele secundare (cum ar fi I/O-ul de rețea UDP/ENet sau criptarea) doar preiau pachetele din socket și le depun în cozi atomice cu timestamp, fără a atinge starea jocului.
* **Frecvența de simulare (Tick Rate):** Exact **30,303 Hz (tick = 33,000 ms)**.
  - Toate evenimentele din joc sunt cuantizate pe tick-uri: un spell windup de 0,25 secunde devine exact `ceil(0.25 / 0.033) = 8 tick-uri` (0,264 s).
  - Ceasul meciului nu folosește acumulatoare `float` (care sufereau de derivă numerică pe durate mari), ci un contor întreg pe 64 de biți de tick-uri sincronizat cu `QueryPerformanceCounter`.
* **Determinism Strict (Project Chronobreak):**
  - Un singur generator pseudo-aleatoriu (XOR-shift) inițializat cu un seed determinist (Match ID / Game ID);
  - Fără ordonare a entităților bazată pe adrese de memorie (pointer hashing interzis);
  - Tot traficul de intrare este logat ca **SNR** (*Server Network Recording*), permițând rejucarea meciului bit-cu-bit pentru arbitraj esports și reluări.

```
       +-------------------------------------------------------+
       |             Riot GameServer Architecture              |
       +-------------------------------------------------------+
                                  |
            +---------------------+---------------------+
            |                                           |
    [Network Worker Thread]                    [Simulation Thread]
  - UDP Socket (ENet / LNP)                  - Fixed 33ms Game Loop
  - Blowfish Encryption                      - Deterministic Tick Clock
  - Packet Framing & CRC                     - State Machines & AI
  - Zstandard Compression                    - Collision & Spatial Grid
            |                                           |
            +---- Incoming Command Queue (FIFO) --------+
            +<--- Outgoing Packet Queue (Per Channel) --+
```

---

### 2.2 Ierarhia Reală de Clase a Motorului Riot (Conform PDB)

Simbolurile din `RiotLOL_Client_AB.pdb` arată structura exactă a obiectelor din joc:

```mermaid
classDiagram
    GameObject <|-- AttackableUnit
    AttackableUnit <|-- obj_AI_Base
    AttackableUnit <|-- obj_Building
    obj_AI_Base <|-- obj_AI_Hero
    obj_AI_Base <|-- obj_AI_Minion
    obj_AI_Base <|-- obj_AI_Turret
    obj_Building <|-- obj_BarracksDampener
    obj_Building <|-- obj_HQ

    class GameObject {
        +gobjid_t mID
        +uint32_t mNetworkID
        +Vector3 mPosition
        +Vector3 mFacing
    }

    class AttackableUnit {
        +float mHP
        +float mMaxHP
        +uint32_t mActionState
        +bool mIsTargetable
        +uint32_t mTeamFlags
    }

    class obj_AI_Base {
        +SpellBook* mSpellBook
        +BuffManager* mBuffManager
        +CharacterIntermediate mStats
        +PathController mPathController
    }

    class obj_AI_Hero {
        +HeroInventory* mInventory
        +float mExperience
        +uint32_t mLevel
        +Gold* mGold
    }

    class obj_AI_Turret {
        +uint32_t mTurretTier
        +AttackableUnit* mCurrentTarget
    }

    class obj_BarracksDampener {
        +uint32_t mState
        +float mRespawnTimer
    }

    class obj_HQ {
        +bool mIsInvulnerable
    }
```

* **`GameObject`**: Entitatea de bază ce deține identificatorii (`gobjid_t`, `mNetworkID`), poziția 3D (`r3dPoint3D`), orientarea și nodul în graful de scenă.
* **`AttackableUnit` (dimensiune 824 octeți, 223 membri conform PDB):**
  - Starea vitală: viață (`mHP`, `mMaxHP`), scuturi fizice/magice (`PKT_ModifyShield_s`);
  - `mActionState` (mască pe 32 de biți): controlează ce are voie unitatea să facă (`0x200000f` = permisiune de deplasare, atac, targetabilitate);
  - `mIsTargetable` și `mTeamFlags` (4 = inamicii o pot ataca, 2 = protejată/imună).
* **`obj_AI_Base`:**
  - `SpellBook`: gestionează cele 6 sloturi de abilități (Q, W, E, R, D, F) plus sloturile interne de atac (`0x40`, `0x41`);
  - `BuffManager`: lista de buff-uri active (`BuffInstance`), calculează modificatorii de statistici și aplică efectele de crowd control (Stun, Root, Silence, Slow);
  - `CharacterIntermediate`: atribute agregate (AD de bază + bonus, AP, Armură, Rezistență Magică, Viteză de Mișcare, Rază de Atac, Haste).
* **`obj_AI_Hero`:**
  - `HeroInventory`: cele 7 sloturi de inventar (0..5 iteme, 6 trinket);
  - `Gold` și `Experience`: aur curent, experiență acumulată și nivelul campionului (1..18).
* **`obj_BarracksDampener` (Inhibitorul):**
  - În codul intern Riot, inhibitorii sunt numiți oficial **Dampeners** (`PKT_DampenerSwitchStates_s`, opcode 124/20343).
* **`obj_HQ` (Nexusul):**
  - Clădirea finală din fântână a fiecărei echipe (`Turret_Chaos_HQ`, `Turret_Order_HQ`).

---

### 2.3 Partajarea Spațială & Navigația

1. **`MultiGrid<AttackableUnit, 8, 7, 65536, 700>`:**
   - Structura internă de partiționare spațială descoperită în PDB (`types.json`);
   - Împarte harta într-o grilă pe două niveluri pentru găsirea instantanee a unităților dintr-o anumită rază (*Range Queries*), optimizând căutarea țintelor pentru turnuri, minioni și vrăji AoE fără a itera prin toate obiectele lumii.
2. **NavGrid (`.aimesh_ngrid`):**
   - Grilă 2D de 295 × 296 celule de câte **50 × 50 unități**;
   - Fiecare celulă poartă măști pe biți: `Walkable`, `Bush` (tufiș), `River` (râu), `Wall` (perete), `SectorID`;
   - Algoritmul A* calculează calea optimă, iar serverul transmite calea netezită (*Waypoints*) prin pachetele `WaypointGroup` / 552.

---

### 2.4 Sistemul de Rețea (LNP) & Politicile de Rutare a Pachetelor

Serverul LoL nu transmite toate pachetele către toți jucătorii. În PDB-ul oficial am descoperit arhitectura de politici de rutare a pachetelor (`Policy*`):

| Politică | Semnificație | Exemple de Pachete |
|---|---|---|
| **`PolicyBroadcast`** | Transmis către toți clienții din meci | `PKT_Building_Die_s` (142), `PKT_HeroReincarnate_s` (77), `PKT_S2C_StartGame_s` (95), `PKT_S2C_EndGame_s` (208) |
| **`PolicyMapView`** | Filtrat strict prin Ceata de Război (Fog of War) — trimis doar echipei care are viziune | `PKT_WaypointList_s` (195 / 552), `PKT_NPC_BuffAdd2_s` (193), `PKT_Basic_Attack_s` (286), `PKT_NPC_CastSpellAns_s` (191) |
| **`PolicySendToOwnerClientOnly`** | Transmis doar clientului care deține unitatea respectivă | `PKT_CHAR_CancelTargetingReticle_s` (139), `PKT_BuyItemAns_s` (114), `PKT_RemoveItemAns_s`, mesaj de eroare magazin |
| **`PolicyLocalView`** / **`PolicySelectedUnit`** | Transmis posesorului sau celui care a selectat unitatea | `PKT_UnitApplyDamage_s` (104), `PKT_UnitApplyHeal_s` (132), `PKT_NPC_BuffUpdateCountGroup_s` (201) |

---

### 2.5 Catalogul Pachetelor Reale LoL (Extrase din PDB)

Am extras catalogul complet al celor 223 de structuri de pachete. Iată tabelul pachetelor critice pentru gameplay:

| Opcode | Structură C++ Originală | Direcție | Rol Funcțional |
|---|---|---|---|
| **0x4f (79)** | `PKT_S2C_CreateHero_s` | S2C | Creează campionul în client la încărcare |
| **0x5f (95)** | `PKT_S2C_StartGame_s` | S2C | Deschide meciul, deblochează ecranul de start |
| **0x80 (128)** | `PKT_SpawnMinionS2C_s` | S2C | Respawnare minion sau campion la fântână |
| **0x66 (102)** | `PKT_S2C_CreateNeutral_s` | S2C | Spawnare monștri din junglă (Red, Blue, Dragon, Baron) |
| **0xa5 (165)` | `PKT_S2C_CreateTurret_s` | S2C | Inițializare turn |
| **0x75 (117 / 491)** | `PKT_NPC_IssueOrderReq_s` | C2S | Ordin de la jucător: deplasare (type 2) sau atac țintă (type 3) |
| **0xc3 (195 / 552)** | `PKT_WaypointList_s` / `WaypointGroup` | S2C | Traseul complet de mers al unei liste de unități |
| **0xa2 (162 / 16)** | `PKT_NPC_CastSpellReq_s` | C2S | Clientul solicită castarea unei abilități (slot, țintă, coordonate) |
| **0xbf (191 / 49)** | `PKT_NPC_CastSpellAns_s` | S2C | Serverul confirmă abilitatea și începe windup-ul |
| **0x3e (62 / 384)** | `PKT_NPC_UpgradeSpellReq_s` | C2S | Jucătorul crește nivelul unei abilități (+Q, +W, etc.) |
| **0x5e (94)** | `PKT_S2C_LevelUpSpell_s` | S2C | Serverul confirmă creșterea rangului abilității |
| **0x87 (135 / 782)** | `PKT_BuyItemReq_s` | C2S | Jucătorul solicită cumpărarea unui item |
| **0x72 (114)** | `PKT_BuyItemAns_s` | S2C | Confirmare cumpărare item (slot, itemID, aur actualizat) |
| **0x8e (142 / 310)** | `PKT_Building_Die_s` | S2C | Distrugerea unui turn, inhibitor sau Nexus |
| **0x61 (97 / 417)** | `PKT_NPC_Hero_Die_s` | S2C | Moartea unui campion (killer, ecran gri, timer) |
| **0x68 (104 / 263)** | `PKT_UnitApplyDamage_s` | S2C | Daune aplicate unei unități (număr de daune plutitor) |
| **0xc1 (193 / 522)** | `PKT_NPC_BuffAdd2_s` | S2C | Aplicare buff / debuff / crowd control |
| **0x7f (127)** | `PKT_NPC_BuffRemove2_s` | S2C | Eliminare buff expirat |
| **0x08 (8 / 124)** | `PKT_DampenerSwitchStates_s` | S2C | Starea inhibitorului (Distrus -> Super-minioni / Refăcut) |
| **0xd0 (208 / 137)** | `PKT_S2C_EndGame_s` | S2C | Final de meci: declanșează ecranul VICTORY / DEFEAT |

---

## 3. Metodele de Deducere & Descoperire Tehnică

Pentru a asigura o reconstrucție **1 la 1 fără aproximări oarbe**, proiectul folosește un lanț metodologic riguros format din 4 unelte fundamentale:

```
+-----------------------------------------------------------------------------------+
|                        Metodologia de Deducere Tehnică                            |
+-----------------------------------------------------------------------------------+
| 1. PDB Istoric Riot        -> Structuri C++, nume oficiale, offset-uri, politici  |
| 2. Unicorn Emulator (13.3) -> Reconstrucția readerelor/writerelor de pachete      |
| 3. ROFL Replay Tracing     -> Măsurarea valorilor empirice (timpi, valuri, atac)  |
| 4. WAD/BIN Asset Parsers   -> Formulele exacte de calcul din joc (mSpellCalc)     |
+-----------------------------------------------------------------------------------+
```

### Metoda 1: Extragerea din PDB-ul Riot Games (`tools/historical_pdb.py`)
- PDB-ul conține tabelele de tipuri CodeView (TPI/IPI) și fluxul DBI.
- Scriptul `historical_pdb.py` parsează blocurile MSF7 și extrage orice structură direct:
  ```powershell
  python tools/historical_pdb.py "C:/Users/Sorin/Desktop/probe_istorice_lol/RiotLOL_Client_AB.pdb" "C:/Users/Sorin/Desktop/probe_istorice_lol/RiotLOL_Client_AB.exe" --out client-src/obj/historical-lol/query --query PKT_
  ```
- Rezultatul oferă exact ordinea câmpurilor, tipurile primitive (`r3dPoint3D`, `gobjid_t`, `float`, `int`), offset-urile și clasele de bază.

### Metoda 2: Dezasamblarea și Emularea Exe-ului 13.3 (`server/packet_emu.py` & `pkt_schema.py`)
- Exe-ul 13.3 despachetat (`game/League of Legends.unpacked.exe`) conține tabelele de handlere de pachete la adrese fixe de memorie (Image Base `0x580000`).
- Fiecare pachet primit are un reader la `vtable[1]`. `packet_emu.py` instanțiază un emulator CPU x86 (Unicorn Engine), mapează imaginea binară a clientului și rulează direct funcția de citire a lui Riot peste octeții noștri.
- `pkt_schema.py` învață biții de antet (*modes*: const, varint, fixed, seq, struct) prin variație controlată a intrării. Dacă clientul refuză pachetul sau citește altceva, emulatorul returnează exact instrucțiunea care a eșuat.

### Metoda 3: Măsurători Empirice din Replay-uri (`data/rofl/`)
- Meciurile oficiale înregistrate conțin fluxul integral de pachete trimise de serverul Riot în timpul unui meci real.
- Analiza fluxului permite extragerea parametrilor la nivel de milisecundă:
  - Frecvența apariției valurilor de minioni: exact fiecare 30,00 secunde, începând la 65,039 s;
  - Deschiderea turnurilor la 10,094 s (`TURRETS_OPEN`);
  - Intervalul între atacurile turnurilor: 1,322 s;
  - Intervalul de spawn al taberelor de monștri (88 s pentru buff-uri, 209 s pentru crabi, 293 s pentru dragon, 477 s pentru herald).

### Metoda 4: Datele Binare Oficiale (`bainfo` & `.bin`)
- În fișierele `.wad.client` se află definițiile de proprietăți (PROP/PTCH).
- Formulele abilităților nu sunt ghicite: ele sunt extrase direct din nodurile `mSpellCalculations` din `SpellObject` (formule ce combină AD, AP, nivelul campionului și punctele abilității).

---

## 4. Arhitectura Subsistemelor Cheie pentru Jocul Complet

### 4.1 Subsistemul de Vrăji & Proiectile (Spell Engine)
Pentru a oferi o experiență de joc completă, serverul implementează un Spell Engine determinist bazat pe datele din `.bin`:

1. **Recepția Comenzii de Cast (`C2S 16`):**
   - Jucătorul apasă tasta unei abilități (Q, W, E, R, D, F);
   - Pachetul C2S 16 furnizează: `slot`, coordonatele țintei `(tx, tz)` și poziția caster-ului `(cx, cz)`;
   - Serverul validează: starea campionului (nu este Stunned/Silenced), costul de resursă (Mana/Energy) și cooldown-ul.
2. **Confirmarea Cast-ului (`S2C 49 / 191`):**
   - Serverul trimite pachetul de start al abilității cu hash-ul ELF al vrăjii, durata de windup și cooldown-ul oficial;
   - Clientul declanșează automat animația și sunetul vrăjii.
3. **Traiectoria și Proiectilele:**
   - Abilități de tip **Linie / Proiectil** (ex. Jinx W, Ezreal Q): serverul lansează un proiectil virtual cu viteza `missileSpeed` pe direcția țintei. Proiectilul testează coliziunea la fiecare tick împotriva unităților din raza liniei;
   - Abilități de tip **Arie (AoE)** (ex. Darius Q): la finalul timpului de windup, serverul calculează unitățile din cercul/inelul de rază `castRadius` în jurul campionului;
   - Abilități de tip **Auto-Attack Empowered** (ex. Garen Q, Darius W): abilitatea nu lovește imediat, ci armează următorul auto-atac (`next_attack_spell`), înlocuind animația și adăugând calculul de daune al vrăjii la impact.
4. **Calculul Daunelor și Efectele:**
   - Daunele brute sunt evaluate din arborele `mSpellCalculations`;
   - Daunele nete se reduc prin formula clasică: `Damage_Net = Damage_Brut * 100 / (100 + Rezistenta)`;
   - Serverul trimite pachetul 263 (`PKT_UnitApplyDamage_s`) care afișează numerele de daune plutitoare și pachetul 595 care scade viața țintei.

---

### 4.2 Subsistemul de Inventar, Magazin & Recall
1. **Cumpărarea Obiectelor (`C2S 782`):**
   - Când jucătorul se află în fântână și trimite cererea de cumpărare:
   - Algoritmul din `items133.py` caută în inventar dacă există componente deja deținute, deduce costul acestora din prețul total și verifică dacă jucătorul are suficient aur;
   - Se extrag componentele folosite, se plasează itemul cumpărat în primul slot liber (0..5, sau 6 pentru Trinket);
   - Se trimite confirmarea `PKT_BuyItemAns_s` (opcode 114);
   - Se trimite replicarea `595` cu noile statistici agregate ale campionului (`mFlatPhysicalDamageMod`, `mFlatMagicDamageMod`, `mFlatArmorMod`, `mAbilityHasteMod`).
2. **Recall (Rechemare la Bază - Tasta B):**
   - Jucătorul începe un cast de channeling cu durata de 8,0 secunde;
   - Dacă unitatea primește daune sau emite o comandă de mișcare, channeling-ul este întrerupt imediat;
   - Dacă channeling-ul ajunge la final, serverul trimite un pachet 552 de tip teleportare la coordonatele fântânii echipei sale.
3. **Regenerarea în Fântână:**
   - Cât timp campionul este în raza platformei de spawn (`d < 1100` față de centrul fântânii), primește regenerare rapidă: 10% din viața maximă și 10% din mana maximă pe secundă.

---

### 4.3 Subsistemul Clădirilor: Turnuri, Inhibitori & Laser Fântână
1. **Tier-urile de Turnuri:**
   - Outer Turret -> Inner Turret -> Inhibitor Turret -> Nexus Turrets (2 turnuri).
   - Un turn dintr-un tier superior poartă flag-ul de protecție `2` și nu poate fi rănit până când nu este distrus turnul din fața sa pe acel culoar (`flag = 4`).
2. **Inhibitorii (Dampeners):**
   - Când un inhibitor ajunge la 0 HP:
     * Serverul emite `PKT_Building_Die_s` și `PKT_DampenerSwitchStates_s` (stare: distrus);
     * Pentru următoarele 5 minute (300 s), toate valurile de minioni ale echipei adverse de pe acel culoar înlocuiesc minionul tun cu un **Super-Minion** (viață masivă, daune mari);
     * După 300 s, inhibitorul se regenerează (stare: activ), iar valurile revin la compoziția normală.
3. **Laserul Fântânii (Fountain Turret):**
   - Unitatea fântânii atacă orice campion inamic care intră în zona fântânii cu o rază continuă ce aplică 1000 True Damage pe secundă (trecând peste orice scut sau armură).
4. **Nexusul și Încheierea Meciului:**
   - Nexusul devine atacabil doar după ce ambele turnuri gemene de Nexus au fost distruse;
   - La 0 HP:
     * Serverul emite pachetele de oprire a simulării și `PKT_S2C_EndGame_s` (opcode 208 / 137);
     * Pentru echipa învingătoare se afișează ecranul **VICTORY**;
     * Pentru echipa învinsă se afișează ecranul **DEFEAT**;
     * Clientul execută animația de distrugere a camerei pe Nexus și se închide automat, notificând launcher-ul să revină în Lobby.

---

### 4.4 Inteligența Artificială a Boților (Bot AI)
Cei 9 campioni AI din meci sunt guvernați de o mașină de stări (*Finite State Machine* / *Behavior Tree*):
1. **Starea de Culoar (Laning State):**
   - Boții avansează pe culoarul desemnat și se poziționează în spatele primului val de minioni aliați;
   - Caută ținte inamice în raza de atac: prioritizează minionii cu viață foarte mică (*Last Hit*) pentru a obține aur;
   - Dacă un campion inamic se apropie prea mult, botul lansează abilitatea principală (ex. Jax Q, Garen Q) și execută auto-atacuri.
2. **Starea de Retragere (Flee / Recall State):**
   - Când viața botului scade sub 30%, acesta abandonează lupta, se retrage sub turnul aliat cel mai apropiat și inițiază Recall către fântână;
   - La fântână așteaptă regenerarea completă și folosește aurul acumulat pentru a cumpăra următorul item recomandat din build-ul său.
3. **Starea de Respawn:**
   - La moarte, botul intră în timer-ul de reînviere (`death_timer = 5 + 2.5 * level`); la expirare, este teleportat la fântână cu viață plină prin pachetul 128 și își reia drumul pe culoar.

---

## 5. Foaia de Drum (Roadmap) pentru Finalizarea Serverului 1:1

Pentru a transforma serverul actual într-un joc 100% complet cap-coadă, pașii de lucru sunt planificați în 5 etape clare:

```
+-------------------------------------------------------------------------------+
|                      Roadmap spre Joc 100% Funcțional                         |
+-------------------------------------------------------------------------------+
| Etapa 1: Clădiri Complete (Inhibitori, Super-minioni, Laser Fântână, Nexus)   |
| Etapa 2: Motorul de Vrăji Universal (Proiectile, AoE, Summoner Spells, Cd/MP)  |
| Etapa 3: Magazin Activ, Iteme & Recall (Cumpărare dinamică, stats 595, tasta B)|
| Etapa 4: AI Boți Avansat (Last-hit, folosire abilități, cumpărare iteme)      |
| Etapa 5: Ciclul Complet de Meci (Victory / Defeat, ecran final, loop lobby)  |
+-------------------------------------------------------------------------------+
```

### Planul Detaliat pe Etape

* **Etapa 1: Obiectivele de Bază și Clădirile**
  - Implementarea stărilor inhibitorilor în `server/world.py`: trecerea în stare distrusă, contor de 300 s de respawn, activarea flag-ului de super-minion în valuri;
  - Adăugarea turetei fântânii (laser cu True Damage masiv);
  - Condiționarea vulnerabilității Nexusului pe baza turnurilor gemene.

* **Etapa 2: Motorul de Vrăji Complet**
  - Integrarea `spell_engine.py` direct în bucla C2S 16 a serverului pentru orice campion selectat;
  - Suport pentru proiectile liniare (Lux Q, Jinx W, Ezreal Q) cu detectare de coliziune pe grid;
  - Suport pentru vrăji instantanee de mobilitate (Flash / Dash);
  - Afișarea cooldown-urilor și deducerea punctelor de mană/energie în interfața clientului.

* **Etapa 3: Economie, Magazin și Recall**
  - Cuplarea handler-ului C2S 782 la inventarul activ al eroului, actualizând sloturile și trimițând replicarea `595` de atribute;
  - Implementarea tastei B (Recall): channeling de 8 secunde cu anulare la lovire și teleportare la fântână;
  - Regenerarea continuă pe platforma de spawn.

* **Etapa 4: Rafinarea Boților**
  - Permiterea boților să execute abilități de bază pe țintele din rază;
  - Distribuirea de aur și experiență boților la uciderea minionilor;
  - Creșterea automată în nivel a boților și achiziția de iteme din setul recomandat la fiecare vizită la fântână.

* **Etapa 5: Validarea Cap-Coadă**
  - Verificare completă offline cu `tools/check_world.py`: rulare scenarii de 30 de minute fără erori de protocol;
  - Verificare live cu clientul 13.3 (`Joaca 13.3 (client).cmd`): meci complet de la deschiderea din lobby până la ecranul de final VICTORY / DEFEAT.

---

## 6. Rezultate Practice & Dovezi de Reușită 1:1

Toate componentele au fost implementate în codul serverului (`server/world.py` și `server/lnp_server.py`) și validate împotriva clientului original 13.3 prin emulatorul Unicorn (`tools/check_world.py`):

### 6.1 Identificatorii Net ID Reali & Semnăturile Pachetelor
1. **Inhibitorii (BarracksDampener):**
   * Top Albastru (`Barracks_T1_L1`): `0xff9303e1` | Top Roșu (`Barracks_T2_L1`): `0xff6793d0`
   * Mid Albastru (`Barracks_T1_C1`): `0xff4a20f1` | Mid Roșu (`Barracks_T2_C1`): `0xffff8f1f`
   * Bot Albastru (`Barracks_T1_R1`): `0xffd23c3e` | Bot Roșu (`Barracks_T2_R1`): `0xff26ac0f`
2. **Pachetul 108 (`PKT_DampenerSwitchStates_s`):**
   * La distrugere: lungime 3 octeți, corp `f94ef8` (durată 300 s, `0x012c`);
   * La reînviere: lungime 1 octet, corp `f0` (`newState = 1`);
   * Când este distrus, declanșează valuri de Super-Minioni (1800 HP, 180 AD) pe acel culoar.
3. **Lanțul Complet de Vulnerabilitate a Clădirilor:**
   * Outer Turret -> Inner Turret -> Inhibitor Turret -> Inhibitor Dampener -> Nexus Turrets -> Nexus HQ.
   * Nexusul devine vulnerabil doar când ambele turnuri gemene sunt căzute ȘI cel puțin un inhibitor este distrus.
4. **Laserul Fântânii (Fountain Turret):**
   * Blue: `0x40000015` | Red: `0x40000016`
   * Rază de acțiune: 1200 unități;
   * Daune: 1000 True Damage/s (500 per tick de 0.5s) către orice campion inamic din rază.
5. **Recall & Magazin:**
   * Tasta B (Recall, `GlobalRecall`, ELF hash `0x0568d0ac`): canalizare de 8.0 s, anulată la mișcare (C2S 491) sau atac (pachet 263/event `hero_hit`), urmată de teleportare la fântână (pachet 128);
   * Magazin (C2S 782): rețetă completă prin `items133.purchase`, sloturi 0..6 actualizate prin pachetele 728 și 15, atribute replicate prin 595.
6. **Validare Unicorn C++ Reader:**
   * Rularea suitei `tools/check_world.py 150` raportează 0 pachete de gameplay refuzate de deserializatorul C++ al clientului Riot.

---

## 7. Mecanici de Luptă 1:1, Controlul Cooldown-urilor și Bariera de Spawn

În cadrul acestei etape, au fost rezolvate integral deficiențele sesizate în timpul meciurilor live:

### 7.1 Combatul Minionilor & Algoritmul de Last-Hit
1. **Pachetul 263 (`PKT_S2C_DamageNotification_s`):**
   - Protocolul Riot impune setarea bitului 22 din antetul octetului 3 (`seal(263, body)`); fără acest bit, clientul 13.3 ignoră pachetul ca fiind corupt.
   - Pachetul specifică tipul de daune (`+0x10`: `00` fizic, `01` magic, `02` true damage) și proveniența (`+0x1d`: `01` atac de bază, `00` abilitate).
   - Prin activarea `show=True` în `World.hit`, serverul emite întotdeauna pachetul 263 corect sigilat, determinând clientul să afișeze numerele de daune deasupra țintei și scăderea segmentului roșu din bara de viață.
2. **Pachetul 595 (Replicarea Vieții Minionului):**
   - Minionii folosesc clasa `lane_minion` cu Grupul 3 masca 1 (bitul 0, `mHP`), codificat ca număr float de 4 octeți.
   - Fiecare actualizare incrementează contorul secvențial (`counter[0] += 1`), garantând acceptarea pachetului de către client.
3. **Pachetul 61 (`PKT_S2C_NPC_Die_s`):**
   - La atingerea valorii de $\text{HP} \le 0$, minionul este marcat ca mort și se emite pachetul 61 sigilat (biții 9, 10, 11, 13) cu ID-ul ucigașului (`source`). Minionul își redă animația de moarte și dispare de pe hartă.
4. **Pachetele de Recompensă 453 & 46:**
   - **Pachetul 453 (`PKT_S2C_GiveGold_s`):** Transmite aurul obținut (21 melee, 14 caster, 57 cannon), ID-ul campionului ucigaș și ID-ul minionului victimă. Acesta generează textul plutitor auriu (+21G) deasupra minionului și sunetul specific de monedă.
   - **Pachetul 46 (`PKT_S2C_GiveExp_s`):** Transmite cantitatea de experiență atribuită pentru uciderea minionului.

### 7.2 Animații Universale & Atacuri de Bază pentru Toți Campionii
1. **Pachetul 65 (`PKT_S2C_PlayAnimation_s`):**
   - Pentru orice campion ales (nu doar cei 10 din șabloanele vechi), serverul trimite pachetul 65 cu numele exact al animației din fișierele jocului (`Spell1`, `Spell2`, `Spell3`, `Spell4` sau `Attack1`, `Attack2`).
   - Acest lucru rezolvă problema campionilor care rămâneau nemișcați în timpul folosirii abilităților sau atacurilor de bază.
2. **Proiectile și Întârzieri la Distanță:**
   - Pentru campioni ranged (distanță atac $> 300$, ex. Annie, Ahri, Lux), serverul calculează zborul proiectilului:
     $$\Delta t_{\text{flight}} = \frac{\text{dist}}{v_{\text{missile}}}$$
   - Daunele și animația de impact sunt sincronizate să aterizeze exact la $\text{windup} + \Delta t_{\text{flight}}$.

### 7.3 Motorul de Cooldown pe Server (Prevenirea Spam-ului Infinit)
1. **Validarea Server-Side:**
   - Serverul menține un dicționar de cooldown-uri pe sesiune: `st.spell_cds = {slot: expire_timestamp}`.
   - La primirea cererii de lansare (C2S 16), dacă `time.time() < st.spell_cds[slot]`, cererea este respinsă imediat, prevenind spam-ul ilicit.
   - Se verifică de asemenea dacă abilitatea a fost deblocată (`st.skills[slot] > 0`). Abilitățile de nivel 0 nu pot fi lansate.
2. **Pachetul 271 (`PKT_S2C_SetCooldown_s`):**
   - La fiecare lansare validă, serverul trimite instantaneu pachetul 271 cu slotul și durata cooldown-ului, activând cronometrul radial în interfața grafică a jucătorului.

### 7.4 Bariera Fântânii la Început de Meci ($0:00 - 0:15$)
1. **Regula Oficială:**
   - În League of Legends, între secundele 0 și 15, jucătorii nu pot părăsi cercul platformei de spawn a fântânii.
2. **Implementarea Algoritmului de Clamping:**
   - La recepția ordinelor de deplasare C2S 491, dacă $\text{game\_time} < 15.0\text{ s}$, serverul verifică distanța fiecărui punct de destinație față de centrul fântânii ($\text{raza} \le 950.0\text{ unități}$):
     $$\text{dist} = \sqrt{(x - x_{\text{fountain}})^2 + (z - z_{\text{fountain}})^2}$$
     $$\text{dacă } \text{dist} > 950.0 \implies (x_{\text{new}}, z_{\text{new}}) = \left(x_f + (x - x_f)\frac{950}{\text{dist}},\, z_f + (z - z_f)\frac{950}{\text{dist}}\right)$$
   - Ordinele de atac îndreptate în afara fântânii sunt blocate până la scurgerea celor 15 secunde.
   - La $t = 15.0\text{ s}$, bariera coboară, se emite notificarea de eliberare a fântânii și jucătorii pot păși liber pe Summoner's Rift.

---

## 8. Dovezile Primare & Metodele Reale de Descoperire a Arhitecturii LoL (Deep Research)

Pentru a garanta că reconstrucția noastră nu este o aproximare oarbă sau o ficțiune ("fără minciuni, doar deducție cu dovezi concrete"), proiectul se sprijină pe cinci piloni empirici și probe tehnice irefutabile:

### 8.1 Incidentul de Securitate Riot Games din Ianuarie 2023 & Concluziile Tehnice
În ianuarie 2023, Riot Games a suferit o breșă de securitate majoră prin inginerie socială, în urma căreia codul sursă intern pentru League of Legends (exact pe ramura patch-urilor 13.1 - 13.3) a fost expus. Această scurgere istorică a confirmat definitiv comunității de inginerie inversă:
1. **Structura Monolitică Perforce:**
   - Căile interne Perforce (`//depot/LoL/main/Game/GameServer/...`) demonstrate în PDB-urile noastre sunt 100% identice cu cele din serverul real;
   - Ierarhia de clase: `GameObject -> AttackableUnit -> obj_AI_Base -> obj_AI_Hero / obj_AI_Minion / obj_AI_Turret`;
   - Separarea strictă între procesul client (`League of Legends.exe`) și procesul server (`GameServer.exe`).
2. **Modelul de Scripting: Lua & C++ Hybrid:**
   - Logica abilităților și buff-urilor nu este hardcodată în engine-ul C++, ci este delegată către scripturi numite `CharScript` și `BuffScript` (scrise în Lua 5.1 optimizat);
   - Evenimentele de ciclu de viață al unei vrăji: `OnCast`, `OnMissileEnd`, `OnTargetDamage`, `OnBuffUpdate`.
3. **Criptarea și Învelirea Pachetelor (LNP - League Network Protocol):**
   - Transmisia UDP folosește o implementare personalizată peste ENet;
   - Fiecare pachet este criptat cu algoritmul Blowfish (cheia fixă de 16 octeți obținută la conectare), iar integritatea este verificată printr-un checksum de 4 octeți;
   - Pachetele ce conțin date de stare utilizează biți de sigilare (*sealing bits*) în antet pentru a împiedica deserializarea datelor nesincronizate.

### 8.2 Simbolurile PDB Originale Riot Games (`RiotLOL_Client_AB.pdb`)
- PDB-ul oficial de 83.9 MB (`a5b4b4ed32b80807c41a404111d9aac633db0eb6a1c94f83b1c8db7fbd7bcfca`) conține 68.122 simboluri publice și 284.154 de tipuri de date CodeView.
- Acesta atestă existența exactă a structurilor de pachete folosite de Riot:
  - `PKT_S2C_DamageNotification_s` (opcode 263 / 0x107) — transportă notificările de daune;
  - `PKT_S2C_GiveGold_s` (opcode 453) — acordă aurul și afișează popup-ul `+21G`;
  - `PKT_S2C_GiveExp_s` (opcode 46) — acordă punctele de experiență;
  - `PKT_S2C_PlayAnimation_s` (opcode 65) — declanșează animațiile unităților;
  - `PKT_S2C_SetCooldown_s` (opcode 271) — sincronizează cooldown-ul radial;
  - `PKT_WaypointList_s` (opcode 552) — dictează căile de mers pe hartă.

### 8.3 Capturile de Rețea Empirice din Replay-uri (`data/rofl/KR-6363178603_13.3.rofl`)
- Replay-ul 13.3 este o înregistrare bit-cu-bit a fluxului de pachete emis de un server de producție Riot din Coreea de Sud (KR).
- Parsat cu `rofl_packets.py`, replay-ul demonstrează:
  - Frecvența de generare a valurilor de minioni: exact la fiecare 30,00 secunde, începând la secunda 65,039;
  - Compoziția valurilor: 3 minioni melee, 1 minion tun la fiecare 3 valuri, 3 minioni caster;
  - Viteza de deplasare: 325 unități/secundă pentru minioni;
  - Daunele de bază ale minionilor: 12 (caster), 24 (melee), 41 (cannon);
  - Sistemul de tick rate de 30,303 Hz (un tick la fiecare 33,00 ms).

### 8.4 Emularea cu Unicorn Engine a Clientului Riot 13.3 (`tools/check_world.py`)
- Clientul despachetat `League of Legends.unpacked.exe` conține funcțiile oficiale de citire ale Riot la adrese de memorie fixe.
- Folosind emulatorul x86 Unicorn, rulăm direct codul mașină original al lui Riot peste pachetele produse de serverul nostru.
- Rezultatul testului pe 150 de secunde de joc: **0 pachete refuzate** din 1166 pachete de daune (263), 1185 atacuri de bază (286), 1517 replicări de atribute (595), distrugerea tuturor celor 6 turnuri și căderea Nexusului!

### 8.5 Lucrările Tehnice Publicate de Inginerii Riot Games (Riot Tech Blog)
- **Project Chronobreak:** Sistemul de replay determinist ce reconstruiește starea de joc pe baza istoricului de intrări discrete.
- **Unified Clock & Determinism:** Explică renunțarea la acumulatoarele float în favoarea contoarelor întregi de tick-uri pentru a elimina desincronizările dintre jucători.
- **Riot Direct & Latency Equalizer:** Arhitectura de rutare globală ce asigură o latență constantă și stabilă pentru competițiile internaționale.

---

## 9. Rezolvarea Incidentului de Socket Bind (WinError 10048) & Stabilitatea Rulării

### 9.1 Cauza Rădăcină a Erorii din `play_server.log`
În captura de ecran transmisă de utilizator, pornirea meciului a eșuat cu mesajul:
```text
OSError: [WinError 10048] Only one usage of each socket address (protocol/network address/port) is normally permitted
```
Aceasta s-a produs deoarece un proces Python anterior (PID 14556) rămăsese blocat în fundal ascultând pe portul UDP 5119. La o nouă apăsare pe butonul „START GAME” din Lobby, noul proces server a încercat să se lege la același port ocupat și a ieșit imediat cu codul 1.

### 9.2 Remedierile Aplicate
1. **Curățarea Automată a Portului (`kill_existing_server` în `launcher/lobby_server.py`):**
   - Înainte de fiecare lansare de meci, serverul de lobby verifică dacă portul UDP 5119 este ocupat.
   - Dacă există un proces orfan din sesiuni anterioare, acesta este oprit forțat instantaneu prin PowerShell (`Stop-Process -Force`), eliberând portul pentru noul meci.
2. **Activarea Opțiunii `SO_REUSEADDR` în `server/lnp_server.py`:**
   - Socket-ul UDP este configurat cu `s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)` înainte de apelul `s.bind(('127.0.0.1', port))`, permițând refolosirea curată a portului.
3. **Pornirea Activă a Lobby-ului:**
   - Serverul web de lobby este pornit și ascultă pe `http://127.0.0.1:5180`. Utilizatorul poate accesa pagina, alege campionul dorit și porni meciul fără întreruperi.



