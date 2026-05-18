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
