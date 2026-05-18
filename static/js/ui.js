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

/* -- VIEW NAVIGATION SYSTEM -- */
(function() {
  'use strict';

  // View configuration
  var viewConfig = {
    'downloader': { type: 'main' },
    'mp3': { type: 'coming-soon', title: 'MP3 DOWNLOADER', badge: 'COMING SOON', description: 'Audio downloader is under development.' },
    'photo': { type: 'coming-soon', title: 'PHOTO DOWNLOADER', badge: 'BETA', description: 'TikTok photo slideshow support is under development.' },
    'hd-converter': { type: 'coming-soon', title: 'HD CONVERTER', badge: 'COMING SOON', description: 'Video converter is under development.' },
    'caption': { type: 'coming-soon', title: 'CAPTION COPIER', badge: 'COMING SOON', description: 'Caption copy tool is under development.' },
    'store': { type: 'store' },
    'control': { type: 'control' },
    'server': { type: 'coming-soon', title: 'SERVER STATUS', badge: 'COMING SOON', description: 'Server monitoring dashboard is under development.' },
    'howto': { type: 'coming-soon', title: 'HOW TO USE', badge: 'COMING SOON', description: 'Usage guide is under development.' },
    'report': { type: 'coming-soon', title: 'REPORT BUG', badge: 'COMING SOON', description: 'Bug reporting system is under development.' }
  };

  function navigateTo(view) {
    if (!viewConfig[view]) return;
    currentView = view;

    // Hide all views
    var viewDownloader = document.getElementById('viewDownloader');
    var viewComingSoon = document.getElementById('viewComingSoon');
    var viewStore = document.getElementById('viewStore');
    var viewControl = document.getElementById('viewControl');

    if (viewDownloader) viewDownloader.style.display = 'none';
    if (viewComingSoon) viewComingSoon.style.display = 'none';
    if (viewStore) viewStore.style.display = 'none';
    if (viewControl) viewControl.style.display = 'none';

    var config = viewConfig[view];

    if (config.type === 'main') {
      if (viewDownloader) viewDownloader.style.display = '';
    } else if (config.type === 'coming-soon') {
      renderComingSoon(config.title, config.badge, config.description);
      if (viewComingSoon) viewComingSoon.style.display = '';
    } else if (config.type === 'store') {
      renderStore();
      if (viewStore) viewStore.style.display = '';
    } else if (config.type === 'control') {
      renderControl();
      if (viewControl) viewControl.style.display = '';
    }

    // Update active state in drawer
    updateDrawerActive(view);

    // Close drawer
    if (window._closeDrawer) window._closeDrawer();

    // Scroll to top
    window.scrollTo(0, 0);
  }

  function renderComingSoon(title, badge, description) {
    var container = document.getElementById('viewComingSoon');
    if (!container) return;
    container.innerHTML = '<div class="coming-soon-card">' +
      '<div class="coming-soon-scanline"></div>' +
      '<div class="coming-soon-corner tl"></div>' +
      '<div class="coming-soon-corner tr"></div>' +
      '<div class="coming-soon-corner bl"></div>' +
      '<div class="coming-soon-corner br"></div>' +
      '<h2 class="coming-soon-title">' + title + '</h2>' +
      '<span class="coming-soon-badge">' + badge + '</span>' +
      '<p class="coming-soon-subtitle">' + description + '</p>' +
      '<button class="coming-soon-btn" onclick="showMainView()">BACK TO DOWNLOADER</button>' +
      '</div>';
  }

  function renderStore() {
    var container = document.getElementById('viewStore');
    if (!container) return;
    container.innerHTML = '<div class="store-page">' +
      '<div class="store-header">' +
        '<h2 class="store-title">PREMIUM APPS STORE</h2>' +
        '<p class="store-subtitle">MII NETWORK digital products</p>' +
      '</div>' +
      '<div class="store-grid">' +
        '<a href="https://www.instagram.com/miistore.99?igsh=ZmFqanZuOXo4cG92" target="_blank" rel="noopener noreferrer" class="store-card">' +
          '<div class="store-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="28" height="28"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><circle cx="12" cy="12" r="4.5"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg></div>' +
          '<div class="store-card-title">Instagram</div>' +
          '<div class="store-card-desc">Follow for updates</div>' +
        '</a>' +
        '<a href="https://t.me/asami_am0" target="_blank" rel="noopener noreferrer" class="store-card">' +
          '<div class="store-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="28" height="28"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></div>' +
          '<div class="store-card-title">Telegram</div>' +
          '<div class="store-card-desc">Join our channel</div>' +
        '</a>' +
        '<a href="https://wa.me/6282191223912" target="_blank" rel="noopener noreferrer" class="store-card">' +
          '<div class="store-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="28" height="28"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg></div>' +
          '<div class="store-card-title">WhatsApp</div>' +
          '<div class="store-card-desc">Chat with us</div>' +
        '</a>' +
        '<a href="https://lynk.id/miistore99" target="_blank" rel="noopener noreferrer" class="store-card">' +
          '<div class="store-card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="28" height="28"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg></div>' +
          '<div class="store-card-title">Lynk.id Store</div>' +
          '<div class="store-card-desc">Browse all products</div>' +
        '</a>' +
      '</div>' +
      '<button class="coming-soon-btn" onclick="showMainView()" style="margin-top:24px;">BACK TO DOWNLOADER</button>' +
    '</div>';
  }

  function renderControl() {
    var container = document.getElementById('viewControl');
    if (!container) return;
    container.innerHTML = '<div class="control-page">' +
      '<div class="control-header">' +
        '<h2 class="control-title">CONTROL PANEL</h2>' +
        '<p class="control-subtitle">MII NETWORK SYSTEM</p>' +
      '</div>' +
      '<div class="control-grid">' +
        '<div class="control-status-card"><span class="control-dot green"></span><span>Server Online</span></div>' +
        '<div class="control-status-card"><span class="control-dot green"></span><span>Video Ready</span></div>' +
        '<div class="control-status-card"><span class="control-dot yellow"></span><span>Photo Beta</span></div>' +
        '<div class="control-status-card"><span class="control-dot gray"></span><span>MP3 Soon</span></div>' +
      '</div>' +
      '<div class="control-stats">' +
        '<div class="control-stat-box"><div class="control-stat-value" id="ctrlViews">0</div><div class="control-stat-label">VIEWS</div></div>' +
        '<div class="control-stat-box"><div class="control-stat-value" id="ctrlDownloads">0</div><div class="control-stat-label">DOWNLOADS</div></div>' +
        '<div class="control-stat-box"><div class="control-stat-value" id="ctrlVisitors">0</div><div class="control-stat-label">VISITORS</div></div>' +
      '</div>' +
      '<button class="coming-soon-btn" onclick="showMainView()" style="margin-top:24px;">BACK TO DOWNLOADER</button>' +
    '</div>';

    // Copy stats from main page if available
    var sv = document.getElementById('statViews');
    var sd = document.getElementById('statDownloads');
    var svi = document.getElementById('statVisitors');
    var cv = document.getElementById('ctrlViews');
    var cd = document.getElementById('ctrlDownloads');
    var cvi = document.getElementById('ctrlVisitors');
    if (sv && cv) cv.textContent = sv.textContent;
    if (sd && cd) cd.textContent = sd.textContent;
    if (svi && cvi) cvi.textContent = svi.textContent;
  }

  function updateDrawerActive(view) {
    var items = document.querySelectorAll('.side-drawer .drawer-item[data-view]');
    items.forEach(function(item) {
      if (item.getAttribute('data-view') === view) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  }

  function showMainView() {
    navigateTo('downloader');
  }

  // Expose globally
  window.showMainView = showMainView;
  window.navigateTo = navigateTo;

  // Wire up drawer items with data-view
  document.addEventListener('DOMContentLoaded', function() {
    var items = document.querySelectorAll('.side-drawer .drawer-item[data-view]');
    items.forEach(function(item) {
      item.addEventListener('click', function(e) {
        e.preventDefault();
        var view = item.getAttribute('data-view');
        navigateTo(view);
      });
    });
  });
})();
