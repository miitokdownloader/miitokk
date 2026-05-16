/* ── EFFECTS: NAVBAR + REDUCED MOTION ─────────── */
/* Dependency-free. Loads even if the MII namespace failed to set
   up so the navbar still works. Runs after the DOM is parsed
   thanks to the `defer` attribute on the <script> tag. */

(function () {
  /* Reduced-motion class so animations.css can disable transitions
     even on browsers that do not natively honor the OS setting. */
  try {
    var mq = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq && mq.matches) {
      document.documentElement.classList.add('rm');
    }
  } catch (e) { /* matchMedia not available */ }

  function bindHamburger() {
    var btn  = document.getElementById('hamburgerBtn');
    var menu = document.getElementById('navMenu');
    if (!btn || !menu) return;

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = menu.classList.toggle('open');
      btn.classList.toggle('active', isOpen);
    });

    document.addEventListener('click', function (e) {
      if (!menu.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
        menu.classList.remove('open');
        btn.classList.remove('active');
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        menu.classList.remove('open');
        btn.classList.remove('active');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindHamburger);
  } else {
    bindHamburger();
  }
})();
