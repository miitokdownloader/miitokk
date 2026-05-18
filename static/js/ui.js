/* ── UI HELPERS ────────────────────────────────── */

function setStatus(msg, type) {
  var el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status' + (type ? ' ' + type : '');
}

function hidePreview() {
  previewData = null;
  document.getElementById('previewCard').classList.remove('show');
}

/* ── SIDE DRAWER ──────────────────────────────── */
(function() {
  var btn = document.getElementById('hamburgerBtn');
  var drawer = document.getElementById('sideDrawer');
  var overlay = document.getElementById('drawerOverlay');
  var closeBtn = document.getElementById('drawerClose');

  if (!btn || !drawer || !overlay) return;

  function openDrawer() {
    drawer.classList.add('active');
    overlay.classList.add('active');
    drawer.setAttribute('aria-hidden', 'false');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    drawer.classList.remove('active');
    overlay.classList.remove('active');
    drawer.setAttribute('aria-hidden', 'true');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  // Expose closeDrawer for use by navigation logic
  window._closeDrawer = closeDrawer;

  btn.addEventListener('click', function(e) {
    e.stopPropagation();
    openDrawer();
  });

  overlay.addEventListener('click', function() {
    closeDrawer();
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', function() {
      closeDrawer();
    });
  }

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && drawer.classList.contains('active')) {
      closeDrawer();
    }
  });

  // Update downloads counter in drawer if statDownloads exists
  var statDl = document.getElementById('statDownloads');
  var drawerDl = document.getElementById('drawerDownloads');
  if (statDl && drawerDl) {
    var observer = new MutationObserver(function() {
      drawerDl.textContent = 'Downloads: ' + (statDl.textContent || '0');
    });
    observer.observe(statDl, { childList: true, characterData: true, subtree: true });
  }
})();

/* ── DRAWER NAVIGATION ────────────────────────── */
(function() {
  'use strict';

  var comingSoonFeatures = {
    'MP3 Downloader': true,
    'Photo Downloader': false,
    'HD Converter': true,
    'Caption Copier': true,
    'Control Panel': true,
    'Server Status': true,
    'How To Use': true,
    'Report Bug': true,
    'Dashboard': true
  };

  function showComingSoon(title) {
    var section = document.getElementById('comingSoonSection');
    var titleEl = document.getElementById('comingSoonTitle');
    var card = document.querySelector('.card');
    var features = document.querySelector('.features-section');
    var stats = document.querySelector('.stats-section');
    var social = document.querySelector('.social-section');

    if (titleEl) titleEl.textContent = title.toUpperCase();
    if (section) { section.style.display = 'block'; }
    if (card) card.style.display = 'none';
    if (features) features.style.display = 'none';
    if (stats) stats.style.display = 'none';
    if (social) social.style.display = 'none';

    window.location.hash = '#coming-soon';
  }

  function showMainView() {
    var section = document.getElementById('comingSoonSection');
    var card = document.querySelector('.card');
    var features = document.querySelector('.features-section');
    var stats = document.querySelector('.stats-section');
    var social = document.querySelector('.social-section');

    if (section) section.style.display = 'none';
    if (card) card.style.display = '';
    if (features) features.style.display = '';
    if (stats) stats.style.display = '';
    if (social) social.style.display = '';

    if (window.location.hash === '#coming-soon') {
      history.replaceState(null, '', window.location.pathname);
    }
  }

  // Expose globally
  window.showComingSoon = showComingSoon;
  window.showMainView = showMainView;

  // Handle browser back button
  window.addEventListener('hashchange', function() {
    if (window.location.hash !== '#coming-soon') {
      showMainView();
    }
  });

  // Wire up drawer items
  var drawerItems = document.querySelectorAll('.side-drawer .drawer-item');
  drawerItems.forEach(function(item) {
    var textEl = item.querySelector('.drawer-item-text');
    if (!textEl) return;
    var text = textEl.textContent.trim();

    if (text === 'TikTok Downloader') {
      item.addEventListener('click', function(e) {
        e.preventDefault();
        if (window._closeDrawer) window._closeDrawer();
        showMainView();
      });
    } else if (comingSoonFeatures[text]) {
      item.addEventListener('click', function(e) {
        e.preventDefault();
        if (window._closeDrawer) window._closeDrawer();
        showComingSoon(text);
      });
    }
  });
})();
