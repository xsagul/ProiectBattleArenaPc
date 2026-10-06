# Clientul din afara meciului (lobby.exe), după clientul 14.1

## Sursa

Clientul League din afara meciului (LCU) e o aplicație web: pluginuri `rcp-fe-*` (pagini, stiluri, poze, sunete,
texte) și `rcp-be-*` (servicii). Fișierele pluginurilor patch-ului 14.1 sunt arhivate de CommunityDragon
(`https://raw.communitydragon.org/14.1/plugins/`); `tools/cdragon_lcu.py` le descarcă în `lcu-data/14.1/plugins/`, în
aceeași structură în care clientul le servește (`/fe/<plugin>/...`, `/lol-game-data/assets/...`). Descărcate (~124 MB):
champ-select, parties, navigation, uikit, typekit (fonturile Beaufort/Spiegel), social, shared-components, startup, l10n,
plugin-runner, lock-and-load, skins-picker, audio, kickout, plus din `rcp-be-lol-game-data` datele și pozele celor 5
campioni (`champion-summary.json`, `champions/<id>.json`, iconițe, splash-uri, replici la alegere).

**Paginile:** fiecare componentă Ember își are layout-ul (.hbs) compilat în scriptul pluginului, ca date.
`tools/lcu_templates.py <plugin>` le scrie înapoi ca text în `data/lcu141/templates/<plugin>/` (60 pentru
champ-select, 119 parties, 65 navigation, 39 social, 76 shared-components). Clasele de stare ale fiecărei componente
(`classNameBindings`) se citesc din același script.

**Regula:** stilurile, fonturile, pozele, sunetele, textele și structura elementelor sunt ale clientului; codul care le
umple și le mișcă (`lobby/www/champ-select.js`) e al nostru. Nu rulăm scripturile Riot (ar cere emularea serviciilor
clientului, ca LeagueSandbox; vezi CERCETARE.md).

## Ce e făcut (2026-10-03)

- `lobby.exe` servește fișierele clientului la adresele lui, plus `/lol/me` (numele contului Windows), `/lol/champions`
  (doar campionii pentru care serverul are script), `/lol/start`. Se deschide ca fereastră de aplicație (Edge
  `--app`, 1280 x 720, profil separat în `lobby_profile`), conținutul scalat ca la client.
- **Champion select** (`champ-select.js`), după layout-urile `layout.hbs`, `summoner-array`, `summoner-object`,
  `timer-status`, `pick-phase`, `champion-grid`, `champion-grid-champion`, `lock-in-button`, `action-button`,
  `champion-splash-background`, `skin-name`: mesajele timer-ului din `trans.json`, grila cu celulele 101 x 96 ale
  clientului, reticulul de selecție, splash-ul în spate, Lock In, faza de finalizare, sunetele clientului și replica
  campionului la blocare; apoi pornește meciul și revine când se închide jocul. Rulează ca clientul cu „large area
  animations” oprite (modul low spec).

## Ce lipsește

- **Logarea.** În 14.1 logarea nu e în clientul League: e în Riot Client (aplicație separată, fără versiune 14.1 în
  nicio arhivă pe care o avem). De hotărât cu utilizatorul.
- **Ecranele dinainte de champion select:** pagina principală + bara de navigare (rcp-fe-lol-navigation), alegerea
  modului și lobby-ul (rcp-fe-lol-parties: Training → Practice Tool → Confirm → lobby → Start Game), ready check.
- În champion select: runele, vrăjile de summoner, skin-urile (loadouts-edit, skin-select), chat-ul, echipa adversă,
  ban-urile, filtrele pe poziții (cer listele serviciului de statistici), videoclipurile (animațiile mari), muzica.
- **Duratele fazelor** (pick, finalizare) vin de la serverele Riot și nu sunt în niciun fișier: 90 s și 10 s sunt puse
  provizoriu (**de măsurat**).
- Ecranul de după meci (rcp-fe-lol-postgame, nedescărcat).
