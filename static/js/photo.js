/* ── PHOTO / SLIDESHOW MODE ───────────────────── */
/* Depends on: config.js, ui.js. Wires the carousel, single-photo
   download and DOWNLOAD ALL flow against the backend endpoints
   /photos, /photo-proxy and /download-photo. */

(function () {
  var MII = window.MII;
  if (!MII) {
    console.error('[miitok] photo.js loaded before config.js - window.MII missing');
    return;
  }

  function $(id) { return document.getElementById(id); }

  async function fetchPhotos(url) {
    if (MII.state.isDownloading) return;
    MII.state.isDownloading = true;

    var spinner = $('spinnerWrap');
    var section = $('photoSection');
    if (spinner) spinner.classList.add('show');
    if (section) section.style.display = 'none';
    if (typeof window.setStatus === 'function') window.setStatus('', '');

    try {
      var fd = new FormData();
      fd.append('url', url);
      var res = await fetch(MII.endpoints.photos, { method: 'POST', body: fd });
      var data = await res.json();
      if (data.error) {
        if (typeof window.setStatus === 'function') window.setStatus(data.error, 'err');
        return;
      }
      renderCarousel(data.photos || []);

      if (data.title || data.uploader || data.thumbnail) {
        var preview = {
          title:     data.title || '',
          uploader:  data.uploader || '',
          thumbnail: data.thumbnail || null
        };
        MII.state.previewData = preview;
        var titleEl    = $('previewTitle');
        var uploaderEl = $('previewUploader');
        var durationEl = $('previewDuration');
        var thumbEl    = $('previewThumb');
        var card       = $('previewCard');
        if (titleEl)    titleEl.textContent = preview.title;
        if (uploaderEl) uploaderEl.textContent = preview.uploader ? '@' + preview.uploader : '';
        if (durationEl) durationEl.textContent = '';
        if (thumbEl && preview.thumbnail) thumbEl.src = preview.thumbnail;
        if (card) card.classList.add('show');
      }
    } catch (e) {
      if (typeof window.setStatus === 'function') {
        window.setStatus('Terjadi kesalahan saat mengambil foto.', 'err');
      }
    } finally {
      MII.state.isDownloading = false;
      if (spinner) spinner.classList.remove('show');
    }
  }

  function renderCarousel(photos) {
    if (!MII.state.isPhotoMode) return;
    var carousel = $('photoCarousel');
    var countEl  = $('photoCount');
    var dlAllBtn = $('downloadAllBtn');
    var section  = $('photoSection');
    if (!carousel || !countEl || !dlAllBtn || !section) return;

    carousel.innerHTML = '';

    if (!photos || !photos.length) {
      if (typeof window.setStatus === 'function') {
        window.setStatus('Tidak ada foto ditemukan. Link ini mungkin video, bukan slideshow.', 'err');
      }
      countEl.textContent = '';
      dlAllBtn.style.display = 'none';
      section.style.display = 'none';
      MII.state.photoUrls = [];
      return;
    }

    MII.state.photoUrls = photos.slice();
    var visibleCount = photos.length;
    countEl.textContent = 'Photos found: ' + visibleCount;
    countEl.style.color = 'rgba(204,0,0,0.8)';

    function updatePhotoCount() {
      // Recompute from visible cards so the count never overstates what the
      // user can actually see (img.onerror hides cards in place).
      var stillVisible = 0;
      var nodes = carousel.querySelectorAll('.photo-card');
      for (var n = 0; n < nodes.length; n++) {
        if (nodes[n].style.display !== 'none') stillVisible++;
      }
      countEl.textContent = 'Photos found: ' + stillVisible;
    }

    photos.forEach(function (url, i) {
      var card = document.createElement('div');
      card.className = 'photo-card';

      var img = document.createElement('img');
      img.src     = MII.endpoints.photoProxy + '?url=' + encodeURIComponent(url);
      img.alt     = 'Photo ' + (i + 1);
      img.loading = 'lazy';
      img.onerror = (function (cardEl) {
        return function () {
          cardEl.style.display = 'none';
          updatePhotoCount();
        };
      })(card);

      var footer = document.createElement('div');
      footer.className = 'photo-card-footer';

      var btn = document.createElement('button');
      btn.className   = 'photo-dl-btn';
      btn.textContent = 'DOWNLOAD PHOTO';
      btn.onclick     = (function (u, idx) {
        return function () { downloadPhoto(u, idx); };
      })(url, i + 1);

      footer.appendChild(btn);
      card.appendChild(img);
      card.appendChild(footer);
      carousel.appendChild(card);
    });

    dlAllBtn.style.display = 'inline-block';
    section.style.display  = 'block';
  }

  async function downloadPhoto(url, index) {
    try {
      var filename = 'miitok_photo_' + index + '.jpg';
      var endpoint = MII.endpoints.downloadPhoto +
        '?url=' + encodeURIComponent(url) +
        '&filename=' + encodeURIComponent(filename);
      var res = await fetch(endpoint);
      if (!res.ok) {
        if (typeof window.setStatus === 'function') {
          window.setStatus('Gagal mengunduh foto ' + index, 'err');
        }
        return;
      }
      var blob    = await res.blob();
      var blobUrl = URL.createObjectURL(blob);
      var a       = document.createElement('a');
      a.href      = blobUrl;
      a.download  = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
      }, 1000);
    } catch (e) {
      if (typeof window.setStatus === 'function') {
        window.setStatus('Gagal mengunduh foto ' + index, 'err');
      }
    }
  }

  async function downloadAllPhotos() {
    var urls = MII.state.photoUrls;
    if (!urls || !urls.length) return;
    if (typeof window.setStatus === 'function') {
      window.setStatus('Mengunduh ' + urls.length + ' foto...', 'ok');
    }
    for (var i = 0; i < urls.length; i++) {
      await downloadPhoto(urls[i], i + 1);
      if (i < urls.length - 1) {
        await new Promise(function (resolve) { setTimeout(resolve, 350); });
      }
    }
    if (typeof window.setStatus === 'function') {
      window.setStatus('Semua foto berhasil diunduh!', 'ok');
    }
  }

  function carouselScroll(direction) {
    var carousel = $('photoCarousel');
    if (!carousel) return;
    var card = carousel.querySelector('.photo-card');
    var cardWidth = card ? (card.offsetWidth + 12) : 280;
    carousel.scrollBy({ left: direction * cardWidth, behavior: 'smooth' });
  }

  window.fetchPhotos        = fetchPhotos;
  window.renderCarousel     = renderCarousel;
  window.downloadPhoto      = downloadPhoto;
  window.downloadAllPhotos  = downloadAllPhotos;
  window.carouselScroll     = carouselScroll;
})();
