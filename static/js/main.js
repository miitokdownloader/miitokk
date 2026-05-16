/* ── MIITOK BOOTSTRAP ─────────────────────────── */
/* This file used to be the 354-line monolithic frontend script.
   It has been split into config.js / ui.js / downloader.js /
   photo.js / effects.js. main.js is now the slim bootstrap that
   confirms the namespace is wired up; the inline onclick / oninput
   attributes in templates/index.html remain the canonical bindings
   and resolve to window.* functions installed by the modules above. */

(function () {
  if (!window.MII) {
    console.error('[miitok] bootstrap: window.MII missing - config.js failed to load');
    return;
  }

  var required = [
    'setQuality', 'onUrlInput', 'clearUrl',
    'openModal', 'closeModal', 'backdropClick', 'copyLink',
    'confirmDownload', 'fetchPreview',
    'fetchPhotos', 'renderCarousel', 'downloadPhoto',
    'downloadAllPhotos', 'carouselScroll',
    'setStatus', 'hidePreview'
  ];

  var missing = [];
  for (var i = 0; i < required.length; i++) {
    if (typeof window[required[i]] !== 'function') missing.push(required[i]);
  }
  if (missing.length) {
    console.error('[miitok] bootstrap: missing handlers ->', missing.join(', '));
  }
})();
