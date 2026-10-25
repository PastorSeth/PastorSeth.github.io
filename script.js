/* Seth Peacock — site interactions. No dependencies. */

/* ---------- Nav menu (mobile overlay) ---------- */
function initNav() {
  const nav = document.getElementById('nav');
  const toggle = nav.querySelector('.nav__toggle');
  const menu = document.getElementById('nav-menu');

  const setOpen = (open) => {
    nav.classList.toggle('is-open', open);
    document.body.classList.toggle('menu-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  };

  toggle.addEventListener('click', () => setOpen(!nav.classList.contains('is-open')));
  menu.addEventListener('click', (e) => { if (e.target.closest('a')) setOpen(false); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && nav.classList.contains('is-open')) {
      setOpen(false);
      toggle.focus();
    }
  });
}

/* ---------- Video modal (welcome video + sermons) ---------- */
const YOUTUBE_ID = /^[A-Za-z0-9_-]{11}$/;
let videoOpener = null;

function videoModal() {
  return document.getElementById('video-modal');
}

function clearVideo() {
  const dialog = videoModal();
  dialog.querySelector('.video-frame').replaceChildren();
  dialog.querySelector('.video-modal__title').textContent = '';
}

function openVideo(id, title) {
  const dialog = videoModal();
  const frame = dialog.querySelector('.video-frame');
  clearVideo();

  if (YOUTUBE_ID.test(id || '')) {
    const iframe = document.createElement('iframe');
    iframe.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`;
    iframe.title = title || 'Video';
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture';
    iframe.allowFullscreen = true;
    frame.append(iframe);
  } else {
    const soon = document.createElement('p');
    soon.className = 'video-soon';
    soon.textContent = 'Video coming soon!';
    frame.append(soon);
  }
  dialog.querySelector('.video-modal__title').textContent = title || '';

  videoOpener = document.activeElement;
  dialog.showModal();
}

function closeVideo() {
  const dialog = videoModal();
  if (dialog.open) dialog.close();
}

function initVideoModal() {
  const dialog = videoModal();

  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-video-id]');
    if (trigger) openVideo(trigger.dataset.videoId, trigger.dataset.videoTitle);
  });

  dialog.querySelector('.video-close').addEventListener('click', closeVideo);
  // A click on the dialog element itself is a click on the backdrop.
  dialog.addEventListener('click', (e) => { if (e.target === dialog) closeVideo(); });
  // Fires for every close path (button, backdrop, Escape): stop playback, restore focus.
  dialog.addEventListener('close', () => {
    clearVideo();
    if (videoOpener && videoOpener.focus) videoOpener.focus();
    videoOpener = null;
  });
}

/* ---------- Motion ---------- */
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function countUp(el) {
  if (el.dataset.counted) return;
  el.dataset.counted = 'true';
  const target = Number(el.dataset.count);
  const suffix = el.dataset.suffix || '';
  if (prefersReducedMotion) { el.textContent = target + suffix; return; }

  const duration = 1200;
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(target * eased) + suffix;
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function initReveal() {
  const items = document.querySelectorAll('[data-reveal]');
  const show = (el) => {
    el.classList.add('is-visible');
    el.querySelectorAll('[data-count]').forEach(countUp);
  };

  // Printing or "Save as PDF": everything visible, real numbers.
  window.addEventListener('beforeprint', () => {
    items.forEach((el) => el.classList.add('is-visible'));
    document.querySelectorAll('[data-count]').forEach((el) => {
      el.dataset.counted = 'true';
      el.textContent = el.dataset.count + (el.dataset.suffix || '');
    });
  });

  if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    items.forEach(show);
    return;
  }

  // Numbers start at 0 and count up when revealed (HTML holds the real value for no-JS visitors).
  document.querySelectorAll('[data-count]').forEach((el) => { el.textContent = '0'; });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      show(entry.target);
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.15 });
  items.forEach((el) => observer.observe(el));
}

// The timeline's line grows as you scroll through the experience section.
function initTimelineLine() {
  const timeline = document.querySelector('.timeline');
  const line = timeline && timeline.querySelector('.timeline__line');
  if (!line || prefersReducedMotion) return;

  let ticking = false;
  const update = () => {
    ticking = false;
    const rect = timeline.getBoundingClientRect();
    const progress = (window.innerHeight * 0.75 - rect.top) / rect.height;
    line.style.setProperty('--progress', Math.min(1, Math.max(0, progress)).toFixed(3));
  };
  window.addEventListener('scroll', () => {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  window.addEventListener('resize', update);
  update();
}

// Hero art: the stained-glass window, drifting specks of light, and the photo's block-by-block reveal.
function initHeroArt() {
  const jewels = ['var(--gold)', 'var(--ruby)', 'var(--sapphire)', 'var(--emerald)', 'var(--violet)'];

  const glass = document.querySelector('.hero__window');
  if (glass) {
    const cells = document.createDocumentFragment();
    for (let r = 0; r < 13; r++) {
      for (let c = 0; c < 10; c++) {
        const cell = document.createElement('span');
        cell.className = 'hero__glass';
        cell.style.background = jewels[Math.floor(Math.abs(c - 4.5) + Math.abs(r - 5)) % jewels.length];
        cell.style.setProperty('--d', (((r * 7 + c * 13) % 23) * 0.05 + 0.15).toFixed(2) + 's');
        cells.append(cell);
      }
    }
    glass.prepend(cells);
  }

  if (prefersReducedMotion) return;

  const motes = document.querySelector('.hero__motes');
  if (motes) {
    for (let i = 0; i < 14; i++) {
      const mote = document.createElement('span');
      const size = 4 + (i % 3) * 2;
      mote.className = 'mote';
      mote.style.left = ((i * 41) % 96) + 2 + '%';
      mote.style.width = mote.style.height = size + 'px';
      mote.style.background = jewels[i % 4];
      mote.style.animationDuration = (7 + (i % 5) * 1.3).toFixed(1) + 's';
      mote.style.animationDelay = ((i * 0.71) % 7).toFixed(2) + 's';
      motes.append(mote);
    }
  }

  const pixels = document.querySelector('.welcome__pixels');
  if (pixels) {
    for (let i = 0; i < 48; i++) {
      const px = document.createElement('span');
      px.style.setProperty('--d', (((i * 29) % 48) * 0.025 + 1.4).toFixed(3) + 's');
      pixels.append(px);
    }
  }
}

function initFooterYear() {
  document.querySelectorAll('.footer__year').forEach((el) => { el.textContent = new Date().getFullYear(); });
}

document.addEventListener('DOMContentLoaded', () => {
  // Reveal first, then mark the page ready (the inline fallback in <head> stands down).
  initReveal();
  window.siteReady = true;
  // Each extra runs on its own, so one broken piece (say, an edited-out menu) can't stop the rest.
  [initNav, initVideoModal, initHeroArt, initTimelineLine, initFooterYear].forEach((init) => {
    try { init(); } catch (err) { console.error(err); }
  });
});
