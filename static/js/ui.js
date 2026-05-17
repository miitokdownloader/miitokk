/* ── UI HELPERS ────────────────────────────────── */

function setStatus(msg, type) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status' + (type ? ' ' + type : '');
}

function hidePreview() {
  previewData = null;
  document.getElementById('previewCard').classList.remove('show');
}

/* ── NAVBAR HAMBURGER ─────────────────────────── */
/* Supports nav-menu-header and nav-menu-status elements inside .nav-menu */
(function() {
  const btn  = document.getElementById('hamburgerBtn');
  const menu = document.getElementById('navMenu');
  if (!btn || !menu) return;

  btn.addEventListener('click', function(e) {
    e.stopPropagation();
    const isOpen = menu.classList.toggle('open');
    btn.classList.toggle('active', isOpen);
  });

  document.addEventListener('click', function(e) {
    if (!menu.contains(e.target) && e.target !== btn) {
      menu.classList.remove('open');
      btn.classList.remove('active');
    }
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      menu.classList.remove('open');
      btn.classList.remove('active');
    }
  });
})();
