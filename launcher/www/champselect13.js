// Champion select after League Client 13.3 (plugin rcp-fe-lol-champ-select), one local player picking.
// Element trees: data/lcu133/templates/rcp-fe-lol-champ-select/*.hbs (each builder names its layout); state
// classes from the components' classNameBindings; style sheet, pictures, sounds, texts and champion data are the
// client's. Low spec mode (no large-area animations: the image backgrounds instead of the videos).
// Summoner spells and the skin are chosen in a plain strip of our own under the champion's name once it is locked
// (the client's loadouts-edit / skin-select components are not rebuilt). Not there: runes, chat, bans, the other
// nine players.
'use strict';

const CS_SOUNDS = '/fe/lol-champ-select/sounds/';
// Phase lengths come from Riot's servers (session.timer), no file has them [to verify on a 13.3 recording]:
// draft queues pick 30 s / finalization 30 s, blind pick 90 s / 10 s.
const PHASE_SECONDS = { draft: [30, 30], blind: [90, 10] };

const CSEL = {
  phase: 'BAN_PICK', phaseEnds: 0, selected: null, locked: null, search: '', filters: {}, lastTick: -1,
  starting: false, error: '', spells: ['SummonerFlash', 'SummonerDot'], skin: 0, choosing: -1, runes: '',
};
// the rune pages the server knows (server/core/runes.py); '' = the page of the champion's class
const CS_RUNES = [['', 'Runes: by class'], ['Conqueror', 'Conqueror'], ['Electrocute', 'Electrocute'],
  ['PressTheAttack', 'Press the Attack'], ['SummonAery', 'Summon Aery'], ['GraspOfTheUndying', 'Grasp of the Undying']];
// the game's names of the summoner spells of Summoner's Rift, their client names and icons (lol-game-data)
const CS_SPELLS = [
  ['SummonerFlash', 'Flash', 'Summoner_flash.png'], ['SummonerDot', 'Ignite', 'SummonerIgnite.png'],
  ['SummonerHeal', 'Heal', 'Summoner_heal.png'], ['SummonerHaste', 'Ghost', 'Summoner_haste.png'],
  ['SummonerBarrier', 'Barrier', 'SummonerBarrier.png'], ['SummonerExhaust', 'Exhaust', 'Summoner_exhaust.png'],
  ['SummonerSmite', 'Smite', 'Summoner_smite.png'], ['SummonerTeleport', 'Teleport', 'Summoner_teleport.png'],
  ['SummonerBoost', 'Cleanse', 'Summoner_boost.png'],
];
const csSpellIcon = (id) => '/lol-game-data/assets/DATA/Spells/Icons2D/' + (CS_SPELLS.find((s) => s[0] === id) || CS_SPELLS[0])[2];
try {
  const saved = JSON.parse(localStorage.getItem('ba.spells') || 'null');
  if (Array.isArray(saved) && saved.length === 2 && saved.every((s) => CS_SPELLS.some((x) => x[0] === s))) CSEL.spells = saved;
} catch (e) { /* no stored choice */ }

function csText(k) { return S.csTra[k] ?? k; }

function startChampSelect() {
  const [pick] = PHASE_SECONDS[QUEUE_PICK[S.selected.queueId]] || PHASE_SECONDS.blind;
  Object.assign(CSEL, { phase: 'BAN_PICK', phaseEnds: performance.now() + pick * 1000, selected: null, locked: null,
    search: '', filters: {}, lastTick: -1, starting: false, error: '', skin: 0, choosing: -1 });
  S.screen = 'champSelect';
  render();
}

// summoner-object-component/layout.hbs (13.3: no swap / subteam wrappers), low spec branch
function csSummonerObject() {
  const champ = CSEL.locked || CSEL.selected;
  const picking = CSEL.phase === 'BAN_PICK' && !CSEL.locked;
  const icon = champ ? `background-image:url(${champ.squarePortraitPath})` : '';
  const primary = CSEL.locked ? '' : picking ? csText('picking_champion') : '';
  return el(`
    <div class="summoner-object ember-view left isSelf ${picking ? 'is-picking-now' : ''} ${CSEL.locked ? 'actions-complete' : ''} slot-id-0">
      <div class="image-magic-background ${picking ? 'is-acting-background' : 'not-acting-background'} skin-showcase"></div>
      <div class="active-bar ${picking ? '' : 'hidden'}"></div>
      <div class="active-bar-spacer"></div>
      <div class="summoner-spells removed"></div>
      <div class="summoner-ban-item removed"></div>
      <div class="summoner-container-spacer"></div>
      <div class="summoner-container ${picking ? 'expanded' : 'collapsed'}">
        <div class="champion-icon-container">
          <div class="champion-ring-pop-animation removed"></div>
          <div class="champion-ring-shine-animation removed"></div>
          <div class="champion-icon-pick-snipe-glow-animation"></div>
          <div class="champion-icon-pick-snipe-magic-animation"></div>
          <div class="champion-icons"><div class="champion-icons-bg"></div><div class="portrait-icon fit-icon" style="${icon}"></div></div>
          <div class="champion-ring"></div>
          <div class="champion-icon-pick-snipe-ring-animation"></div>
          <div class="champion-icon-pick-snipe-magic-animation"></div>
          <div class="champion-ring-magic-animation-inner removed"></div>
          <div class="champion-ring-magic-animation-outer removed"></div>
          <div class="image-ring-spinner ${picking ? 'visible' : 'removed'} left-side is-self not-animated"></div>
        </div>
        <div class="player-details-spacer"></div>
        <div class="player-details">
          <div class="champion-vote-projection no-vote-percent"></div>
          <div class="summoner-secondary-text ${champ ? '' : 'removed'}"><span class="summoner-secondary-text-inner">${champ ? esc(champ.name) : ''}</span></div>
          <div class="summoner-primary-text ${primary ? '' : 'hidden'}">${esc(primary)}<div class="summoner-primary-text-glow">${esc(primary)}</div></div>
          <div class="summoner-name"><span class="name-text">${esc(S.me.name)}</span></div>
        </div>
      </div>
    </div>`);
}

// summoner-array-component/layout.hbs
function csSummonerArray(isLeft) {
  const node = el(`
    <div class="summoner-array ember-view ${isLeft ? 'your-party' : 'enemy-party'}">
      <span class="first-pick removed"></span>
      <div class="party visible"></div>
    </div>`);
  const party = node.querySelector('.party');
  if (isLeft) {
    const wrap = el('<div class="summoner-wrapper visible left"><div class="lines visible"></div></div>');
    wrap.appendChild(csSummonerObject());
    party.appendChild(wrap);
  }
  party.appendChild(el('<div class="summoner-timer-wrapper"><div class="summoner-timer ember-view"></div></div>'));
  return node;
}

// timer-status-component/layout.hbs (header not expanded)
function csTimerStatus() {
  const metal = 'M-261.55,112.3v9.45h10.79V101.37h-5.4c-47,0-87.17-36-93.48-83.75l-2.71-7.84H-583.08L-595.5-2.5h212c-.08,1.83,0,10.14,0,12h4v-16l-236,0v4h4l23,23.14h225.34C-354.46,69.64-310,109.74-261.55,112.3Zm6,17.2c-57.68,0-107.69-40.62-120-96h-4c12.41,58.46,63.33,100,124,100h996l4-4Z';
  return el(`
    <div class="timer-status ember-view">
      <div class="message local-player-acting"></div>
      <div class="timer-container">
        <div class="burnout-timer left hidden blue"><div class="burnout-timer-glow"></div><div class="burnout-timer-bar"></div></div>
        <div class="timer" data-time=""></div>
        <div class="burnout-timer right hidden blue"><div class="burnout-timer-glow"></div><div class="burnout-timer-bar"></div></div>
        <svg class="metal-work left" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1360 140.04" width="340" height="35.01">
          <defs><linearGradient id="Gradient1"><stop class="stop1" offset="0%"></stop><stop class="stop2" offset="55%"></stop></linearGradient>
          <style type="text/css">.cls-1 { fill: url(#Gradient1); } .stop1 { stop-color: #463714; } .stop2 { stop-color: #785A28; }</style></defs>
          <path class="cls-1" transform="translate(615.5 6.54)" d="${metal}"></path>
        </svg>
        <svg class="metal-work right" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1360 140.04" width="340" height="35.01">
          <path class="cls-1" transform="translate(615.5 6.54)" d="${metal}"></path>
        </svg>
      </div>
    </div>`);
}

// champion-grid-component/layout.hbs + champion-grid-champion-component/layout.hbs
const CS_FILTERS = ['top', 'jungle', 'middle', 'bottom', 'support'];
function csChampionGrid() {
  const node = el(`
    <div class="champion-grid ember-view champion-grid-visible">
      <div class="champion-grid-header">
        <div class="filter-icons"></div>
        <div class="spacer"></div>
        <lol-uikit-flat-input><input class="champion-input ember-view ember-text-field" type="search" maxlength="25" name="searchText" placeholder="${esc(csText('search'))}"></lol-uikit-flat-input>
      </div>
      <div class="champions"><div class="champion-container ember-view"></div></div>
    </div>`);
  const icons = node.querySelector('.filter-icons');
  for (const name of CS_FILTERS) {
    const f = el(`<div class="filter ${name} ${CSEL.filters[name] ? 'active' : ''}" title="${esc(csText('filter_by_position_' + name))}"></div>`);
    f.onclick = () => {
      CSEL.filters[name] = !CSEL.filters[name];
      f.classList.toggle('active', !!CSEL.filters[name]);
      play('/fe/lol-uikit/sfx-uikit-generic-click-small.ogg');
      csFillGrid(node);
    };
    icons.appendChild(f);
  }
  const input = node.querySelector('input');
  input.value = CSEL.search;
  input.oninput = () => { CSEL.search = input.value; csFillGrid(node); };
  csFillGrid(node);
  return node;
}

function csFillGrid(grid) {
  const box = grid.querySelector('.champion-container');
  box.textContent = '';
  // ember-collection: absolutely placed cells of 101 x 96 in a width of 622 (gridChampionLayout, gridEstimatedClientWidth)
  const cellW = 101, cellH = 96, columns = Math.floor(622 / cellW);
  const q = CSEL.search.trim().toLowerCase();
  // the position filters use the client's per-position lists (a statistics service, not in its files); the
  // champions' own roles stand in for them [approximation]
  const roleOf = { top: 'fighter', jungle: 'assassin', middle: 'mage', bottom: 'marksman', support: 'support' };
  const roles = CS_FILTERS.filter((f) => CSEL.filters[f]).map((f) => roleOf[f]);
  const list = S.champions
    .filter((c) => !q || c.name.toLowerCase().includes(q))
    .filter((c) => !roles.length || (c.roles || []).some((r) => roles.includes(r)))
    .sort((a, b) => a.name.localeCompare(b.name));
  const scroller = el('<div style="position:absolute;left:0;top:0;width:100%;height:100%;overflow-y:auto;"></div>');
  const content = el(`<div style="position:relative;width:100%;height:${Math.ceil(list.length / columns) * cellH}px;"></div>`);
  scroller.appendChild(content);
  box.appendChild(scroller);
  list.forEach((c, i) => {
    const picked = CSEL.selected === c;
    const wrap = el(`<div style="position:absolute;left:0;top:0;width:${cellW}px;height:${cellH}px;transform:translate(${(i % columns) * cellW}px, ${Math.floor(i / columns) * cellH}px);"></div>`);
    const cell = el(`
      <div class="grid-champion ember-view ${picked ? 'grid-champion-selected' : ''}">
        <div class="grid-champion-hitbox">
          <div class="champion-grid-champion-thumbnail"><img class="champion-background-image" src="${c.squarePortraitPath}" loading="lazy"></div>
          <lol-uikit-resizing-text-field class="champion-name" data-max-width="100">${esc(c.name)}</lol-uikit-resizing-text-field>
          <div class="grid-champion-overlay"></div>
        </div>
      </div>`);
    cell.onmouseenter = () => play(CS_SOUNDS + 'sfx-uikit-grid-hover.ogg', 0.5);
    cell.onclick = () => {
      if (CSEL.locked) return;
      CSEL.selected = c;
      play(CS_SOUNDS + 'sfx-uikit-grid-click.ogg');
      render();
    };
    wrap.appendChild(cell);
    content.appendChild(wrap);
  });
}

// lock-in-button-component/layout.hbs + action-button-component/layout.hbs
function csLockIn() {
  const disabled = !CSEL.selected || !!CSEL.locked;
  const node = el(`
    <div class="lock-in ember-view ${CSEL.locked ? 'hidden' : 'visible'} picking">
      <div class="action-button-container ember-view">
        <div class="action-button" ${disabled ? 'disabled="true"' : ''}>
          <div class="action-button-background"></div>
          <div class="action-button-inner"><div class="visible">${esc(csText('lock_in'))}</div></div>
        </div>
      </div>
    </div>`);
  const b = node.querySelector('.action-button');
  b.onmouseenter = () => { if (!disabled) play(CS_SOUNDS + 'sfx-cs-lockin-button-hover.ogg'); };
  b.onclick = () => {
    if (disabled) return;
    play(CS_SOUNDS + 'sfx-cs-lockin-button-click.ogg');
    CSEL.locked = CSEL.selected;
    // the champion's own pick line and stinger (chooseVoPath, stingerSfxPath of its data)
    if (CSEL.locked.chooseVoPath) play(CSEL.locked.chooseVoPath, 1);
    if (CSEL.locked.stingerSfxPath) play(CSEL.locked.stingerSfxPath, 0.6);
    const [, fin] = PHASE_SECONDS[QUEUE_PICK[S.selected.queueId]] || PHASE_SECONDS.blind;
    CSEL.phase = 'FINALIZATION';
    CSEL.phaseEnds = performance.now() + fin * 1000;
    render();
  };
  return node;
}

// the two summoner spells and the skin of the locked champion
function csLoadout() {
  const skins = (CSEL.locked && CSEL.locked.skins) || [];
  const skin = skins.find((s) => s.num === CSEL.skin);
  const node = el(`
    <div class="cs-loadout" style="position:absolute;left:50%;bottom:86px;transform:translateX(-50%);display:flex;gap:18px;align-items:center;z-index:5;">
      <div class="cs-skin" style="display:${skins.length > 1 ? 'flex' : 'none'};gap:8px;align-items:center;color:#f0e6d2;font-family:var(--font-display, serif);font-size:13px;letter-spacing:0.05em;">
        <div class="cs-skin-prev" style="cursor:pointer;padding:4px 8px;border:1px solid #785a28;">&#9664;</div>
        <div style="min-width:180px;text-align:center;">${esc(skin ? skin.name : '')}</div>
        <div class="cs-skin-next" style="cursor:pointer;padding:4px 8px;border:1px solid #785a28;">&#9654;</div>
      </div>
      <div class="cs-spells" style="display:flex;gap:6px;position:relative;"></div>
      <select class="cs-runes" style="background:#010a13;color:#f0e6d2;border:1px solid #785a28;padding:6px 8px;font-size:12px;">
        ${CS_RUNES.map(([id, name]) => `<option value="${id}" ${CSEL.runes === id ? 'selected' : ''}>${esc(name)}</option>`).join('')}
      </select>
    </div>`);
  node.querySelector('.cs-runes').onchange = (e) => { CSEL.runes = e.target.value; };
  const step = (d) => {
    const i = Math.max(0, skins.findIndex((s) => s.num === CSEL.skin));
    CSEL.skin = skins[(i + d + skins.length) % skins.length].num;
    play('/fe/lol-uikit/sfx-uikit-generic-click-small.ogg');
    render();
  };
  node.querySelector('.cs-skin-prev').onclick = () => step(-1);
  node.querySelector('.cs-skin-next').onclick = () => step(1);
  const box = node.querySelector('.cs-spells');
  CSEL.spells.forEach((id, slot) => {
    const b = el(`<div title="${esc((CS_SPELLS.find((s) => s[0] === id) || [])[1] || '')}" style="width:40px;height:40px;cursor:pointer;border:1px solid ${CSEL.choosing === slot ? '#f0e6d2' : '#785a28'};background:url(${csSpellIcon(id)}) center/cover;"></div>`);
    b.onclick = () => { CSEL.choosing = CSEL.choosing === slot ? -1 : slot; play('/fe/lol-uikit/sfx-uikit-generic-click-small.ogg'); render(); };
    box.appendChild(b);
  });
  if (CSEL.choosing >= 0) {
    const pop = el('<div style="position:absolute;bottom:50px;left:50%;transform:translateX(-50%);display:grid;grid-template-columns:repeat(5,40px);gap:4px;padding:8px;background:#010a13;border:1px solid #785a28;"></div>');
    for (const [id, name, icon] of CS_SPELLS) {
      const o = el(`<div title="${esc(name)}" style="width:40px;height:40px;cursor:pointer;border:1px solid #463714;background:url(/lol-game-data/assets/DATA/Spells/Icons2D/${icon}) center/cover;"></div>`);
      o.onclick = () => {
        const other = 1 - CSEL.choosing;
        if (CSEL.spells[other] === id) CSEL.spells[other] = CSEL.spells[CSEL.choosing];     // the two swap places
        CSEL.spells[CSEL.choosing] = id;
        CSEL.choosing = -1;
        try { localStorage.setItem('ba.spells', JSON.stringify(CSEL.spells)); } catch (e) { /* not kept */ }
        play('/fe/lol-uikit/sfx-uikit-generic-click-small.ogg');
        render();
      };
      pop.appendChild(o);
    }
    box.appendChild(pop);
  }
  return node;
}

// champ-select root layout.hbs
function championSelect() {
  const champ = CSEL.locked || CSEL.selected;
  const screen = CSEL.locked ? 'selected-screen' : 'pick-screen';
  const picking = CSEL.phase === 'BAN_PICK' && !CSEL.locked;
  const lockedSkin = CSEL.locked ? (CSEL.locked.skins || []).find((s) => s.num === CSEL.skin) : null;
  const splash = lockedSkin ? lockedSkin.splashPath : champ ? champ.splashPath : '';
  const q = S.queues[String(S.selected.queueId)] || {};
  const root = el(`
    <div class="champion-select ember-view screen ${screen} ${picking ? 'is-acting-now is-picking-now is-showing-grid' : ''} no-large-area-animations">
      <div class="position-assignment-intro-container hidden"></div>
      <div class="champion-splash-background ember-view ${screen} large-area-animations-disabled is-pending is-not-rotating ${picking ? 'is-showing-grid' : 'is-not-showing-grid'}">
        <div class="background-vignette-container ${picking ? 'defocussed' : 'focussed'} static ${splash ? 'visible' : 'hidden'}">
          <div class="uikit-background-switcher ember-view champ-select-bg" style="position:absolute;left:0;top:0;width:100%;height:100%;">
            ${splash ? `<img src="${splash}" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;">` : ''}
          </div>
          <div class="${splash ? 'champ-select-bg-darken' : ''}"></div>
        </div>
      </div>
      <div class="top-darken"></div>
      <div class="champion-select-summoner-array-container ${CSEL.phase === 'FINALIZATION' ? 'in-finalization' : ''}"></div>
      <div class="champion-select-main-container">
        <div class="visible main-inner">
          <div class="${picking || CSEL.locked ? 'visible' : 'hidden'} pick-phase-holder">
            <div class="pick-phase ember-view pick-phase-visible ${picking ? 'champion-grid-visible' : 'champion-grid-hidden'}">
              <div class="champion-name-wrapper ${CSEL.locked ? 'visible just-locked' : 'hidden'}">
                <div class="champion-skin-name ember-view"><div class="skin-name-text">${CSEL.locked ? esc(CSEL.locked.name) : ''}</div></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="bottom-right-buttons">
        <div class="corner-game-info-container">
          <div class="team-size">${esc(t('game_select_team_size').replaceAll('{{size}}', 5))}</div>
          <div class="queue-name">${esc(q.description || '')}</div>
        </div>
      </div>
    </div>`);
  const arrays = root.querySelector('.champion-select-summoner-array-container');
  arrays.appendChild(csSummonerArray(true));
  arrays.appendChild(csSummonerArray(false));
  const inner = root.querySelector('.main-inner');
  inner.insertBefore(csTimerStatus(), inner.firstChild);
  const phase = root.querySelector('.pick-phase');
  if (picking) {
    phase.insertBefore(csChampionGrid(), phase.firstChild);
    phase.insertBefore(csLockIn(), phase.querySelector('.champion-name-wrapper'));
  }
  if (CSEL.phase !== 'GAME_STARTING') root.appendChild(csLoadout());
  if (CSEL.error) root.appendChild(el(`<div class="cs-start-error">${esc(CSEL.error)}</div>`));
  return root;
}

function csTick() {
  if (S.screen !== 'champSelect') return;
  const root = document.querySelector('.champion-select');
  if (!root) return;
  const left = Math.max(0, Math.ceil((CSEL.phaseEnds - performance.now()) / 1000));
  const timer = root.querySelector('.timer-status .timer');
  const message = root.querySelector('.timer-status .message');
  const starting = CSEL.phase === 'GAME_STARTING';
  if (timer) { timer.textContent = starting ? '' : String(left); timer.dataset.time = starting ? '' : String(left); }
  if (message) {
    message.textContent = starting ? csText('timer_phase_game_starting_message')
      : CSEL.phase === 'FINALIZATION' ? csText('timer_phase_finalization_message')
        : CSEL.selected ? csText('timer_phase_ban_pick_lock_message') : csText('timer_phase_ban_pick_choose_message');
  }
  root.classList.toggle('timer-less-than-11-seconds', left < 11 && !starting);
  if (left !== CSEL.lastTick && left <= 10 && left > 0 && CSEL.phase === 'BAN_PICK') play(CS_SOUNDS + 'sfx-cs-timer-tick.ogg', 0.6);
  CSEL.lastTick = left;
  if (left > 0 || starting) return;
  if (CSEL.phase === 'BAN_PICK') {
    // nobody locked in: champion select ends, back to the lobby (the client's dodge path)
    S.screen = 'client';
    S.inQueue = false;
    render();
  } else if (CSEL.phase === 'FINALIZATION') {
    CSEL.phase = 'GAME_STARTING';
    render();
    startGame();
  }
}
setInterval(csTick, 100);

async function startGame() {
  const body = new URLSearchParams({ champion: CSEL.locked.alias, skin: String(CSEL.skin || 0), spells: CSEL.spells.join(','),
    runes: CSEL.runes, queue: String(S.selected.queueId) });
  try {
    const r = await fetch('/lol/start', { method: 'POST', body });
    const res = await r.json();
    if (!r.ok || !res.ok) throw new Error(res.error || 'the game did not start');
  } catch (e) {
    CSEL.error = e.message;
    render();
    setTimeout(() => { S.screen = 'client'; S.inQueue = false; CSEL.error = ''; render(); }, 4000);
    return;
  }
  const poll = async () => {
    try {
      const r = await fetch('/lol/status');
      if (r.ok && !(await r.json()).inGame) {
        S.screen = 'client';
        S.inQueue = false;
        render();
        return;
      }
    } catch (e) { /* the game server page may be busy; ask again */ }
    setTimeout(poll, 1500);
  };
  setTimeout(poll, 3000);
}
