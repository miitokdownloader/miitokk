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

  /* Add glow class to stat values after counting completes */
  function addGlowOnComplete() {
    setTimeout(function() {
      var values = document.querySelectorAll('.stat-value');
      values.forEach(function(el) {
        el.classList.add('counter-done');
      });
    }, 2200);
  }

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
