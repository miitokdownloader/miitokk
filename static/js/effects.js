/* ── EFFECTS ──────────────────────────────────── */
/* Lightweight CSS-driven effects for the Control Panel */

(function() {
  'use strict';

  /* Add scanline overlay to stats section via CSS class */
  function initScanline() {
    var stats = document.querySelector('.stats-section');
    if (!stats) return;
    var scanline = document.createElement('div');
    scanline.className = 'stats-scanline';
    stats.appendChild(scanline);
  }

  /* IntersectionObserver to trigger counter animation when stats visible */
  function initStatsObserver() {
    var statsSection = document.querySelector('.stats-section');
    if (!statsSection) return;

    var hasAnimated = false;

    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting && !hasAnimated) {
          hasAnimated = true;
          statsSection.classList.add('stats-visible');
          addGlowOnComplete();
        }
      });
    }, { threshold: 0.3 });

    observer.observe(statsSection);
  }

  /* Add glow class to stat values after counting completes.
     The counter in analytics.js runs for 1500ms starting on DOMContentLoaded.
     If the section becomes visible after the counter already finished,
     apply the glow immediately. Otherwise wait for the counter duration. */
  function addGlowOnComplete() {
    var values = document.querySelectorAll('.stat-value');
    var pageLoadTime = window.__effectsLoadTime || Date.now();
    var counterDuration = 1600; // slightly above analytics.js 1500ms
    var elapsed = Date.now() - pageLoadTime;
    var remaining = Math.max(0, counterDuration - elapsed);

    setTimeout(function() {
      values.forEach(function(el) {
        el.classList.add('counter-done');
      });
    }, remaining);
  }

  /* Record load time so we can calculate counter elapsed */
  window.__effectsLoadTime = Date.now();

  /* Initialize on DOM ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      initScanline();
      initStatsObserver();
    });
  } else {
    initScanline();
    initStatsObserver();
  }
})();

/* ── INTERACTIVE ORBS ─────────────────────────── */
(function() {
  'use strict';

  var MAX_ORBS = 12;
  var orbContainer = document.getElementById('orbContainer');
  if (!orbContainer) return;

  var activeOrbs = [];
  var lastTouchMove = 0;
  var lastMouseMove = 0;

  function createOrb(x, y, isSmall) {
    var orb = document.createElement('div');
    orb.className = 'touch-orb' + (isSmall ? ' orb-small' : '');
    var size = isSmall ? 40 : 80;
    orb.style.left = (x - size / 2) + 'px';
    orb.style.top = (y - size / 2) + 'px';
    orbContainer.appendChild(orb);
    activeOrbs.push(orb);

    if (activeOrbs.length > MAX_ORBS) {
      var oldest = activeOrbs.shift();
      if (oldest.parentNode) {
        oldest.parentNode.removeChild(oldest);
      }
    }

    setTimeout(function() {
      if (orb.parentNode) {
        orb.parentNode.removeChild(orb);
      }
      var idx = activeOrbs.indexOf(orb);
      if (idx > -1) {
        activeOrbs.splice(idx, 1);
      }
    }, 800);
  }

  document.addEventListener('click', function(e) {
    createOrb(e.clientX, e.clientY, false);
  });

  document.addEventListener('touchstart', function(e) {
    if (e.touches && e.touches.length > 0) {
      createOrb(e.touches[0].clientX, e.touches[0].clientY, false);
    }
  }, { passive: true });

  document.addEventListener('touchmove', function(e) {
    var now = Date.now();
    if (now - lastTouchMove < 50) return;
    lastTouchMove = now;
    if (e.touches && e.touches.length > 0) {
      createOrb(e.touches[0].clientX, e.touches[0].clientY, false);
    }
  }, { passive: true });

  document.addEventListener('mousemove', function(e) {
    var now = Date.now();
    if (now - lastMouseMove < 100) return;
    lastMouseMove = now;
    createOrb(e.clientX, e.clientY, true);
  });
})();
