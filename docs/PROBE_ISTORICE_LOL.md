# Probe istorice LoL â€” verificare 2026-10-09

Pachetul utilizatorului din `C:/Users/Sorin/Desktop/probe_istorice_lol` este o
sursÄƒ de simboluri È™i de ancore semantice pentru reconstrucÈ›ia actualÄƒ.
FiÈ™ierele originale au fost doar citite; executabilele jocului nu au fost rulate.

## Identitatea pachetului

| FiÈ™ier | Identitate din PE | Timestamp COFF UTC | Simboluri disponibile |
|---|---|---|---|
| client 1.31/League of Legends.exe | 1.0.0.131, PUBLIC | 2011-12-19 21:50:43 | RTTI È™i È™iruri; PDB local absent |
| client1.32/League of Legends.exe | 1.0.0.132, PUBLIC | 2012-01-16 19:00:35 | RTTI È™i È™iruri; PDB local absent |
| RiotLOL_Client_AB.exe | 1.0.0.961, RELEASE_AB | 2011-10-13 00:12:52 | RiotLOL_Client_AB.pdb, verificat |

Timestamp-urile sunt informaÈ›ii din header, fÄƒrÄƒ a stabili data publicÄƒrii.
Toate cele trei executabile sunt x86, image base 0x400000, linker 8.0.
Èšinta reconstrucÈ›iei foloseÈ™te altÄƒ imagine È™i alt toolchain; acestea sunt
build-uri istorice, nu patch-urile 13.1/13.2.

EXE AB È™i PDB au GUID **1bbbdd37-bc5e-4ff9-9920-ce5c5aad9a40**, age **1**.
SHA256 PDB: `a5b4b4ed32b80807c41a404111d9aac633db0eb6a1c94f83b1c8db7fbd7bcfca`.
PDB-ul are 83.979.264 bytes. Aplicarea lui la EXE 1.0.0.132 este respinsÄƒ Ã®nainte
scrierii rezultatelor, deoarece GUID-ul nu corespunde.

## Ce a fost extras efectiv

`tools/historical_pdb.py` citeÈ™te MSF7 È™i subseturi de CodeView, conform
[formatului documentat de LLVM](https://llvm.org/docs/PDB/index.html).
ExportÄƒ Ã®n `client-src/obj/historical-lol/`, fÄƒrÄƒ modificÄƒri de registry/DIA.
Parserul nativ Ghidra a constatat lipsa Ã®nregistrÄƒrii DIA; nu s-au fÄƒcut schimbÄƒri
Ã®n registry pentru a-l porni.

- 68.122 simboluri publice, inclusiv 40.627 marcate Function;
- 284.154 Ã®nregistrÄƒri de tipuri;
- 37.352 Ã®nregistrÄƒri class/struct/union, dintre care 17.994 fÄƒrÄƒ flag forward;
- 3.592 cÄƒi de fiÈ™iere sursÄƒ;
- 68.119 simboluri cu RVA mapabil prin secÈ›iunile PE; OMAP absent.

Numerele includ runtime, biblioteci, È™abloane È™i nume folded la aceeaÈ™i adresÄƒ.
CÄƒile cÄƒtre `.cpp/.h` nu includ conÈ›inutul original al surselor. Cititorul nu
pretinde implementarea Ã®ntregului format PDB. Listele de cÃ¢mpuri decodeazÄƒ
membrii cu offset È™i bazele; Ã®nregistrÄƒrile metodelor/static sunt traversate,
nu reconstruite ca sursÄƒ. Un leaf necunoscut respinge lista, fÄƒrÄƒ offseturi ghicite.

ComandÄƒ reproductibilÄƒ:

```powershell
python tools/historical_pdb.py 'C:/Users/Sorin/Desktop/probe_istorice_lol/RiotLOL_Client_AB.pdb' 'C:/Users/Sorin/Desktop/probe_istorice_lol/RiotLOL_Client_AB.exe' --out client-src/obj/historical-lol --query 'ParticleSystem::ValueVector3' --query 'FlexType<float>' --query Probability
```

## Pilot VFX È™i rezultat modern

ExistÄƒ 23 Ã®nregistrÄƒri complete care au 20 nume scurte comune cu metadatele
actuale. Acestea sunt candidaÈ›i nominali: namespace-urile È™i mÄƒrimile pot diferi,
iar RigResource are douÄƒ variante istorice distincte. Familia VFX este verificatÄƒ
mai profund prin cÃ¢mpuri, destructor È™i funcÈ›ii de evaluare.

| Concept | Layout istoric PDB | Layout modern verificat |
|---|---|---|
| ValueVector3 | 68 bytes; constantÄƒ, ramp pointer, flags, vectors È™i 3 probability pointers inline | 16 bytes; constantÄƒ È™i pointer cÄƒtre dynamics |
| Flex<ValueVector3> | 76 bytes, include flag de prezenÈ›Äƒ | 20 bytes |
| ProbabilityTable | 52 bytes; single/flat flags, valori È™i douÄƒ std::vectors de 16 bytes | 32 bytes; douÄƒ buffers de 12 bytes, singleValue È™i douÄƒ bool |

Treisprezece funcÈ›ii publice ale familiei ValueVector3 au adrese validate È™i
instrucÈ›iuni exportate. Codul vechi construieÈ™te o rampÄƒ de 256 vectori,
interpolaÈ›ie liniarÄƒ È™i aplicÄƒ trei tabele de probabilitate separat. Codul de
transport vechi este ENet; nu existÄƒ Ã®ncÄƒ dovadÄƒ pentru transfer Ã®n LNP modern.
ABI-ul privat AB foloseÈ™te inclusiv EDI/ESI È™i return float Ã®n XMM0; decorarea
thiscall din nume nu poate fi aplicatÄƒ direct unui alias modern.

**Prim rezultat ghidat de aceste ancore:** MetaVirtual2<VfxProbabilityTableData>,
RVA modern **0xa581b0**, are sursÄƒ C++ cu **93/93 bytes** È™i toate cele patru
relocÄƒri float exact verificate. Single flag = count(keys)==0. Flat flag cere
exact douÄƒ chei, prima Ã®n jurul lui 0 È™i a doua Ã®n jurul lui 1, cu toleranÈ›ele
float concrete din client: +/-1e-6, 1.0000009536743164 È™i 0.9999989867210388.
Un Vector2 local cu cele douÄƒ chei reproduce Ã®ncÄƒrcÄƒrile/SSE È™i ordinea exactÄƒ;
formele cu citiri individuale aveau numai 79/93 bytes.

Acest callback este integrat Ã®n generatorul normal `gen_vfx_runtime.py`, care
verificÄƒ acum 24 corpuri / 1.536 bytes. Prototipul de cÄƒutare rÄƒmÃ¢ne separat.
Rezultatele funcÈ›iei vechi sunt folosite pentru ipoteze; acceptarea sursei
moderne rÄƒmÃ¢ne comparaÈ›ia Ã®ntregului corp, ABI-ului È™i È›intelor, apoi auditul complet.

## Resurse È™i urmÄƒtoarele ancore

Folderul 1.31 are 25.709 fiÈ™iere (2,696 GB), iar 1.32 1.117 (109,8 MB); al doilea
pare o delta, nu o instalare completÄƒ. Toate cele 2.720 Luaobj se parseazÄƒ Lua 5.1.
BuildingBlocksBase pÄƒstreazÄƒ 57 globale scrise È™i 32 citite comune cu scriptul
actual, extrase din instrucÈ›iuni GETGLOBAL/SETGLOBAL. Acestea includ È™i biblioteci
Lua generice. Headerul actual are size_t64, cel istoric size_t32; bloburile nu
sunt identice. Pentru gameplay, ancore concrete sunt GetArmor, GetSpellBlock,
GetTotalAttackDamage, GetTime, SpellBuffAdd/Remove È™i SetSpellCastRange.

Dovezi: inventory.json, pdb-summary.json, publics.json, types.json,
selected-fields.json, source-files.json, shared-metadata-types.json,
valuevector3_analysis.md È™i clients_resources_report.md, Ã®n directorul de raport.
Acest inventar nu demonstreazÄƒ o proporÈ›ie automatizabilÄƒ sau un termen pÃ¢nÄƒ la100%.
