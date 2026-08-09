/* ===========================================================
   PokeDatabase — Site Interactions
   Loaded on every page via base.html. Hero-specific effects
   check that their elements exist before running, so this is
   safe on pages that don't have a .hero section.
   All effects respect prefers-reduced-motion.
   =========================================================== */

document.addEventListener('DOMContentLoaded', () => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;

  initHeroEntrance();
  initStatCountUp();
  initFloatingArt();
  initVisualParallax();
  initCardEntrance();
  stickyNavBar();
});

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
   6. Makes the top bar sticky on scrolling
----------------------------------------------------------- */
function stickyNavBar(){
  window.onscroll = function() {myFunction()};
  
  var navlist = document.querySelector(".topbar");
  var sticky = navlist.offsetTop;
  
  /* Function to stick the nav bar */
  function myFunction() {
      if (window.pageYOffset >= sticky) {
          navlist.classList.add("sticky")
      } 
        else {
            navlist.classList.remove("sticky");
        }
  }

}

