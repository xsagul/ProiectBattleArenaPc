// 14.1 rcp-fe-lol-parties: Training -> PRACTICETOOL -> custom lobby -> champion select.
// Element trees: research/lcu141/templates/rcp-fe-lol-parties; asset mapping: TUTORIAL_ASSETS.
// Only the locally implemented mode is enabled. No substitute match for an unsupported queue.
// This is our service/UI adapter; no Riot JavaScript is executed.
'use strict';

const gameflow = {
  screen: 'MODE_SELECT', selected: null, tra: {}, modes: [], error: '',
  async load() {
    const json = async (url) => {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Cannot load ${url}`);
      return response.json();
    };
    [this.tra, this.modes] = await Promise.all([
      json('/fe/lol-parties/trans.json'), json('/lol/modes'),
    ]);
  },
  text(key) { return this.tra[key] || key; },
  show(screen) {
    this.screen = screen;
    this.error = '';
    render();
  },
  mode() { return this.modes.find((m) => m.gameMode === this.selected); },
  // Shared component lib.arrow-footer...hbs. Its CSS supplies all the image slices.
  footer(label, confirm, cancel, enabled = true) {
    const node = el(`<div class="arrow-footer" version="7.13">
      <div class="arrow-footer-decoration"><div class="arrow-footer-decoration-child arrow-footer-decoration-left"></div></div>
      <div class="confirm-button-container"><div class="border-bg"><div class="left-border-bg"></div><div class="middle-border-bg"></div><div class="right-border-bg"></div></div>
        <button class="confirm ${enabled ? '' : 'disabled'}" ${enabled ? '' : 'disabled'}><div class="left-confirm"></div><div class="middle-confirm">${esc(label)}</div><div class="right-confirm"></div></button>
        <button class="close" type="back" aria-label="${esc(this.text('parties_button_cancel'))}"><div class="close-icon"></div></button>
      </div><div class="arrow-footer-decoration"><div class="arrow-footer-decoration-child arrow-footer-decoration-right"></div></div>
    </div>`);
    node.querySelector('.confirm').onclick = () => {
      if (!enabled) return;
      play('/fe/lol-uikit/sfx-uikit-button-gold-click.ogg');
      confirm();
    };
    node.querySelector('.close').onclick = cancel;
    return node;
  },
  card(mode, asset) {
    const supported = this.modes.some((m) => m.gameMode === mode && m.available);
    const selected = this.selected === mode;
    const name = this.text(`game_select_game_type_name_11_${mode.toLowerCase()}`);
    const node = el(`<div class="game-type-card ember-view ${selected ? 'selected' : ''} ${supported ? '' : 'disabled'}" data-map-id="11" data-game-mode="${mode}">
      <div class="parties-game-type-upper-half" role="button" tabindex="${supported ? '0' : '-1'}" aria-label="${esc(name)}" aria-disabled="${!supported}" aria-pressed="${selected}" ${supported ? '' : 'title="Not available in this installation"'}>
        <div class="parties-game-type-icon map-11"><div class="parties-game-type-card-selected-glow"></div><div class="icon-frame">
          ${['default', 'hover', 'disabled', 'active'].map((s) => `<div class="icon-bg icon-bg-${s}" style="background-image:url('/fe/lol-parties/${asset}-${s === 'active' ? 'icon-victory' : s}.png')"></div>`).join('')}
        </div><div class="parties-game-type-card-break"></div><div class="parties-game-type-card-name">${esc(name)}</div></div>
      </div><div class="parties-game-type-lower-half"><div class="parties-game-type-card-intro">${esc(this.text(`game_select_category_description_training_11_${mode.toLowerCase()}`))}</div></div>
    </div>`);
    const button = node.querySelector('[role=button]');
    button.onclick = () => {
      if (!supported) return;
      this.selected = mode;
      play('/fe/lol-uikit/sfx-uikit-button-gold-click.ogg');
      render();
    };
    button.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); button.click(); }
    };
    return node;
  },
  selection() {
    const node = el(`<div class="parties-game-select-screen game-select-show ember-view"><div class="parties-game-select-wrapper">
      <div class="parties-game-navs"><nav class="parties-game-navs-list local-category-nav" aria-label="Game category"></nav><hr></div>
      <div class="parties-game-type-select-wrapper"></div>
    </div><div class="game-select-footer-container"></div></div>`);
    const nav = node.querySelector('nav');
    for (const category of ['PvP', 'VersusAi', 'Training', 'CreateCustom', 'JoinCustom']) {
      if (category === 'CreateCustom') nav.appendChild(el('<span class="parties-game-navs-break"></span>'));
      const active = category === 'Training';
      nav.appendChild(el(`<button class="parties-game-navs-item ${active ? 'active' : ''}" data-category="${category}" ${active ? 'aria-current="page"' : 'disabled title="Not available in this installation"'}>${esc(this.text('parties_game_category_' + category.toLowerCase()))}</button>`));
    }
    const cards = node.querySelector('.parties-game-type-select-wrapper');
    cards.append(this.card('TUTORIAL_FLOW', 'battletraining'), this.card('PRACTICETOOL', 'practicetool'));
    node.querySelector('.game-select-footer-container').appendChild(this.footer(
      this.text('parties_button_confirm'), () => this.show('LOBBY'), () => { this.selected = null; render(); }, !!this.mode()?.available));
    return node;
  },
  lobby() {
    // PracticeTool is customGameLobby configuration {mapId:11, teamSize:1, mutators:{id:1}} in 14.1.
    // The original uses custom-game-root, NOT the ranked/quickplay banner lobby.
    const node = el(`<div class="local-custom-lobby">
      <div class="parties-header-container custom-header-container"><div class="lobby-header-wrapper custom-header-wrapper">
        <div class="lobby-header-map-icon game_map_summoners_rift"></div><div class="lobby-header-right"><div class="lobby-header-details"><span class="lobby-header-detail uppercase">${esc(state.me.name)}</span></div>
        <div class="lobby-header-game-type-details"><span class="lobby-header-game-type-detail lobby-header-custom-map-name">${esc(this.text('game_select_game_type_name_11_classic'))}</span><span class="lobby-header-game-type-detail">1v1</span><span class="lobby-header-game-type-detail">${esc(this.text('game_select_game_type_name_11_practicetool'))}</span></div></div>
      </div></div>
      <div class="custom-root custom-lobby-show"><div class="parties-lower-section parties-lower-section-fade-in animations-disabled">
        <div class="custom-game-teams">
          <div class="custom-game-team custom-game-team-one"><div class="team-header">${esc(this.text('custom_game_team_one'))}</div><ul class="custom-game-team-members">
            <li class="custom-game-team-member is-current-custom-player is-custom-leader" data-custom-member-type="player"><div class="custom-member-info-left"><div class="custom-info-left-first"></div><div class="custom-member-icon"></div><div class="custom-member-name">${esc(state.me.name)}</div><div class="custom-leader-icon"></div></div></li>
          </ul></div>
          <div class="custom-game-team custom-game-team-two"><div class="team-header">${esc(this.text('custom_game_team_two'))}</div><ul class="custom-game-team-members">
            <li class="custom-game-team-member" data-custom-member-type="placeholder"><div class="custom-member-info-left"><div class="custom-team-member-placeholder member-info-left">${esc(this.text('custom_game_empty'))}</div></div>
              <div class="custom-member-info-right custom-placeholder-buttons"><button disabled title="Not available in this installation">${esc(this.text('custom_game_bot_add'))}</button></div></li>
          </ul></div>
        </div><div class="local-lobby-footer"></div>
      </div></div>
    </div>`);
    node.querySelector('.local-lobby-footer').appendChild(this.footer(this.text('parties_button_start_game'), () => {
      state.selected = null;
      state.locked = null;
      state.phase = 'BAN_PICK';
      state.phaseEnds = performance.now() + kPickSeconds * 1000;
      this.show('CHAMP_SELECT');
    }, () => this.show('MODE_SELECT')));
    return node;
  },
  render() {
    const root = el('<div class="screen local-parties-shell"><div class="parties-view ember-view"><div class="parties-background"><div class="parties-background-mask"></div></div><div class="parties-content"></div></div></div>');
    root.querySelector('.parties-content').appendChild(this.screen === 'LOBBY' ? this.lobby() : this.selection());
    if (this.error) root.appendChild(el(`<div class="local-flow-error" role="alert">${esc(this.error)}</div>`));
    return root;
  },
};
