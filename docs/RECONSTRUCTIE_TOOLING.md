# Instrumente de reconstrucție verificate — 2026-10-08

Obiectivul rămâne sursa C++ care, compilată cu MSVC, reproduce instrucțiunile și
țintește simbolurile reale ale clientului. Decompilarea și echivalența semantică
ajută la descoperire; acceptarea rămâne în `tools/match_func.py` și auditul complet
în `tools/progress.py`. Procentul de similaritate objdiff nu este scor de paritate.

## Instalări locale

| Instrument | Versiune / amplasare | Utilizare verificată |
|---|---|---|
| Ghidra existent | 12.1.4, `toolchain/ghidra_12.1.4_PUBLIC` | Proiectul BA13, imagine x86 cu baza 0x580000 |
| JDK existent | 21.0.12.1+1, `toolchain/jdk-21.0.12.1+1` | JVM și compilarea bridge-ului Java |
| [Ghidra CLI](https://github.com/akiselev/ghidra-cli/tree/v0.2.2) | 0.2.2, `toolchain/ghidra-cli/ghidra.exe` | Decompilare și inspecție JSON prin bridge persistent |
| [PyGhidra](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Features/PyGhidra/pypkg/README.md) | 3.1.0, în `toolchain/reconstruction-env` | API direct: bytes, instrucțiuni, apeluri, tipuri, ABI, P-code |
| [objdiff](https://github.com/encounter/objdiff/tree/v3.8.2) | 3.8.2, `toolchain/objdiff/objdiff-cli-windows-x86_64.exe` | Comparație între obiecte COFF x86 produse de MSVC |
| [Z3](https://github.com/Z3Prover/z3) | `z3-solver==4.15.4.0`, în mediul izolat | Dovezi și contraexemple pentru expresii bit-vector |
| [Skill ghidra-cli](https://github.com/akiselev/ghidra-cli/blob/v0.2.2/.claude/skills/ghidra-cli/SKILL.md) | `C:/Users/Sorin/.codex/skills/ghidra-cli` | Instrucțiuni upstream revizuite și instalate; disponibil în catalog din următoarea tură |

Nu s-a reinstalat Ghidra și nu s-a schimbat JDK-ul proiectului. Mediul Python
principal al generatoarelor rămâne separat. PyGhidra provine din wheel-urile
distribuției Ghidra locale, cu JPype1 1.5.2 și packaging 25.0; Z3 din PyPI.

Arhiva Windows Ghidra CLI a fost descărcată din release-ul upstream v0.2.2;
SHA256 verificat față de digest-ul asset-ului GitHub:
`36d1b70cbc6ff20860953631d73707b9ea05a29bfc705c8222e4e1bdb3f608f8`.
Pentru executabilul objdiff v3.8.2:
`36d229ac6ce74a26b47f42cf86ea8e808d8cd834a54aa62d7ed3f47b765d971b`.
Sursele și hash-urile sunt păstrate și în `provenance.json` lângă executabile.
Skill-ul este cel din tag-ul v0.2.2, SHA256
`7dd69a910d53d25bbe9169e067d1c96ff24613a6a425fb4d699d66e4317fb4b5`.

## Comenzi pe proiectul real

Rulați din rădăcina proiectului, în PowerShell. CLI-ul primește **VA**, iar
exportatorul Python primește **RVA hexadecimal**. Pentru client, VA = 0x580000 + RVA.

```powershell
python tools/ghidra_cli.py doctor
python tools/ghidra_cli.py decompile 0x864990 --with-vars --with-params
python tools/ghidra_cli.py stop

toolchain/reconstruction-env/Scripts/python.exe tools/ghidra_inspect.py 0x2e4990 0x188980 --pcode -o client-src/obj/tooling-research/batch-inspect.json
toolchain/reconstruction-env/Scripts/python.exe tools/ghidra_inspect.py 0x613110 --verified-abis -o client-src/obj/destructor-ui.json
toolchain/reconstruction-env/Scripts/python.exe tools/re_tooling_probe.py

toolchain/objdiff/objdiff-cli-windows-x86_64.exe diff -1 obiect-referinta.obj -2 obiect-candidat.obj -o diferenta.json --format json
```

Bridge-ul CLI și PyGhidra au acces exclusiv la același proiect. Opriți bridge-ul
înaintea comenzilor PyGhidra; nu lansați cititori simultani pe BA13. Pentru lucru
cu subagenți, exportați lotul o singură dată și distribuiți JSON-ul; împărțiți apoi
fișierele sursă și probele de compilare, cu un singur proprietar pentru fiecare.
Auditul complet rămâne un proces separat, pornit după integrare.

`ghidra_inspect.py` exportă decompilarea, semnătura, instrucțiunile cu octeți,
apelurile directe cunoscute și, opțional, P-code-ul brut al instrucțiunilor.
Compară fiecare instrucțiune cu `client-src/exe_image_unpacked.bin` înainte de
scrierea rezultatului. Funcțiile absente din index sunt create doar în tranzacția
temporară. Nu rezolvă automat țintele tuturor apelurilor indirecte și nu validează
o sursă C++ candidat.

Există o coliziune de import Python între directorul local `tools/ghidra` și
pachetul Java `ghidra`. Cele două scripturi PyGhidra exclud directorul `tools`
din `sys.path` înainte de încărcarea API-ului; directorul Java existent este păstrat.

`--verified-abis` aplică temporar convențiile și semnăturile măsurate pentru șapte
entry points native și elimină adnotări noreturn greșite. Pentru instrucțiuni CALL
către acestea, elimină flow override-ul noreturn și recalculează corpul funcției.
Override-urile JMP care reprezintă tail calls sunt păstrate. În proba **0x613110**,
baza existentă transforma bucla în `if` cu ieșire imediat după destructorul UI;
după corecție apar bucla completă și deallocarea condiționată. Exportul verifică
**57 bytes**, iar tail-call wrapperul **0x64c470** rămâne de **21 bytes**.
Modificările sunt în tranzacția care se termină prin rollback, fără salvare în BA13.
Această opțiune nu deduce automat ABI-ul celorlalte funcții și nu stabilește
contractul C++ al callback-urilor din valorile reziduale ale registrelor.

## Dovezi obținute

* Replay, RVA **0x2e4990**, este decompilat din BA13; **36/36 bytes** din proiect
  sunt identici cu imaginea autoritară. API-ul instrucțiunilor identifică apelul
  către **RVA 0x996470**. Aceasta verifică intrarea de analiză, nu o sursă nouă.
* Funcția placement **RVA 0x188980**, absentă din indexul Ghidra existent, este
  creată temporar. Definirea structurii de 16 bytes și a ABI-ului `void __cdecl`
  produce `p->data`, `p->size`, `p->capacity`, `p->value`, în locul acceselor
  `param_1[0..3]`. Structura corespunde formei deja verificate în sursa proiectului;
  pseudocodul singur nu dovedește proprietatea/lifetime-ul C++. Funcția și tipul
  temporare sunt eliminate prin rollback și absența lor este verificată explicit.
* Exportul în lot pentru aceste două funcții, inclusiv P-code, trece verificarea
  instrucțiunilor față de client. O execuție locală a durat aproximativ 9 secunde,
  inclusiv pornirea JVM; nu este o estimare pentru toate cele 60.454 funcții.
* objdiff citește obiectele COFF MSVC ale Replay. Comparația cu același obiect
  este identică; comparația celor două profile de compilare raportează
  **87,69231%** similaritate pentru funcție și evidențiază `setne al` față de
  ramura cu `mov al,1`. Aceste profile produc corpuri de 35, respectiv 36 bytes.
* Z3 demonstrează comutativitatea înmulțirii modulo 2^32 (`unsat` pentru diferență)
  și găsește contraexemplul **x = 0xffffffff / -1** pentru împărțirea signed la 2
  față de shift aritmetic la dreapta (`sat`). Semanticile C++ nedefinite, memoria,
  excepțiile și durata de viață trebuie modelate separat înaintea unei dovezi.

Rapoarte locale în `client-src/obj/tooling-research/`: `ghidra-replay.json`,
`batch-inspect.json`, `pyghidra-z3-probe.json`, `coff-self.json`, `coff-profile.json`.
Directorul cu probe și toolchain-ul sunt ignorate de Git; scripturile și această
documentație sunt în proiect. Testul PyGhidra nu salvează analiza în BA13.

## Limite descoperite și alternative evaluate

**Bug observat în Ghidra CLI 0.2.2:** `function calls` întoarce referințe incoming,
deși skill-ul îl prezintă drept outgoing. Wrapperul respinge această comandă;
exportatorul folosește `instruction.getReferencesFrom()` și filtrează referințele
CALL. Skill-ul upstream nu trebuie tratat drept dovadă a comportamentului tool-ului.

objdiff este verificat aici pentru **COFF vs COFF**. Nu avem încă un adaptor care
să transforme imaginea clientului și relocările ei într-un obiect de referință
objdiff. Pentru candidat vs client se folosește în continuare `match_func.py`;
nu se declară o funcție identică după procentul objdiff.

[decomp-permuter](https://github.com/simonlindholm/decomp-permuter) oferă motoare
pentru MIPS, PowerPC și ARM32, fără un backend MSVC x86 gata de utilizare; nu a
fost instalat ca soluție pentru acest client. Un căutător de variante C++ orientat
MSVC și integrat cu matcherul nostru rămâne o posibilă dezvoltare distinctă.

[IDA MCP oficial](https://github.com/HexRaysSA/ida-mcp) cere IDA 9.4+ cu idalib și
dependențele indicate de upstream. Nu s-a achiziționat o licență și nu s-a verificat
existența unei licențe a utilizatorului. Este o opțiune de al doilea decompiler,
nu o condiție pentru utilizarea instrumentelor deja instalate.

[ghidra-rpc](https://github.com/cellebrite-labs/ghidra-rpc) și skill-uri generale
de reverse engineering au fost evaluate; integrarea Windows concretă aleasă este
Ghidra CLI plus PyGhidra. angr nu a fost instalat în acest lot: execuția simbolică
generală nu este încă legată de un caz care să justifice costul de integrare.

Acest lot adaugă infrastructură, **nu un nou scor complet de paritate**. Ultimul
scor complet rămâne 21.038 funcții / 3.017.660 bytes / 18,95%, din auditul
`progress-2026-10-08-native-lifetimes`. Modificările ulterioare de sursă se
raportează separat până la următorul audit complet.

## 2026-10-10 — căutătorul de variante, layout-uri din callback-uri, cache de compilare

**`tools/permute.py` — ultima porțiune, făcută de procesor.** Primește o sursă care are deja logica bună și
aproape instrucțiunile clientului, o descompune în instrucțiuni C++ și aplică rescrieri mici, la întâmplare
(ordinea instrucțiunilor, ordinea operanzilor, `a += b` / `a = a + b`, valoare ținută într-un local sau nu,
forme de `if`/`else`, `for`/`while`, tipul localelor, atribuire de agregat pe membri, buclă pe componentele
unui vector). Fiecare variantă este fișierul real cu acel corp înlocuit, compilat cu compilatorul lui Riot pe
toate nucleele; scorul este numărul de instrucțiuni care diferă de client. Se oprește numai la identitate
confirmată de `match_func.compare` (octeți și ținte). O rescriere nu trebuie să păstreze sensul: singurul
judecător este codul clientului.

```bash
python tools/permute.py client-src/src/Fisier.cpp <rva hex> --minutes 30 --apply
python tools/permute.py --audit client-src/progress-<data>-audit.json --minutes 20
```

`--apply` scrie corpul găsit în sursă și îl păstrează numai dacă toate revendicările fișierului rămân
identice. Jurnal și cea mai bună variantă: `client-src/obj/permute/<sursa>_<rva>/` (`log.jsonl`, `best.cpp`,
`found.cpp`). Măsurat: ~10 variante pe secundă pe 8 nuclee pentru un fișier mic. `CalculateNineSlice`
(0xae4e40) de la forma 332/347 la identic în 26 de variante / 3 secunde; `LnpWorker::Post1` (0x2dd220, două
instrucțiuni în altă ordine) NU a fost găsit în 1.584 de variante / 5 minute. Limite: corpul nu poate conține
linii de preprocesor; un constructor cu listă de inițializare cu acolade nu este recunoscut; fiecare lecție de
formă nouă din jurnal trebuie adăugată ca rescriere în `REWRITES` ca să fie încercată automat. Unealta nu
scrie prima ciornă a unei funcții: pornește de la una aproape potrivită. Teste: `tools/test_permute.py`.

**`tools/gen_poly_placements.py` — layout de clasă din ce scrie callback-ul de plasare.** Pentru clasele
polimorfe al căror `MetaConstruct` doar stochează constante: stocările + membrii reflectați dau membrii clasei
(cei reflectați simpli cu nume și tip, restul `unknownXX` de lățimea stocării). `probe` compilează toate
clasele deschise într-un singur fișier (3 s), `write` ține în `tools/poly_placement_layouts.json` doar clasele
identice care sunt frunze și nu au constructor propriu, `publish` scrie `gen/PolyPlacementCallbacks.cpp` cu
revendicările verificate pe definițiile reale din `BinClasses.h`. Ordinea unei runde:
`write` → `gen_sources.py BinClasses.h` → `publish` → `gen_sources.py` pentru shard-urile Small atinse și
`MetaFunctions.cpp` → audit.

**Cache și paralelism la compilare (`match_func.compile_cached`, `compile_many`).** Un obiect este refolosit
când nimic din ce citește compilarea nu s-a schimbat: sursa, headerele proiectului incluse (urmărite recursiv,
fără evaluarea condițiilor de preprocesor, deci mulțimea poate fi doar prea mare), opțiunile și compilatorul;
hash-ul stă lângă obiect în `<obiect>.dep`. `progress.py` compilează toate perechile (sursă, opțiuni) în
paralel prin acest cache, apoi compară ca înainte. `MATCH_NO_CACHE=1` forțează recompilarea. Comparația cu
clientul se face de fiecare dată, pentru toate revendicările: numai compilarea este sărită.
