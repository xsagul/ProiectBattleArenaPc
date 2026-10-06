// The <lol-uikit-*> / <uikit-*> elements of League Client 13.3, as this project's own small element classes: each
// attaches the client's own shadow template and style sheet (uikit/elements.json, read out of rcp-fe-lol-uikit.js by
// tools/uikit_extract.js) and does what the client's element does with its attributes (the attribute -> class rules
// below are the ones in the client's element code). Riot's scripts are not run.
'use strict';

const UIKIT_SOUNDS = {   // rcp-fe-lol-uikit module 7
  navClick: '/fe/lol-uikit/sfx-nav-button-text-click.ogg',
  subnavClick: '/fe/lol-uikit/sfx-uikit-text-click-small.ogg',
  radioInputClick: '/fe/lol-uikit/sfx-uikit-radio-click.ogg',
  flatButtonHover: '/fe/lol-uikit/sfx-uikit-button-gold-hover.ogg',
  flatButtonClick: '/fe/lol-uikit/sfx-uikit-button-gold-click.ogg',
};

function uikitSound(src, volume = 0.5) {
  try {
    const a = new Audio(src);
    a.volume = volume;
    a.play().catch(() => {});
  } catch (e) { /* no audio device */ }
}

const truthy = (v) => v !== null && v !== undefined && v !== 'false';

async function defineUikit() {
  const defs = {
    ...(await (await fetch('/uikit/elements.json')).json()),
    ...(await (await fetch('/uikit/elements-shared-components.json')).json()),
  };
  const shadow = (host, tag) => {
    const d = defs[tag];
    const root = host.attachShadow({ mode: 'open' });
    const tpl = document.createElement('template');
    // the module is "<template>...</template>", sometimes after a comment: keep what is inside the template tags
    const src = d.template || '<template><slot></slot></template>';
    const a = src.indexOf('<template>');
    const b = src.lastIndexOf('</template>');
    tpl.innerHTML = (d.css ? `<style>${d.css}</style>` : '') + (a >= 0 && b > a ? src.slice(a + 10, b) : src);
    root.appendChild(tpl.content.cloneNode(true));
    return root;
  };
  const special = {
    // the item's .section carries active / disabled / alert as classes; a click on an item that is neither active
    // nor disabled plays the bar's sound and asks the bar to make it the selected one
    'lol-uikit-navigation-item': (Base) => class extends Base {
      static get observedAttributes() { return ['active', 'disabled', 'alert']; }
      constructor() {
        super();
        this.addEventListener('click', () => {
          if (this.hasAttribute('disabled') && truthy(this.getAttribute('disabled'))) return;
          if (truthy(this.getAttribute('active'))) return;
          const bar = this.closest('lol-uikit-navigation-bar');
          const type = bar && bar.getAttribute('type');
          if (type === 'nav-bar-secondary' || type === 'tabbed') uikitSound(UIKIT_SOUNDS.subnavClick);
          else if (type === 'nav-bar') uikitSound(UIKIT_SOUNDS.navClick);
          this.dispatchEvent(new CustomEvent('lol-uikit-navigation-item-click-event', { bubbles: true, composed: true, detail: { node: this } }));
        });
      }
      connectedCallback() { for (const a of ['active', 'disabled', 'alert']) this.attributeChangedCallback(a); }
      attributeChangedCallback(name) {
        const s = this.shadowRoot.querySelector('.section');
        if (s) s.classList.toggle(name, this.hasAttribute(name) && truthy(this.getAttribute(name)));
      }
    },
    // the bar: selectedindex marks the n-th item active
    'lol-uikit-navigation-bar': (Base) => class extends Base {
      static get observedAttributes() { return ['selectedindex']; }
      constructor() {
        super();
        this.addEventListener('lol-uikit-navigation-item-click-event', (e) => {
          const items = [...this.getElementsByTagName('lol-uikit-navigation-item')];
          this.setAttribute('selectedindex', items.indexOf(e.target));
        });
      }
      connectedCallback() { this.attributeChangedCallback(); }
      attributeChangedCallback() {
        const i = parseInt(this.getAttribute('selectedindex'), 10);
        if (Number.isNaN(i)) return;
        [...this.getElementsByTagName('lol-uikit-navigation-item')].forEach((it, k) => {
          if (k === i) it.setAttribute('active', 'true'); else it.removeAttribute('active');
        });
      }
    },
    'lol-uikit-radio-input-option': (Base) => class extends Base {
      static get observedAttributes() { return ['selected']; }
      constructor() {
        super();
        this.addEventListener('click', () => {
          const r = this.closest('lol-uikit-radio-input');
          if (r) r.selectOption(this);
        });
      }
      connectedCallback() { this.attributeChangedCallback(); }
      attributeChangedCallback() {
        const li = this.shadowRoot.querySelector('li');
        const on = this.getAttribute('selected') !== null;
        li.classList.toggle('ui-radio-input-option-selected', on);
        li.classList.toggle('ui-radio-input-option-unselected', !on);
      }
    },
    'lol-uikit-radio-input': (Base) => class extends Base {
      selectOption(o) {
        const cur = this.querySelector('lol-uikit-radio-input-option[selected]');
        if (o === cur) return;
        if (cur) cur.removeAttribute('selected');
        o.setAttribute('selected', true);
        const ev = new Event('selected', { bubbles: true });
        ev.selected = o;
        this.dispatchEvent(ev);
        uikitSound(UIKIT_SOUNDS.radioInputClick);
      }
    },
  };
  // uikit-state-machine: the parts of its shadow tree marked visible-state="a,b" show only in those states (the
  // regalia elements are driven straight to their non-animated state, as the client does in low spec mode)
  const applyStates = (sm) => {
    const state = sm.getAttribute('state');
    for (const n of sm.querySelectorAll('[visible-state]')) {
      if (n.closest('uikit-state-machine') !== sm) continue;
      n.style.display = n.getAttribute('visible-state').split(',').map((x) => x.trim()).includes(state) ? '' : 'none';
    }
  };
  special['uikit-state-machine'] = (Base) => class extends Base {
    static get observedAttributes() { return ['state']; }
    connectedCallback() { applyStates(this); }
    attributeChangedCallback() { applyStates(this); }
  };
  // themed level ring v2: the level picks the ring theme (_getThemeFromLevel)
  special['lol-uikit-themed-level-ring-v2'] = (Base) => class extends Base {
    static get observedAttributes() { return ['level', 'size', 'prestige-crest-id']; }
    attributeChangedCallback(name, _, v) {
      const r = this.shadowRoot.querySelector('.theme-ring-border');
      if (name === 'prestige-crest-id') r.setAttribute('theme', v);
      else if (name === 'size') r.classList.add(v);
      else {
        const lv = +v;
        r.setAttribute('theme', lv >= 1 && lv <= 29 ? 1 : lv >= 30 && lv <= 49 ? 2 : Math.min(Math.floor(lv / 25) + 1, 21));
      }
    }
  };
  // the lobby banner (lol-regalia-parties-v2-element): member type on its root, the backdrop banner and the crest.
  // The client reads the player's regalia (banner, icon, level, rank) from its back end by summoner id; this page
  // passes them as attributes (profile-icon, summoner-level) from its own player data.
  special['lol-regalia-parties-v2-element'] = (Base) => class extends Base {
    static get observedAttributes() { return ['member-type', 'profile-icon', 'summoner-level']; }
    connectedCallback() { this.render(); }
    attributeChangedCallback() { this.render(); }
    render() {
      const root = this.shadowRoot.querySelector('.regalia-parties-v2-root');
      const banner = this.shadowRoot.querySelector('.regalia-parties-v2-banner-backdrop');
      const crest = this.shadowRoot.querySelector('.regalia-parties-v2-crest-element');
      const mt = this.getAttribute('member-type') || 'current-player';
      root.setAttribute('member-type', mt);
      banner.setAttribute('member-type', mt);
      crest.setAttribute('crest-sizing', mt === 'other-player' ? 'medium' : '');
      // crest type: the player's regalia choice; 'prestige' (the level ring) for a player without a ranked crest
      // [default regalia assumed, the account service is not in the client's files]
      crest.setAttribute('crest-type', 'prestige');
      if (this.hasAttribute('profile-icon')) crest.setAttribute('profile-icon', this.getAttribute('profile-icon'));
      if (this.hasAttribute('summoner-level')) crest.setAttribute('summoner-level', this.getAttribute('summoner-level'));
    }
  };
  // banner v2: with no banner chosen the client shows generic-assets regalia-bannerskins-default.default
  special['lol-regalia-banner-v2-element'] = (Base) => class extends Base {
    static get observedAttributes() { return ['member-type']; }
    connectedCallback() {
      this.shadowRoot.querySelector('.regalia-banner-asset-static-image').src = '/lol-game-data/assets/ASSETS/Regalia/BannerSkins/default.png';
      this.shadowRoot.querySelector('.regalia-banner-state-machine').setAttribute('state', 'static');
    }
    attributeChangedCallback(_, __, v) { this.shadowRoot.querySelector('.regalia-banner-v2-root').setAttribute('member-type', v); }
  };
  // crest v2: summoner icon (profile-icons/<id>.jpg), crest type on the root, the level ring v2 (the lobby
  // challenges ring; the challenge crystal stays hidden: no challenge data for our player [approximation])
  special['lol-regalia-crest-v2-element'] = (Base) => class extends Base {
    static get observedAttributes() { return ['crest-type', 'profile-icon', 'summoner-level', 'crest-sizing']; }
    connectedCallback() {
      const sr = this.shadowRoot;
      sr.querySelector('.regalia-crest-state-machine').setAttribute('state', 'static');
      sr.querySelector('.ring-v1').classList.add('hidden');
      sr.querySelector('.ring-v2').classList.remove('hidden');
      sr.querySelector('.regalia-crystal-element-container').classList.add('hidden');
    }
    attributeChangedCallback(name, _, v) {
      const sr = this.shadowRoot;
      if (name === 'crest-type') sr.querySelector('.lol-regalia-crest-root').setAttribute('data-type', v);
      else if (name === 'profile-icon') {
        sr.querySelector('div.lol-regalia-summoner-icon').style.backgroundImage =
          `url(${+v >= 0 ? `/lol-game-data/assets/v1/profile-icons/${+v}.jpg` : '/fe/lol-static-assets/images/empty-icon.png'})`;
      } else if (name === 'summoner-level') sr.querySelector('.ring-v2').setAttribute('level', v);
      else if (name === 'crest-sizing' && v) {
        sr.querySelector('.lol-regalia-crest-root').setAttribute('size', v);
        sr.querySelector('.ring-v2').setAttribute('size', v);
      }
    }
  };
  for (const tag of Object.keys(defs)) {
    if (!defs[tag].template || customElements.get(tag)) continue;
    const Base = class extends HTMLElement {
      constructor() {
        super();
        shadow(this, tag);
      }
    };
    customElements.define(tag, special[tag] ? special[tag](Base) : Base);
  }
}
