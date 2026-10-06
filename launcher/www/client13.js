// The out-of-game client after League Client 13.3. The element trees are the client's own page layouts
// (data/lcu133/templates/<plugin>/*.hbs), the choices those layouts make are the ones in the client's plugin code
// (cited per function), the pictures / texts / sounds are the client's files. This file is this project's code; no Riot
// script runs. What the installation cannot play yet stays on the page as the client shows an unavailable choice.
'use strict';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const el = (html) => { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; };
const play = (src, volume = 0.5) => uikitSound(src, volume);

// Queues this installation can start (our game server: Summoner's Rift, 13.3). Everything else is shown, unavailable.
const PLAYABLE_QUEUES = new Set([400, 420, 430, 440]);

// rcp-fe-lol-parties: CATEGORIES_DISPLAY_ORDER {primary: PvP, VersusAi, Training; secondary: CreateCustom, JoinCustom}
const CATEGORIES = { primary: ['PvP', 'VersusAi', 'Training'], secondary: ['CreateCustom', 'JoinCustom'] };
// The game types per category and the queues on each. Which queues a 13.3 server offered is server data, not in the
// client's files: this list is the one agreed for this project [to verify against a 13.3 screenshot]. The game type
// order is the client's (_sortGameTypes: CLASSIC, ARAM, TFT, then the rest; the PvP list ends with the disabled
// rotating-mode card DISABLED_RGM_GAME_TYPE when no rotating mode is live); Training is TUTORIAL_GAME_TYPES.
const GAME_TYPES = {
  PvP: [
    { mapId: 11, gameMode: 'CLASSIC', queues: [400, 420, 440, 430] },
    { mapId: 12, gameMode: 'ARAM', queues: [450] },
    { mapId: 22, gameMode: 'TFT', queues: [1090, 1100, 1130, 1160] },
    { mapId: 11, gameMode: 'LCURGMDISABLED', queues: [], disabledRgm: true },
  ],
  VersusAi: [{ mapId: 11, gameMode: 'CLASSIC', queues: [830, 840, 850] }],
  Training: [
    { mapId: 11, gameMode: 'TUTORIAL_FLOW', queues: [2000, 2010, 2020], training: true },
    { mapId: 11, gameMode: 'PRACTICETOOL', queues: [], training: true },
  ],
};
// rcp-fe-lol-parties TUTORIAL_ASSETS (training cards use the plugin's own pictures)
const TUTORIAL_ASSETS = {
  TUTORIAL_FLOW: 'battletraining',
  PRACTICETOOL: 'practicetool',
};

const S = {
  tra: {},           // parties + l10n + navigation texts
  queues: {},        // game data queues.json
  maps: {},          // game data map-assets.json
  champions: [],
  me: { name: 'Player' },
  nav: 'home',       // the navigation item shown: home / parties
  partiesState: 'gameSelect',   // gameSelect / party
  category: 'PvP',
  selected: { mapId: 11, gameMode: 'CLASSIC', queueId: 400 },
  positions: ['UNSELECTED', 'UNSELECTED'],   // primary, secondary (lobby position preferences)
  positionModal: null,
  inQueue: false,
  readyCheck: null,  // null / in-progress / accepted / declined
  screen: 'client',  // client (navigation + screens) / champSelect (full screen)
  csTra: {},
};
const t = (k) => S.tra[k] ?? k;

async function loadData() {
  const j = async (u) => { const r = await fetch(u); if (!r.ok) throw new Error(u); return r.json(); };
  const [parties, l10n, nav, queues, maps, champions, me, cs] = await Promise.all([
    j('/fe/lol-parties/trans.json'), j('/fe/lol-l10n/trans.json'), j('/fe/lol-navigation/trans.json'),
    j('/lol-game-data/assets/v1/queues.json'), j('/lol-game-data/assets/v1/map-assets/map-assets.json'),
    j('/lol/champions'), j('/lol/me'), j('/fe/lol-champ-select/trans.json'),
  ]);
  S.csTra = cs;
  S.tra = { ...l10n, ...nav, ...parties };
  S.queues = queues;
  S.maps = maps;
  S.champions = champions;
  S.me = me;
}

// ---------------------------------------------------------------------------------------------------------------
// navigation (rcp-fe-lol-navigation: application.hbs > navbar_backdrop > patcher-and-play-button + navigation-root)

// menu items as the plugins register them (priority sorts; left items show text, right items their icon in the
// default NavBarDisplayMode ICONS): Home 1, TFT 400 (disabled), Clash 1500 / Profile 20, Collection 30, Loot 40 (disabled),
// Store 60 (disabled). Pages we do not have stay disabled.
const NAV_ITEMS = [
  { id: 'home', key: 'navbar_home', priority: 1, alignment: 'left' },
  { id: 'tft', key: 'navbar_tft', priority: 400, alignment: 'left', disabled: true },
  { id: 'clash', key: 'navbar_competitive', priority: 1500, alignment: 'left', disabled: true },
  { id: 'profile', key: 'navbar_profile', priority: 20, alignment: 'right', icon: 'nav-icon-profile.svg', disabled: true },
  { id: 'collections', key: 'navbar_collection', priority: 30, alignment: 'right', icon: 'nav-icon-collections.svg', disabled: true },
  { id: 'loot', key: 'navbar_loot', priority: 40, alignment: 'right', icon: 'nav-icon-loot.svg', disabled: true },
  { id: 'store', key: 'navbar_store', priority: 60, alignment: 'right', icon: 'nav-icon-store.svg', disabled: true },
];

function menuItem(item) {   // templates.components.menu-item.hbs (tagName lol-uikit-navigation-item)
  const active = S.nav === item.id;
  const inner = item.icon
    ? `<div class="menu-item-icon-wrapper"><div class="menu-item-icon" style="-webkit-mask-image: url(/fe/lol-static-assets/images/${item.icon})"></div></div>`
    : esc(t(item.key));
  const node = el(`<lol-uikit-navigation-item class="main-navigation-menu-item menu_item_${item.key} ember-view"
      ${active ? 'active="true"' : ''} ${item.disabled ? 'disabled="true"' : ''} title="${item.icon ? esc(t(item.key)) : ''}">${inner}</lol-uikit-navigation-item>`);
  node.addEventListener('click', () => {
    if (item.disabled || active) return;
    S.nav = item.id;
    render();
  });
  return node;
}

function playButton() {
  // patcher-basic-button.hbs; images / sounds of patcher-play-button (playImages / lobbyImages, playSounds / lobbySounds);
  // isLobbyBtn = a lobby exists (playButton.isLobbyOrTournament): PARTY with the lobby images, else PLAY
  const lobby = S.partiesState === 'party';
  const images = lobby
    ? { default: 'play-button-lobby-default.png', hover: 'play-button-lobby-hover.png' }
    : { default: 'play-button-default.png', hover: 'play-button-hover.png' };
  const sounds = lobby
    ? { click: 'sfx-nav-button-lobby-click.ogg', hover: 'sfx-nav-button-lobby-hover.ogg' }
    : { click: 'sfx-nav-button-play-click.ogg', hover: 'sfx-nav-button-play-hover.ogg' };
  const img = (k) => `background-image: url('/fe/lol-static-assets/images/${images[k]}')`;
  const node = el(`<div class="patcher-and-play-button ember-view"><div class="play-button-component patcher-play-button enabled ember-view">
    <div class="basic-button ${lobby ? 'lobby' : 'play'} ember-view">
      <div class="play-button-frame" data-is-logged-in="true" data-is-not-patching="true" data-patcher-state="idle"></div>
      <div class="play-button-container" style="${img('default')}">
        <div class="league-client-logo ember-view">
          <div class="league-logo"><video autoplay loop muted src="/fe/lol-static-assets/videos/league-logo-loop-idle.webm"></video></div>
        </div>
        <div class="play-button-content"><span class="play-button-text">${esc(t(lobby ? 'navbar_button_lobby' : 'navbar_button_play'))}</span></div>
      </div>
    </div></div></div>`);
  const container = node.querySelector('.play-button-container');
  const content = node.querySelector('.play-button-content');
  content.addEventListener('mouseenter', () => { container.style.cssText = img('hover'); play('/fe/lol-static-assets/sounds/' + sounds.hover); });
  content.addEventListener('mouseleave', () => { container.style.cssText = img('default'); });
  content.addEventListener('click', () => {
    play('/fe/lol-static-assets/sounds/' + sounds.click);
    if (S.nav !== 'parties') { S.nav = 'parties'; render(); }
  });
  return node;
}

function navigation() {
  const root = el(`<div id="rcp-fe-lol-navigation-app" class="ember-view rcp-fe-lol-navigation-app navbar_backdrop"></div>`);
  root.appendChild(playButton());
  const nr = el(`<div class="navigation-root-component ember-view"></div>`);
  const bar = el(`<lol-uikit-navigation-bar class="rcp-fe-lol-navigation main-nav-bar ember-view" type="nav-bar">
      <div class="left-nav-menu"></div>
      <div class="right-nav-menu"><div class="right-nav-vertical-rule"></div><div class="wallet-and-badges">
        <div class="currency-container-stacked ember-view">
          <div class="currency-rp">0</div>
          <div class="currency-be"><div class="currency-be-component ember-view"><div class="currency-be-icon-container"><div class="currency-be-icon-static"></div></div>0</div></div>
        </div></div></div>
    </lol-uikit-navigation-bar>`);
  const sorted = [...NAV_ITEMS].sort((a, b) => a.priority - b.priority);
  for (const it of sorted.filter((i) => i.alignment === 'left')) bar.querySelector('.left-nav-menu').appendChild(menuItem(it));
  const right = bar.querySelector('.right-nav-menu');
  for (const it of sorted.filter((i) => i.alignment === 'right')) right.insertBefore(menuItem(it), right.querySelector('.right-nav-vertical-rule'));
  nr.appendChild(bar);
  root.appendChild(nr);
  return root;
}

// ---------------------------------------------------------------------------------------------------------------
// parties: game select (components/game-select/*)

function mapAsset(mapId, gameMode, mutator = '') {
  // assets.getMap(mapId, gameMode, mutator) over map-assets.json
  const list = S.maps[String(mapId)] || [];
  return list.find((m) => m.gameMode === gameMode && (m.gameMutator || '') === (mutator || '')) ||
    list.find((m) => m.gameMode === gameMode) || null;
}
const assetUrl = (gt, key) => {
  if (gt.training) {
    const a = TUTORIAL_ASSETS[gt.gameMode];
    const file = { 'game-select-icon-default': 'default', 'game-select-icon-hover': 'hover', 'game-select-icon-disabled': 'disabled', 'icon-victory': 'icon-victory', 'game-select-icon-active': 'active' }[key];
    return `/fe/lol-parties/${a}-${file}.png`;
  }
  const m = mapAsset(gt.mapId, gt.gameMode, gt.assetMutator);
  return m && m.assets && m.assets[key] ? '/' + m.assets[key] : '';
};
const queueOk = (q) => PLAYABLE_QUEUES.has(q);
const gameTypeOk = (gt) => !gt.disabledRgm && gt.queues.some(queueOk);

function gameTypeName(gt) {   // game-type-card gameTypeName
  let name;
  if (S.category === 'PvP') { const m = mapAsset(gt.mapId, gt.gameMode, gt.assetMutator); name = m && m.gameModeName; }
  return name || t(`game_select_game_type_name_${gt.mapId}_${gt.gameMode.toLowerCase()}`);
}
function gameTypeDescription(gt) {   // game-type-card gameTypeDescription
  let d;
  if (S.category === 'PvP') { const m = mapAsset(gt.mapId, gt.gameMode, gt.assetMutator); d = m && m.gameModeDescription; }
  if (!d) {
    if (gt.disabledRgm) return '';
    d = t(`game_select_category_description_${S.category.toLowerCase()}_${gt.mapId}_${gt.gameMode.toLowerCase()}`);
  }
  return d;
}
function mapVersus(gt) {   // game-type-card mapVersus
  if (gt.gameMode === 'TFT') return t('game_select_team_size_free_for_all_acronym');
  if (gt.training || gt.disabledRgm) return '';
  const q = S.queues[String(gt.queues[0])];
  const size = q && q.numPlayersPerTeam ? q.numPlayersPerTeam : 5;   // [5 when queues.json has no team size]
  return t('game_select_team_size').replaceAll('{{size}}', size);
}

function categorySelect() {   // category-select-component (+ category-component, tagName lol-uikit-navigation-item)
  const all = [...CATEGORIES.primary, ...CATEGORIES.secondary];
  const node = el(`<div class="parties-game-navs ember-view">
    <lol-uikit-navigation-bar selectedindex="${CATEGORIES.primary.indexOf(S.category)}" type="nav-bar-secondary" class="parties-game-navs-list"></lol-uikit-navigation-bar>
  </div>`);
  const bar = node.firstElementChild;
  for (const c of all) {
    if (c === CATEGORIES.secondary[0]) bar.appendChild(el('<span class="parties-game-navs-break"></span>'));
    const disabled = CATEGORIES.secondary.includes(c);
    const it = el(`<lol-uikit-navigation-item class="parties-game-navs-item ember-view" ${disabled ? 'disabled="true"' : ''}
        ${disabled ? `title="${esc(t('game_select_category_nav_not_available'))}"` : ''}>${esc(t('parties_game_category_' + c.toLowerCase()))}</lol-uikit-navigation-item>`);
    if (!disabled) it.addEventListener('click', () => {
      if (S.category === c) return;
      S.category = c;
      const first = GAME_TYPES[c].find(gameTypeOk);
      S.selected = first ? { mapId: first.mapId, gameMode: first.gameMode, queueId: first.queues.find(queueOk) } : { mapId: null, gameMode: null, queueId: null };
      render();
    });
    bar.appendChild(it);
  }
  return node;
}

function gameTypeCard(gt) {   // game-type-card + game-type-icon + game-type-category
  const ok = gameTypeOk(gt);
  const selected = ok && S.selected.mapId === gt.mapId && S.selected.gameMode === gt.gameMode;
  const versus = mapVersus(gt);
  const node = el(`<div class="game-type-card ember-view ${selected ? 'selected' : ''} ${ok ? '' : 'disabled'}">
    <div class="parties-game-type-upper-half">
      <div class="parties-game-type-icon map-${gt.mapId} ember-view">
        <div class="parties-game-type-card-selected-glow"></div>
        <div class="icon-frame">
          <div class="icon-bg icon-bg-default" style="background-image: url('${assetUrl(gt, 'game-select-icon-default')}');"></div>
          <div class="icon-bg icon-bg-hover" style="background-image: url('${assetUrl(gt, 'game-select-icon-hover')}');"></div>
          <div class="icon-bg icon-bg-disabled" style="background-image: url('${assetUrl(gt, 'game-select-icon-disabled')}');"></div>
          <div class="icon-bg icon-bg-active" style="background-image: url('${assetUrl(gt, 'icon-victory')}');"></div>
        </div>
        <div class="parties-game-type-card-break ${gt.disabledRgm ? 'parties-disabled-featured-game-mode-break' : ''}">${esc(versus)}</div>
        <div class="parties-game-type-card-name">${esc(gameTypeName(gt))}</div>
      </div>
      ${ok ? '' : `<div class="parties-eligibility-error" title="${esc(t('game_select_queue_restriction_party_queuedisabled'))}"></div>`}
    </div>
    <div class="parties-game-type-lower-half">
      <div class="parties-game-type-card-intro">${esc(gameTypeDescription(gt))}</div>
    </div>
  </div>`);
  // shouldDisplayQueueSelect: not disabled and not training
  if (ok && !gt.training) {
    const lower = node.querySelector('.parties-game-type-lower-half');
    lower.appendChild(el('<hr>'));
    const list = el('<lol-uikit-scrollable class="parties-game-type-card-categories"></lol-uikit-scrollable>');
    for (const q of gt.queues) {
      const qd = S.queues[String(q)] || {};
      const cur = selected && S.selected.queueId === q;
      const dis = !queueOk(q);
      const row = el(`<div class="parties-game-type-card-category-div ember-view ${cur ? 'selected' : ''} ${dis ? 'disabled' : ''}">
        <div class="parties-game-type-card-category-radio-option"></div>
        <div class="queue-eligibility-error queue-status-icon ${dis ? 'queue-status-icon-visible' : ''}" title="${dis ? esc(t('game_select_queue_restriction_party_queuedisabled')) : ''}"></div>
        <div class="solo-rewards-icon queue-status-icon"></div>
        <div data-queue-id="${q}" class="${cur ? 'current' : ''} ${dis ? 'disabled' : ''} parties-game-type-card-category-btn">${esc(qd.description || q)}</div>
      </div>`);
      row.addEventListener('click', () => {
        if (!selected || cur || dis) return;
        S.selected.queueId = q;
        play('/fe/lol-uikit/sfx-uikit-radio-click.ogg');
        render();
      });
      list.appendChild(row);
    }
    lower.appendChild(list);
  }
  node.querySelector('.parties-game-type-upper-half').addEventListener('click', () => {
    if (!ok) { play('/fe/lol-uikit/sfx-uikit-button-locked-click.ogg'); return; }
    if (selected) return;
    play('/fe/lol-parties/sfx-gameselect-button-map-click.ogg');
    S.selected = { mapId: gt.mapId, gameMode: gt.gameMode, queueId: gt.queues.find(queueOk) };
    render();
  });
  node.querySelector('.parties-game-type-upper-half').addEventListener('mouseenter', () => {
    if (ok && !selected) play('/lol-game-data/assets/content/src/LeagueClient/GameModeAssets/Shared/sound/sfx-gameselect-button-hover.ogg');
  });
  return node;
}

function arrowFooter({ confirmText, confirmDisabled, onConfirm, onClose, sounds }) {   // lib.arrow-footer
  const node = el(`<div class="arrow-footer ember-view" version="7.13">
    <div class="arrow-footer-decoration"><div class="arrow-footer-decoration-child arrow-footer-decoration-left"></div></div>
    <div class="confirm-button-container">
      <div class="border-bg"><div class="left-border-bg"></div><div class="middle-border-bg"></div><div class="right-border-bg"></div></div>
      <button class="confirm ${confirmDisabled ? 'disabled' : ''}">
        <lol-uikit-animated-arrow-overlay state="click" single-carot=""></lol-uikit-animated-arrow-overlay>
        <div class="left-confirm"></div><div class="middle-confirm">${esc(confirmText)}</div><div class="right-confirm"></div>
      </button>
      <button class="close" type="back"><div class="close-icon"></div></button>
    </div>
    <div class="arrow-footer-decoration"><div class="arrow-footer-decoration-child arrow-footer-decoration-right"></div></div>
  </div>`);
  const confirm = node.querySelector('.confirm');
  const close = node.querySelector('.close');
  confirm.addEventListener('mouseenter', () => { if (!confirmDisabled && sounds.confirmHover) play(sounds.confirmHover); });
  confirm.addEventListener('click', () => { if (confirmDisabled) return; if (sounds.confirmClick) play(sounds.confirmClick); onConfirm(); });
  close.addEventListener('mouseenter', () => { if (sounds.closeHover) play(sounds.closeHover); });
  close.addEventListener('click', () => { if (sounds.closeClick) play(sounds.closeClick); onClose(); });
  return node;
}

function gameSelect() {   // game-select-root-component
  const node = el(`<div class="parties-game-select-screen game-select-show ember-view">
    <div class="parties-game-select-wrapper"></div>
    <div class="game-select-footer-container ember-view"></div>
  </div>`);
  const wrap = node.firstElementChild;
  wrap.appendChild(categorySelect());
  const types = el('<div class="parties-game-type-select-wrapper ember-view"><hr></div>');
  for (const gt of GAME_TYPES[S.category]) types.appendChild(gameTypeCard(gt));
  wrap.appendChild(types);
  node.querySelector('.game-select-footer-container').appendChild(arrowFooter({
    confirmText: t('parties_button_confirm'),
    confirmDisabled: !S.selected.queueId || !queueOk(S.selected.queueId),
    onConfirm: () => { S.partiesState = 'party'; render(); },
    onClose: () => { S.nav = 'home'; render(); },
    sounds: {   // game-select footer buttonSounds [the lobby footer's; the game-select footer's own list not yet read]
      confirmClick: '/fe/lol-uikit/sfx-uikit-button-gold-click.ogg',
      confirmHover: '/fe/lol-uikit/sfx-uikit-button-gold-hover.ogg',
    },
  }));
  return node;
}

function parties() {   // root-component.layout.hbs (classNames parties-view)
  const bg = (() => {
    const m = mapAsset(S.selected.mapId || 11, S.selected.gameMode && !S.selected.gameMode.startsWith('LCU') ? S.selected.gameMode : 'CLASSIC');
    return m && m.assets && m.assets['parties-background'] ? '/' + m.assets['parties-background'] : '';
  })();
  const node = el(`<div class="parties-view ember-view">
    <div class="parties-background ember-view">
      <div class="uikit-background-switcher ember-view"><img src="${esc(bg)}" class="lol-uikit-background-switcher-image"></div>
      <div class="parties-background-mask"></div>
    </div>
    <div class="parties-content"></div>
  </div>`);
  const content = node.querySelector('.parties-content');
  if (S.partiesState === 'party') {
    content.appendChild(el('<div class="empty-header-spacer"></div>'));
    content.appendChild(lobby());
    content.appendChild(lobbyHeader());
  } else content.appendChild(gameSelect());
  return node;
}

// ---------------------------------------------------------------------------------------------------------------
// parties: the lobby (components/parties-v2/*; PartiesV2Enabled defaults to true in 13.3's platform config)

// pick type per queue: gameTypeConfig.pickMode -> PICK_TYPES (TeamBuilderDraftPickStrategy draft, SimulPickStrategy
// blind). The queue's pick strategy is server data [known 13.3 values]; showPositionSelector likewise (draft queues).
const QUEUE_PICK = { 400: 'draft', 420: 'draft', 440: 'draft', 430: 'blind', 450: 'blind', 830: 'blind', 840: 'blind', 850: 'blind' };
const POSITIONS = ['TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY'];

function genericButton({ base, over, down, disabled, text, enabled = true, onClick, clickSound, hoverSound, cls = '' }) {
  // generic-button-component: four stacked states (up / over / down / disabled), the current one .active
  const state = (name, img) => `<div class="generic-button-state ${name}" ${name === 'disabled' && !enabled ? '' : ''}>
      <div class="generic-button-primary-img-container">${img ? `<img src="${img}">` : ''}</div>
      ${text ? `<div class="generic-button-text">${esc(text)}</div>` : ''}</div>`;
  const node = el(`<div class="generic-button match-h match-w ember-view ${cls}"><div class="generic-button-root">
      ${state('up', base)}${state('over', over)}${state('down', down)}${state('disabled', disabled)}</div></div>`);
  const root = node.firstElementChild;
  const set = (name) => root.querySelectorAll('.generic-button-state').forEach((n) => n.classList.toggle('active', n.classList.contains(name)));
  set(enabled ? 'up' : 'disabled');
  if (enabled) {
    root.addEventListener('mouseenter', () => { set('over'); if (hoverSound) play(hoverSound); });
    root.addEventListener('mouseleave', () => set('up'));
    root.addEventListener('mousedown', () => set('down'));
    root.addEventListener('mouseup', () => { set('over'); if (clickSound) play(clickSound); if (onClick) onClick(); });
  }
  return node;
}

function lobbyHeader() {   // v2-header-component
  const q = S.queues[String(S.selected.queueId)] || {};
  const m = mapAsset(S.selected.mapId, S.selected.gameMode) || {};
  const pick = QUEUE_PICK[S.selected.queueId];
  const node = el(`<div class="v2-header-component ember-view">
    <div class="lobby-header-overlay"></div>
    <div class="lobby-header-content">
      <div class="lobby-back-button-container">
        <div class="lobby-back-button" title="${esc(t('parties_button_change_mode'))}"></div>
        <div class="lobby-header-vertical-line"></div>
      </div>
      <div class="lobby-header-map-icon ${S.selected.mapId === 11 ? 'game_map_summoners_rift' : S.selected.mapId === 12 ? 'game_map_howling_abyss' : `game_map_${S.selected.mapId}`}"></div>
      <div class="lobby-header-description">
        <div class="lobby-header-detail">${esc(t('map_name_short_' + (m.mapStringId || 'SR')))}</div>
        <div class="lobby-header-separator"></div>
        <div class="lobby-header-detail">${esc(q.shortName || '')}</div>
        ${pick ? `<div class="lobby-header-separator"></div><div class="lobby-header-detail">${esc(t('game_select_pick_type_name_' + pick))}</div>` : ''}
      </div>
      <div class="lobby-header-tooltip"><div class="v2-point-eligibility-component ember-view"><div class="lobby-point-eligibility-content"><div class="point-eligibility-icon"></div></div></div></div>
      <div class="lobby-header-buttons-container"></div>
    </div>
  </div>`);
  node.querySelector('.lobby-back-button').appendChild(genericButton({
    base: '/fe/lol-parties/button-back-arrow.png', over: '/fe/lol-parties/button-back-arrow-over.png',
    down: '/fe/lol-parties/button-back-arrow-down.png', disabled: '/fe/lol-parties/button-back-arrow-disabled.png',
    clickSound: '/fe/lol-uikit/sfx-uikit-button-gold-click.ogg', hoverSound: '/fe/lol-uikit/sfx-uikit-button-gold-hover.ogg',
    onClick: () => { S.partiesState = 'gameSelect'; render(); },
  }));
  return node;
}

function banner(member) {   // v2-banner-component (the local player)
  const showPos = QUEUE_PICK[S.selected.queueId] === 'draft';
  const node = el(`<div class="v2-banner-component challenges-enabled ember-view">
    <div class="lobby-banner local">
      <lol-regalia-parties-v2-element member-type="current-player" summoner-id="1" profile-icon="${member.profileIconId}" summoner-level="${member.summonerLevel}" queue="">
        <div class="lobby-banner-contents">
          <div class="banner-highlight"></div>
          <div class="banner-spacer"></div>
          <div class="player-identity-container"></div>
          <div class="chat-restriction-warning-container"></div>
          <div class="player-details-spacer"></div>
          <div class="player-name-container"><div class="leader-icon"></div><div class="player-name">${esc(member.name)}</div></div>
          <div class="player-achievements-container"></div>
          ${showPos ? `<div class="position-icons-container">
            <div class="position-element secondary"><div class="v2-banner-position-icon-component ember-view"><div class="position-image-container"><img class="position-image" src="/fe/lol-parties/icon-position-banner-secondary-${S.positions[1].toLowerCase()}.png"></div></div></div>
            <div class="position-element primary"><div class="v2-banner-position-icon-component ember-view"><div class="position-image-container"><img class="position-image" src="/fe/lol-parties/icon-position-banner-primary-${S.positions[0].toLowerCase()}.png"></div></div></div>
          </div>` : ''}
          <div class="v2-player-party-controls main-player-controls ember-view"></div>
        </div>
      </lol-regalia-parties-v2-element>
    </div>
  </div>`);
  return node;
}

function bannerPlaceholder() {   // v2-banner-placeholder (invites: shown, not available in this installation)
  const node = el(`<div class="v2-banner-placeholder ember-view"><div class="invite-button-container"><div class="invite-button"></div></div></div>`);
  node.querySelector('.invite-button').appendChild(genericButton({
    base: '/fe/lol-parties/banner-invite.png', over: '/fe/lol-parties/banner-invite-hover.png', down: '/fe/lol-parties/banner-invite-click.png',
    onClick: () => play('/fe/lol-uikit/sfx-uikit-button-locked-click.ogg'),
  }));
  return node;
}

function positionSelector() {   // v2-position-selector + v2-position-selector-button
  const node = el(`<div class="v2-position-selector-component ember-view"><div class="position-selector-buttons-container"></div></div>`);
  const box = node.firstElementChild;
  ['PRIMARY', 'SECONDARY'].forEach((ordinal, i) => {
    const pos = S.positions[i];
    const hidden = ordinal === 'SECONDARY' && S.positions[0] === 'FILL';
    const b = el(`<div class="position-selector-button ${ordinal} ${pos} ${hidden ? 'hidden' : ''} ember-view">
      <div class="position-selector-button-background"><img class="position-image" src="/fe/lol-parties/icon-position-button-${pos.toLowerCase()}.png"></div>
    </div>`);
    const bg = b.querySelector('.position-selector-button-background');
    bg.addEventListener('mouseenter', () => play('/fe/lol-uikit/sfx-uikit-button-gold-hover.ogg'));
    bg.addEventListener('mousedown', () => { S.positionModal = ordinal; render(); });
    box.appendChild(b);
  });
  return node;
}

function positionModal() {   // v2-position-selector-modal + v2-horizontal-options-showcase + options
  const ordinal = S.positionModal;
  const node = el(`<div class="selection-modal ember-view">
    <div class="selection-modal-wrapper"></div>
    <div class="selection-modal-content"><div class="horizontal-options-showcase ember-view">
      <div class="horizontal-options-showcase-background"></div>
      <div class="horizontal-options-showcase-content"></div>
    </div></div>
  </div>`);
  node.querySelector('.selection-modal-wrapper').addEventListener('click', () => { S.positionModal = null; render(); });
  const content = node.querySelector('.horizontal-options-showcase-content');
  const option = (pos) => {
    const selected = S.positions.includes(pos);
    const o = el(`<div class="v2-position-selector-option ${pos} ${selected ? 'already-selected' : ''} ${pos === 'FILL' ? 'fill' : ''} ember-view">
      <div class="position-selector-option-container">
        <div class="position-selector-text position">${esc(t('parties_position_' + pos.toLowerCase()))}</div>
        <div class="position-selector-text in-demand"></div>
        <div class="v2-position-icon-component ${pos} ${selected ? 'selected' : ''} ember-view"><div class="position-image-container"><div class="position-image"></div><div class="position-image-glow"></div></div></div>
      </div>
      <div class="position-selector-wrapper visible"></div>
    </div>`);
    o.querySelector('.position-selector-wrapper').addEventListener('mouseup', () => {
      const i = ordinal === 'PRIMARY' ? 0 : 1;
      const other = S.positions[1 - i];
      S.positions[i] = pos;
      if (pos === other && pos !== 'FILL') S.positions[1 - i] = 'UNSELECTED';
      if (S.positions[0] === 'FILL') S.positions[1] = 'UNSELECTED';
      S.positionModal = null;
      play('/fe/lol-uikit/sfx-uikit-button-gold-click.ogg');
      render();
    });
    return o;
  };
  POSITIONS.forEach((p) => content.appendChild(option(p)));
  content.appendChild(el('<div class="horizontal-options-showcase-vertical-divider"></div>'));
  if (ordinal === 'PRIMARY') content.appendChild(option('FILL'));
  return node;
}

function inviteInfoPanel() {   // v2-invite-info-panel (no friends service in this installation: lists stay empty)
  return el(`<div class="v2-parties-invite-info-panel ember-view">
    <div class="split-panel-header right-tab-active">
      <a id="invite-header-suggested" class="split-panel-header-title disabled">${esc(t('suggested_panel_lobby_title'))}</a>
      <a id="invite-header-invited" class="split-panel-header-title active">${esc(t('invited_panel_title'))} ( 0 )</a>
      <div class="split-panel-arrow"></div>
    </div>
    <div class="parties-invite-info-panel-body"><ul class="parties-invite-info-panel-list">
      <li class="parties-invite-info-empty"><span class="parties-invite-info-empty-text">${esc(t('custom_game_invited_panel_no_invites'))}</span></li>
    </ul></div>
  </div>`);
}

function lobbyFooter() {   // v2-footer-component
  const draft = QUEUE_PICK[S.selected.queueId] === 'draft';
  const positionsOk = !draft || S.positions[0] === 'FILL' || (S.positions[0] !== 'UNSELECTED' && S.positions[1] !== 'UNSELECTED');
  const node = el(`<div class="v2-footer-component ember-view">
    <div class="left-container"><div class="chat-container"><lol-social-chat-room type="lobby" disabled-when-connecting=""></lol-social-chat-room></div></div>
    <div class="center-container">
      <div class="close-button-container"><div class="close-button"></div></div>
      <div class="find-match-button-container"><div class="left-wing"></div><div class="right-wing"></div></div>
      <div class="role-selectors-container"></div>
    </div>
    <div class="right-container"><div class="invite-info-panel-container"></div></div>
  </div>`);
  const sounds = {   // parties footer buttonSounds
    closeHover: '/fe/lol-parties/sfx-lobby-button-quit-hover.ogg', closeClick: '/fe/lol-parties/sfx-lobby-button-quit-click.ogg',
    confirmHover: '/fe/lol-parties/sfx-lobby-button-find-match-hover.ogg', confirmClick: '/fe/lol-parties/sfx-lobby-button-find-match-click.ogg',
  };
  node.querySelector('.close-button').appendChild(genericButton({
    base: '/fe/lol-parties/button-x.png', over: '/fe/lol-parties/button-x-over.png', down: '/fe/lol-parties/button-x-down.png',
    clickSound: sounds.closeClick, hoverSound: sounds.closeHover,
    onClick: () => { S.partiesState = 'gameSelect'; S.nav = 'home'; render(); },
  }));
  const fm = genericButton({
    base: '/fe/lol-parties/button-find-match.png', over: '/fe/lol-parties/button-find-match-over.png',
    down: '/fe/lol-parties/button-find-match-down.png', disabled: '/fe/lol-parties/button-find-match-disabled.png',
    text: t(S.inQueue ? 'parties_button_in_queue' : 'parties_button_find_match'), enabled: positionsOk && !S.inQueue,
    clickSound: sounds.confirmClick, hoverSound: sounds.confirmHover,
    onClick: () => findMatch(),
  });
  node.querySelector('.find-match-button-container').prepend(fm);
  if (draft) node.querySelector('.role-selectors-container').appendChild(positionSelector());
  node.querySelector('.invite-info-panel-container').appendChild(inviteInfoPanel());
  return node;
}

function lobby() {   // v2-parties-root (inParty)
  const node = el(`<div class="v2-lobby-root-component ember-view">
    <div class="parties-lower-section parties-lower-section-fade-in animations-disabled parties-v2 ember-view"><div class="party-members-container"></div>
      <div class="parties-invite-dropzone"><div class="parties-invite-dropzone-icon"></div><span class="parties-invite-dropzone-tooltip"></span></div>
    </div>
    <div class="footer-container"></div>
    <div class="navbar-blur"></div>
  </div>`);
  const members = node.querySelector('.party-members-container');
  members.appendChild(banner(S.me));
  for (let i = 0; i < 4; i++) members.appendChild(bannerPlaceholder());   // maxTeamSize 5 - 1
  node.querySelector('.footer-container').appendChild(lobbyFooter());
  if (S.positionModal) node.appendChild(positionModal());
  return node;
}

function findMatch() {
  // In queue, then a match is found: this installation has no other players to wait for, the game is found after a
  // short moment [our matchmaking]; then the ready check (rcp-fe-lol-navigation ready-check-root)
  S.inQueue = true;
  render();
  setTimeout(() => {
    if (!S.inQueue) return;
    S.readyCheck = 'in-progress';
    const m = mapAsset(S.selected.mapId, S.selected.gameMode);
    if (m && m.assets['ready-check-background-sound']) play('/' + m.assets['ready-check-background-sound'], 0.7);
    render();
  }, 3000);
}

const QUEUE_TYPE = { 400: 'NORMAL', 430: 'NORMAL', 420: 'RANKED_SOLO_5x5', 440: 'RANKED_FLEX_SR', 450: 'ARAM_UNRANKED_5x5' };

function readyCheck() {   // ready-check-root (low spec: intro -> in-progress straight away) and its parts
  const st = S.readyCheck;
  const m = mapAsset(S.selected.mapId, S.selected.gameMode) || { assets: {} };
  const a = (k) => (m.assets[k] ? '/' + m.assets[k] : '');
  const responded = st === 'accepted' || st === 'declined';
  const timerVideo = { 'in-progress': 'timer-countdown', accepted: 'timer-accepted-intro', declined: 'timer-declined' }[st];
  const node = el(`<div class="ready-check-root-element ember-view">
    <div class="ready-check-visible-state-hack">
      <div class="ready-check-map-background ember-view ${st === 'declined' ? 'ready-check-map-background-declined' : ''}"><img class="ready-check-map-background-image" src="${a('ready-check-background')}"></div>
      <div class="ready-check-frame-element"></div>
      <div class="ready-check-timer ember-view"><video class="ready-check-timer-${timerVideo}" autoplay muted src="/fe/lol-static-assets/videos/${timerVideo}.webm"></video></div>
      <div class="ready-check-map-icon ember-view"><img class="ready-check-map-icon-image" src="${a(st === 'declined' ? 'game-select-icon-default' : 'game-select-icon-hover')}"></div>
      <div class="ready-check-status-text ember-view">
        ${responded ? `<div class="ready-check-status-title">${st === 'accepted'
          ? `${esc(t('ready_check_response_message_accepted'))}<div class="ready-check-status-details">${esc(t('ready_check_waiting_players'))}</div>`
          : esc(t('ready_check_response_message_declined'))}</div>`
        : `<div class="ready-check-status-title">${esc(t('ready_check_match_found'))}</div>
           <div class="ready-check-status-details">${esc(t('game_select_map_name_' + S.selected.mapId))}<span class="ready-check-bullet">•</span>${esc(t('ready_check_queue_type_' + (QUEUE_TYPE[S.selected.queueId] || 'NORMAL')))}<span class="ready-check-bullet">•</span>${esc(t('ready_check_tagline_versus').replace('{{myTeamCount}}', 5).replace('{{theirTeamCount}}', 5))}</div>`}
      </div>
      <div class="ready-check-buttons-element">
        <div class="ready-check-button-accept ember-view ${responded ? 'ready-check-button-accept-disabled' : ''}">${esc(t('ready_check_accept_button'))}</div>
        <lol-uikit-flat-button class="ready-check-button-decline ember-view" ${responded ? 'disabled' : ''}>${esc(t('ready_check_decline_button'))}</lol-uikit-flat-button>
      </div>
    </div>
  </div>`);
  if (!responded) {
    node.querySelector('.ready-check-button-accept').addEventListener('click', () => {
      play('/fe/lol-uikit/sfx-uikit-button-gold-click.ogg');
      S.readyCheck = 'accepted';
      render();
      setTimeout(() => { S.readyCheck = null; S.inQueue = false; startChampSelect(); }, 2000);
    });
    node.querySelector('.ready-check-button-decline').addEventListener('click', () => {
      play('/fe/lol-uikit/sfx-uikit-button-gold-click.ogg');
      S.readyCheck = 'declined';
      render();
      setTimeout(() => { S.readyCheck = null; S.inQueue = false; render(); }, 2000);
    });
  }
  return node;
}

// ---------------------------------------------------------------------------------------------------------------
// viewport

function render() {
  const full = document.querySelector('[data-screen-name="rcp-fe-lol-champ-select"]');
  const rc = document.querySelector('[data-screen-name="rcp-fe-lol-ready-check"]');
  rc.replaceChildren(...(S.readyCheck ? [readyCheck()] : []));
  if (S.screen === 'champSelect') {
    // champion select covers the window (1278 x 718); the navigation hides meanwhile
    const search = document.activeElement && document.activeElement.classList.contains('champion-input');
    full.replaceChildren(championSelect());
    full.classList.add('active');
    document.querySelector('[data-screen-name="rcp-fe-lol-navigation-screen"]').replaceChildren();
    if (search) { const i = full.querySelector('.champion-input'); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }
    return;
  }
  full.replaceChildren();
  full.classList.remove('active');
  const nav = document.querySelector('[data-screen-name="rcp-fe-lol-navigation-screen"]');
  nav.replaceChildren(navigation());
  const main = document.querySelector('.rcp-fe-viewport-main');
  const partiesRoot = main.querySelector('[data-screen-name="rcp-fe-lol-parties"]');
  const homeRoot = main.querySelector('[data-screen-name="rcp-fe-lol-home-main"]');
  partiesRoot.classList.toggle('active', S.nav === 'parties');
  partiesRoot.classList.toggle('hidden', S.nav !== 'parties');
  homeRoot.classList.toggle('active', S.nav === 'home');
  homeRoot.classList.toggle('hidden', S.nav !== 'home');
  partiesRoot.replaceChildren(S.nav === 'parties' ? parties() : document.createTextNode(''));
}

(async () => {
  await defineUikit();
  await loadData();
  render();
})();
