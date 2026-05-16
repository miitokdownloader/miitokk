/* ── UI: STATUS / INPUT / QUALITY / MODAL ─────── */
/* Depends on: config.js. Exposes the inline-handler entry points
   the template references via onclick / oninput attributes. */

(function () {
  var MII = window.MII;
  if (!MII) {
    console.error('[miitok] ui.js loaded before config.js - window.MII missing');
    return;
  }

  function $(id) { return document.getElementById(id); }

  function setStatus(msg, type) {
    var el = $('status');
    if (!el) return;
    el.textContent = msg || '';
    el.className = 'status' + (type ? ' ' + type : '');
  }

  function hidePreview() {
    MII.state.previewData = null;
    var card = $('previewCard');
    if (card) card.classList.remove('show');
  }

  function clearPhotoSection() {
    var section  = $('photoSection');
    var carousel = $('photoCarousel');
    var countEl  = $('photoCount');
    var dlAll    = $('downloadAllBtn');
    if (section)  section.style.display = 'none';
    if (carousel) carousel.innerHTML = '';
    if (countEl)  countEl.textContent = '';
    if (dlAll)    dlAll.style.display = 'none';
    MII.state.photoUrls = [];
  }

  function looksLikeTikTokUrl(val) {
    return val && val.length > 10 &&
      (val.indexOf('tiktok.com') !== -1 || val.indexOf('vt.tiktok') !== -1);
  }

  function setQuality(el, q) {
    MII.state.isDownloading = false;
    setStatus('', '');
    hidePreview();
    clearPhotoSection();

    var buttons = document.querySelectorAll('.q-btn');
    for (var i = 0; i < buttons.length; i++) buttons[i].classList.remove('active');
    if (el && el.classList) el.classList.add('active');

    MII.state.selectedQuality = q;

    var dlWrap = $('dlWrap');
    if (q === 'photo') {
      MII.state.isPhotoMode = true;
      if (dlWrap) dlWrap.style.display = 'none';
      var inputEl = $('urlInput');
      var val = inputEl ? inputEl.value.trim() : '';
      if (looksLikeTikTokUrl(val) && typeof window.fetchPhotos === 'function') {
        window.fetchPhotos(val);
      }
    } else {
      MII.state.isPhotoMode = false;
      if (dlWrap) dlWrap.style.display = '';
    }
  }

  function onUrlInput() {
    var input = $('urlInput');
    if (!input) return;
    var val = input.value.trim();
    var clearBtn = $('clearBtn');
    if (clearBtn) clearBtn.classList.toggle('visible', val.length > 0);

    clearTimeout(MII.state.previewTimer);
    hidePreview();
    setStatus('', '');

    if (!looksLikeTikTokUrl(val)) return;

    if (MII.state.isPhotoMode) {
      MII.state.previewTimer = setTimeout(function () {
        if (typeof window.fetchPhotos === 'function') window.fetchPhotos(val);
      }, MII.debounceMs);
    } else {
      MII.state.previewTimer = setTimeout(function () {
        if (typeof window.fetchPreview === 'function') window.fetchPreview(val);
      }, MII.debounceMs);
    }
  }

  function clearUrl() {
    var input = $('urlInput');
    if (input) input.value = '';
    var clearBtn = $('clearBtn');
    if (clearBtn) clearBtn.classList.remove('visible');
    clearTimeout(MII.state.previewTimer);
    hidePreview();
    setStatus('', '');
    clearPhotoSection();
  }

  function openModal() {
    var input = $('urlInput');
    var url = input ? input.value.trim() : '';
    if (!url) {
      setStatus('Paste TikTok link first.', 'err');
      return;
    }

    var preview = MII.state.previewData;
    var modalTitle    = $('modalTitle');
    var modalUploader = $('modalUploader');
    var modalThumb    = $('modalThumb');

    if (preview) {
      if (modalTitle)    modalTitle.textContent = preview.title || 'TikTok Video';
      if (modalUploader) modalUploader.textContent = preview.uploader ? '@' + preview.uploader : '';
      if (modalThumb) {
        if (preview.thumbnail) {
          modalThumb.src = preview.thumbnail;
          modalThumb.classList.add('show');
        } else {
          modalThumb.classList.remove('show');
        }
      }
    } else {
      if (modalTitle)    modalTitle.textContent = 'TikTok Video';
      if (modalUploader) modalUploader.textContent = '';
      if (modalThumb)    modalThumb.classList.remove('show');
    }

    var pills = $('modalPills');
    if (pills) {
      pills.innerHTML = '';
      var qLabel = MII.labels.quality[MII.state.selectedQuality] || MII.state.selectedQuality;
      var tLabel = MII.labels.type[MII.state.selectedQuality] || 'MP4';
      var qPill = document.createElement('span');
      qPill.className = 'pill highlight';
      qPill.textContent = qLabel;
      pills.appendChild(qPill);
      var tPill = document.createElement('span');
      tPill.className = 'pill';
      tPill.textContent = tLabel;
      pills.appendChild(tPill);
    }

    var backdrop = $('modalBackdrop');
    if (backdrop) backdrop.classList.add('show');
  }

  function closeModal() {
    var backdrop = $('modalBackdrop');
    if (backdrop) backdrop.classList.remove('show');
  }

  function backdropClick(event) {
    var backdrop = $('modalBackdrop');
    if (event && event.target === backdrop) closeModal();
  }

  function copyLink() {
    var input = $('urlInput');
    var url = input ? input.value.trim() : '';
    if (url && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).catch(function () {});
    }
    closeModal();
  }

  /* Expose to globals so the inline onclick / oninput attributes
     in templates/index.html can reach them. */
  window.setStatus     = setStatus;
  window.hidePreview   = hidePreview;
  window.setQuality    = setQuality;
  window.onUrlInput    = onUrlInput;
  window.clearUrl      = clearUrl;
  window.openModal     = openModal;
  window.closeModal    = closeModal;
  window.backdropClick = backdropClick;
  window.copyLink      = copyLink;
})();
