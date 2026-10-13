# Căutare de reconstrucție — prototip izolat, 2026-10-09

Experimentul nu publică surse, aliasuri sau layout-uri în reconstrucție.
Candidații C++, obiectele, rapoartele și baza SQLite sunt numai aici. `M.sources()`
nu include acest director. Matcherul, generatoarele și regulile sale de acceptare
nu sunt modificate de experiment.

Prototipul compilează ipoteze cu MSVC, compară întregul corp și verifică separat
toate relocările. Maximum 16 încercări per caz. Eșecurile sunt clasificate, iar
rezultatele persistente ordonează regulile cunoscute de propunere. Cheia cache-ului
include sursa, flags, compilatorul, motorul, imaginea și intrările producției.
Un rezultat parțial nu este acceptat. Nu se injectează cod mașină sau assembly.

## Ce s-a măsurat

| Caz | Acoperire înainte | Prima căutare | Rezultat | Repetare |
|---|---|---:|---|---:|
| Constructor owned-string 0x9b78e0 | Funcție deja reconstruită; control | 2 compilări | 72/88 → 88/88, lambda prin valoare | 0 compilări |
| Helper 0xa64c90 | Fără revendicare în producție | 3 compilări | Tablou cu 1/2/3 pointeri: 12/53, 77/79, **79/79** | 0 compilări; 2 ipoteze în loc de 3 |
| Ceas 0xa2c930 | Fără revendicare; holdout independent | 5 compilări | **38/46**, fără îmbunătățire | 0 compilări |

Rapoarte: `runs/owned-first/report.json`, `runs/probability-first/report.json`,
`runs/clock-holdout/report.json` și variantele `*-replay`.

Constructorul oferă un control cu soluție cunoscută anterior. În cazul tabloului,
layout-ul obiectului de 32 bytes și ipoteza de ownership provin din analiza
metadatelor; motorul caută dimensiunea tabloului. Nu a inventat de la zero aceste
semantici. Cazul ceasului este furnizat separat, cu seed neschimbat și fingerprint
verificat. Rezultatele sale sunt excluse din actualizarea priorităților de căutare.

Memoria eșecurilor economisește recompilarea și poate reordona ipotezele dintr-o
familie cunoscută. Aceste trei cazuri nu demonstrează transfer general: holdout-ul
rămâne nesoluționat. Nu putem deduce din ele un procent automatizabil din întregul
executabil sau timpul până la 100%.

## Reproducere

Din rădăcina proiectului:

```powershell
python experiments/reconstruction_search/search.py experiments/reconstruction_search/cases/owned_case.json --run-dir experiments/reconstruction_search/runs/owned-replay --history experiments/reconstruction_search/runs/measured-v1.sqlite3
python experiments/reconstruction_search/search.py experiments/reconstruction_search/cases/probability_case.json --run-dir experiments/reconstruction_search/runs/probability-replay --history experiments/reconstruction_search/runs/measured-v1.sqlite3
python experiments/reconstruction_search/search.py experiments/reconstruction_search/cases/clock_case.json --run-dir experiments/reconstruction_search/runs/clock-replay --history experiments/reconstruction_search/runs/measured-v1.sqlite3
python -m unittest discover -s experiments/reconstruction_search -p test_search.py
```

Folosiți un alt `--history` din acest director pentru un istoric nou. Seed-urile
nu conțin sursa câștigătoare. Domeniul ipotezelor și constrângerile sunt explicite
în fiecare JSON; în prezent sunt capturi lambda, temporare ale unei expresii și
o singură dimensiune de tablou. Motorul nu generează C++ pentru funcții arbitrare.

## Verificare de izolare

Fiecare rulare verifică fingerprint-urile producției, lista surselor și inventarul
bindings înainte/după. Obiectele sunt scrise într-un director local al rulării,
prin configurarea temporară și restaurată a destinației compilatorului.
Cele șase teste acoperă limitele și dimensiunea completă a corpului C++, păstrarea parametrilor reference,
excluderea holdout-ului din antrenare, respingerea țintelor greșite și refuzul
scrierii artefactelor în producție.

Auditul complet care a însoțit experimentul este
`client-src/progress-2026-10-09-search-isolation-audit.json`:
**21.105 funcții / 3.017.924 bytes / 18,95%, 536 eșecuri**. Cele 3.986 amprente și
lista de surse au rămas neschimbate. Acest audit a identificat 39 bindings noi de
metadate din lotul normal de reconstrucție anterior înghețării; experimentul nu
le-a creat și nu le-a reparat. Nu se pretinde absența regresiilor în acel lot.
Auditul ulterior `progress-2026-10-09-search-isolation-after-audit.json` este
identic integral cu primul, inclusiv toate cele 536 de eșecuri. Raportul de
izolare este `runs/isolation_audit.json`: zero intrări schimbate, aceeași listă
de surse. Niciun candidat experimental nu a fost publicat.

Bundle-ul `vfx_candidate/` conține o a doua experiență de layout/lifetime:
12 corpuri, 808 bytes, verificate separat. Rămâne izolat și nu este introdus în
scor. Constructorii acelor layout-uri nu sunt încă demonstrați.
