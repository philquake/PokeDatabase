/* ===========================================================
   PokeDatabase — Site Interactions
   Loaded on every page via base.html. Hero-specific effects
   check that their elements exist before running, so this is
   safe on pages that don't have a .hero section.
   All effects respect prefers-reduced-motion.
   =========================================================== */

document.addEventListener('DOMContentLoaded', () => {
  hexChart(); 
  initLazyMovePanels();
  initCompetitiveDropdown();
  initCompetitiveNavigation();

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;

  initHeroEntrance();
  initStatCountUp();
  initFloatingArt();
  initVisualParallax();
  initCardEntrance();
  
});

function initCompetitiveDropdown() {
  const dropdown = document.querySelector('.nav-dropdown');
  if (!dropdown) return;

  const toggle = dropdown.querySelector('button.competitive');
  const setOpen = (open) => {
    dropdown.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
  };

  dropdown.addEventListener('pointerenter', (event) => {
    if (event.pointerType === 'mouse') {
      dropdown.classList.remove('is-dismissed');
      setOpen(true);
    }
  });
  dropdown.addEventListener('pointerleave', (event) => {
    if (event.pointerType === 'mouse' && !dropdown.contains(event.relatedTarget)) {
      setOpen(false);
    }
  });
  dropdown.addEventListener('focusin', () => {
    dropdown.classList.remove('is-dismissed');
    setOpen(true);
  });
  dropdown.addEventListener('focusout', (event) => {
    if (!dropdown.contains(event.relatedTarget)) setOpen(false);
  });
  toggle.addEventListener('click', () => {
    dropdown.classList.remove('is-dismissed');
    setOpen(true);
  });
  dropdown.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && dropdown.classList.contains('is-open')) {
      toggle.focus();
      dropdown.classList.add('is-dismissed');
      setOpen(false);
    }
  });
  document.addEventListener('click', (event) => {
    if (!dropdown.contains(event.target)) setOpen(false);
  });
}

/* -----------------------------------------------------------
   1. Hero entrance — staggered fade/slide-up on page load.
----------------------------------------------------------- */
function initHeroEntrance() {
  const items = document.querySelectorAll('.hero-content > *');
  if (!items.length) return;

  items.forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(16px)';
    el.style.transition = `opacity 600ms ease ${i * 90}ms, transform 600ms ease ${i * 90}ms`;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      });
    });
  });
}

/* -----------------------------------------------------------
   2. Stat count-up — 1,025 / 898 / 305 animate from 0 when
      they scroll into view.
----------------------------------------------------------- */
function initStatCountUp() {
  const stats = document.querySelectorAll('.stat-value');
  if (!stats.length) return;

  const animate = (el) => {
    const target = parseInt(el.textContent.replace(/,/g, ''), 10);
    if (Number.isNaN(target)) return;

    const duration = 1200;
    const start = performance.now();

    const step = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(eased * target).toLocaleString();
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString();
    };

    requestAnimationFrame(step);
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        animate(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.6 });

  stats.forEach((el) => observer.observe(el));
}

/* -----------------------------------------------------------
   3. Floating art — gentle bob on the featured Pokémon slot.
----------------------------------------------------------- */
function initFloatingArt() {
  const art = document.querySelector('.pokemon-image-wrap');
  if (!art) return;

  art.style.animation = 'float 4.5s ease-in-out infinite';

  const styleSheet = document.createElement('style');
  styleSheet.textContent = `
    @keyframes float {
      0%, 100% { transform: translateY(0px); }
      50%      { transform: translateY(-14px); }
    }
  `;
  document.head.appendChild(styleSheet);
}

/* -----------------------------------------------------------
   4. Visual parallax — stat tags drift with cursor movement.
----------------------------------------------------------- */
function initVisualParallax() {
  const visual = document.querySelector('.hero-visual');
  const tags = document.querySelectorAll('.pokemon-tag');
  if (!visual || !tags.length) return;

  visual.addEventListener('mousemove', (e) => {
    const rect = visual.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;

    tags.forEach((tag, i) => {
      const depth = (i + 1) * 6;
      tag.style.transform = `translate(${x * depth}px, ${y * depth}px)`;
      tag.style.transition = 'transform 200ms ease-out';
    });
  });

  visual.addEventListener('mouseleave', () => {
    tags.forEach((tag) => {
      tag.style.transform = 'translate(0, 0)';
    });
  });
}

/* -----------------------------------------------------------
   5. Card entrance — Featured Pokémon cards fade/slide up in a
      staggered wave as the grid scrolls into view.   
----------------------------------------------------------- */
function initCardEntrance() {
  const cards = document.querySelectorAll('.poke-card');
  if (!cards.length) return;

  cards.forEach((card) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(24px)';
    card.style.transition = 'opacity 500ms ease, transform 500ms ease';
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const card = entry.target;
      const index = Array.from(cards).indexOf(card);
      card.style.transitionDelay = `${(index % 4) * 80}ms`;
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
      observer.unobserve(card);
    });
  }, { threshold: 0.15 });

  cards.forEach((card) => observer.observe(card));
}

/* -----------------------------------------------------------
   6. Stat Graph - Renders a 6-axis hexagonal stat chart (HP/Atk/Def/SpA/SpD/Spe) as inline SVG
----------------------------------------------------------- */

function hexChart() {
  "use strict";

  // ---- tunables ----
  const RINGS = 4;
  const STAT_MAX = 255;   // shared ceiling so chart size is comparable across pokemon
  const SIZE = 260;
  const CENTER = SIZE / 2;
  const RADIUS = SIZE * 0.36;
  const STAT_LABELS = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"];

  const TYPE_COLORS = {
    fire: "#ee8130", water: "#6390f0", grass: "#7ac74c",
    electric: "#f7d02c", normal: "#a8a77a", psychic: "#f95587",
    ice: "#96d9d6", fighting: "#c22e28", poison: "#a33ea1",
    ground: "#e2bf65", flying: "#a98ff3", bug: "#a6b91a",
    rock: "#b6a136", ghost: "#735797", dragon: "#6f35fc",
    dark: "#705746", steel: "#b7b7ce", fairy: "#d685ad",
  };

  function pointFor(index, valueFraction) {
    const angle = (Math.PI / 3) * index - Math.PI / 2; // 60° steps, start at top
    const r = RADIUS * valueFraction;
    return [CENTER + r * Math.cos(angle), CENTER + r * Math.sin(angle)];
  }

  function polyStr(fractions) {
    return fractions
      .map((f, i) => pointFor(i, f))
      .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
      .join(" ");
  }

  /**
   * Build the chart's inner SVG markup.
   * @param {{hp:number, atk:number, def:number, spa:number, spd:number, spe:number}} stats
   * @param {string} color - hex or CSS color for the data polygon
   * @returns {string} SVG markup (no outer <svg> wrapper — caller supplies that)
   */
  function buildHexChart(stats, color) {
    const values = [stats.hp, stats.atk, stats.def, stats.spa, stats.spd, stats.spe];

    let grid = "";
    for (let r = 1; r <= RINGS; r++) {
      const frac = r / RINGS;
      grid += `<polygon points="${polyStr(Array(6).fill(frac))}"
        fill="none" stroke="var(--hex-grid)" stroke-width="1"
        opacity="${r === RINGS ? 0.9 : 0.45}"/>`;
    }

    let axes = "";
    for (let i = 0; i < 6; i++) {
      const [x, y] = pointFor(i, 1);
      axes += `<line x1="${CENTER}" y1="${CENTER}" x2="${x}" y2="${y}"
        stroke="var(--hex-grid)" stroke-width="1" opacity="0.45"/>`;
    }

    const dataPoints = values.map((v, i) => pointFor(i, Math.min(v / STAT_MAX, 1)));
    const dataPoly = `<polygon points="${dataPoints
      .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
      .join(" ")}" fill="${color}" fill-opacity="0.28"
      stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/>`;

    let dots = "";
    let labels = "";
    values.forEach((v, i) => {
      const [x, y] = dataPoints[i];
      dots += `<circle cx="${x}" cy="${y}" r="3.2" fill="${color}"/>`;

      const [lx, ly] = pointFor(i, 1.24);
      labels += `
        <text x="${lx}" y="${ly - 4}" text-anchor="middle"
          font-size="10.5" font-weight="700" fill="var(--hex-muted)"
          letter-spacing="0.04em">${STAT_LABELS[i]}</text>
        <text x="${lx}" y="${ly + 9}" text-anchor="middle"
          font-size="11" font-weight="700" fill="var(--hex-text)">${v}</text>`;
    });

    return `${grid}${axes}${dataPoly}${dots}${labels}`;
  }

  /**
   * Render a chart into a container element.
   * @param {HTMLElement} container
   * @param {object} stats
   * @param {string} type - pokemon type, used to pick a color from TYPE_COLORS
   */
  function renderHexChart(container, stats, type) {
    const color = TYPE_COLORS[(type || "").toLowerCase()] || "#a8a77a";
    const total = Object.values(stats).reduce((a, b) => a + b, 0);

    container.innerHTML = `
      <svg class="hex-chart" viewBox="0 0 ${SIZE} ${SIZE}">
        ${buildHexChart(stats, color)}
      </svg>
      <div class="hex-chart-total">Base stat total: <b>${total}</b></div>
    `;
  }

  /**
   * Auto-init: finds every element with [data-hex-chart] and renders it,
   * reading stats from data-stats (JSON) and type from data-type.
   * Markup example:
   *   <div data-hex-chart data-type="fire"
   *        data-stats='{"hp":78,"atk":84,"def":78,"spa":109,"spd":85,"spe":100}'></div>
   */
  function initAll(root) {
  (root || document).querySelectorAll("[data-hex-chart]").forEach((el) => {
    try {
      const dataEl = document.getElementById(el.dataset.statsId);
      const raw = JSON.parse(dataEl.textContent);
      const stats = {
        hp: raw.HP, atk: raw.Attack, def: raw.Defense,
        spa: raw["Special Attack"], spd: raw["Special Defense"], spe: raw.Speed,
      };
      renderHexChart(el, stats, el.dataset.type);
    } catch (err) {
      console.error("hex-chart: invalid stats data on", el, err);
    }
  });
  }

  initAll();

  // Expose for manual use (e.g. re-render after an AJAX search result swap)
  window.HexChart = { renderHexChart, buildHexChart, initAll };
}


/* -----------------------------------------------------------
   Lazy move tables — the Moves tab only renders the visible game;
   the other games' tables are fetched when their tab is first shown.
   (Runs regardless of reduced-motion: it is functional, not decorative.)
   ----------------------------------------------------------- */
function initLazyMovePanels() {
  const loadPane = async (pane) => {
    const src = pane.dataset.src;
    if (!src || pane.dataset.loading) return;
    pane.dataset.loading = '1';
    try {
      const response = await fetch(src, { headers: { 'X-Requested-With': 'fetch' } });
      if (!response.ok) throw new Error(response.status);
      pane.innerHTML = await response.text();
      delete pane.dataset.src;
    } catch (err) {
      pane.innerHTML = '<p class="detail-empty">Couldn\u2019t load these moves. Switch tabs and back to try again.</p>';
    } finally {
      delete pane.dataset.loading;
    }
  };

  document.addEventListener('shown.bs.tab', (event) => {
    const target = event.target.getAttribute('data-bs-target');
    const pane = target && document.querySelector(target);
    if (!pane) return;
    // The shown pane is either a game pane, or a generation pane whose active game may still be unloaded.
    pane.querySelectorAll('.moves-lazy[data-src]').forEach((el) => {
      // Active AND on screen: every generation has an "active" first game, but only the shown generation's is visible.
      if (el.closest('.tab-pane').classList.contains('active') && el.offsetParent !== null) loadPane(el);
    });
  });
}

/* -----------------------------------------------------------
   Competitive rankings — update same-page filters, sorting,
   and pagination without a full document navigation.
----------------------------------------------------------- */
function initCompetitiveNavigation() {
  let activeRequest = null;

  const navigate = async (url, addHistoryEntry = true) => {
    if (activeRequest) activeRequest.abort();
    const controller = new AbortController();
    activeRequest = controller;
    const currentPage = document.querySelector('[data-async-page="competitive"]');
    const status = document.querySelector('[data-navigation-status]');
    if (!currentPage) return;

    currentPage.setAttribute('aria-busy', 'true');
    if (status) status.textContent = 'Updating rankings…';

    try {
      const response = await fetch(url, {
        headers: { 'X-Requested-With': 'fetch' },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Rankings request failed (${response.status})`);
      const html = await response.text();
      const documentFromResponse = new DOMParser().parseFromString(html, 'text/html');
      const nextPage = documentFromResponse.querySelector('[data-async-page="competitive"]');
      if (!nextPage) throw new Error('Rankings content was missing from the response');

      if (activeRequest !== controller) return;
      currentPage.replaceWith(nextPage);
      if (status) status.textContent = 'Rankings updated.';
      if (addHistoryEntry) {
        window.history.pushState({}, '', url);
      }
    } catch (error) {
      if (error.name === 'AbortError' || activeRequest !== controller) return;
      console.error('Could not update competitive rankings:', error);
      if (status) status.textContent = 'Rankings could not update in place. Loading the selected view instead.';
      window.location.assign(url);
    } finally {
      if (activeRequest === controller) {
        activeRequest = null;
        const page = document.querySelector('[data-async-page="competitive"]');
        if (page) page.removeAttribute('aria-busy');
      }
    }
  };

  document.addEventListener('click', (event) => {
    const link = event.target.closest('[data-async-page="competitive"] a');
    if (!link || event.defaultPrevented || event.button !== 0 ||
        event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

    const url = new URL(link.href, window.location.href);
    if (url.origin !== window.location.origin || url.pathname !== window.location.pathname) return;
    event.preventDefault();
    navigate(url);
  });

  document.addEventListener('submit', (event) => {
    const form = event.target.closest('[data-async-page="competitive"] .filters-rank');
    if (!form) return;
    event.preventDefault();

    const url = new URL(form.action, window.location.href);
    url.search = new URLSearchParams(new FormData(form)).toString();
    navigate(url);
  });

  window.addEventListener('popstate', () => {
    if (document.querySelector('[data-async-page="competitive"]')) {
      navigate(new URL(window.location.href), false);
    }
  });
}
