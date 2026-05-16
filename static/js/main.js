
/* ── STATE ────────────────────────────────────── */
let selectedQuality = 'best';
let isDownloading   = false;
let previewData     = null;
let previewTimer    = null;
let photoUrls       = [];
let isPhotoMode     = false;

const qualityLabel = { best:'BEST', '1080':'1080P', '720':'720P', photo:'PHOTO' };
const typeLabel    = { best:'MP4', '1080':'MP4', '720':'MP4', photo:'IMAGE' };

/* ── QUALITY ──────────────────────────────────── */
function setQuality(el, q) {
  isDownloading = false;
  // Clear status and photo section on tab switch
  setStatus('', '');
  hidePreview();
  document.getElementById('photoSection').style.display = 'none';
  document.getElementById('photoCarousel').innerHTML = '';
  document.getElementById('photoCount').textContent = '';
  document.getElementById('downloadAllBtn').style.display = 'none';
  photoUrls = [];
  document.querySelectorAll('.q-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  selectedQuality = q;
  if (q === 'photo') {
    isPhotoMode = true;
    document.getElementById('dlWrap').style.display = 'none';
    setStatus('PHOTO mode is temporarily disabled.', 'err');
  } else {
    isPhotoMode = false;
    document.getElementById('dlWrap').style.display = '';
  }
}

/* ── INPUT ────────────────────────────────────── */
function onUrlInput() {
  const val = document.getElementById('urlInput').value.trim();
  const clearBtn = document.getElementById('clearBtn');
  clearBtn.classList.toggle('visible', val.length > 0);

  clearTimeout(previewTimer);
  hidePreview();
  setStatus('', '');

  if (val.length > 10 && (val.includes('tiktok.com') || val.includes('vt.tiktok'))) {
    if (isPhotoMode) {
      // PHOTO mode is disabled - do not trigger any fetch
    } else {
      previewTimer = setTimeout(() => fetchPreview(val), 900);
    }
  }
}

function clearUrl() {
  document.getElementById('urlInput').value = '';
  document.getElementById('clearBtn').classList.remove('visible');
  clearTimeout(previewTimer);
  hidePreview();
  setStatus('', '');
}

function setStatus(msg, type) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status' + (type ? ' ' + type : '');
}

function hidePreview() {
  previewData = null;
  document.getElementById('previewCard').classList.remove('show');
}

async function fetchPreview(url) {
  try {
    const fd = new FormData();
    fd.append('url', url);
    const res = await fetch('/preview', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error || !data.title) return;
    previewData = data;
    document.getElementById('previewTitle').textContent = data.title || '';
    document.getElementById('previewUploader').textContent = data.uploader ? '@' + data.uploader : '';
    if (data.duration) {
      const m = Math.floor(data.duration / 60);
      const s = data.duration % 60;
      document.getElementById('previewDuration').textContent = m + ':' + String(s).padStart(2,'0');
    }
    if (data.thumbnail) {
      document.getElementById('previewThumb').src = data.thumbnail;
    }
    document.getElementById('previewCard').classList.add('show');
  } catch(e) {}
}

function openModal() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) {
    setStatus('Paste TikTok link first.', 'err');
    return;
  }
  // Populate modal info
  if (previewData) {
    document.getElementById('modalTitle').textContent = previewData.title || 'TikTok Video';
    document.getElementById('modalUploader').textContent = previewData.uploader ? '@' + previewData.uploader : '';
    const thumb = document.getElementById('modalThumb');
    if (previewData.thumbnail) {
      thumb.src = previewData.thumbnail;
      thumb.classList.add('show');
    } else {
      thumb.classList.remove('show');
    }
  } else {
    document.getElementById('modalTitle').textContent = 'TikTok Video';
    document.getElementById('modalUploader').textContent = '';
    document.getElementById('modalThumb').classList.remove('show');
  }
  // Pills
  const pills = document.getElementById('modalPills');
  pills.innerHTML = '';
  const qPill = document.createElement('span');
  qPill.className = 'pill highlight';
  qPill.textContent = qualityLabel[selectedQuality] || selectedQuality;
  pills.appendChild(qPill);
  const tPill = document.createElement('span');
  tPill.className = 'pill';
  tPill.textContent = typeLabel[selectedQuality] || 'MP4';
  pills.appendChild(tPill);

  document.getElementById('modalBackdrop').classList.add('show');
}

function closeModal() {
  document.getElementById('modalBackdrop').classList.remove('show');
}

function backdropClick(event) {
  if (event.target === document.getElementById('modalBackdrop')) {
    closeModal();
  }
}

function copyLink() {
  const url = document.getElementById('urlInput').value.trim();
  if (url) {
    navigator.clipboard.writeText(url).catch(() => {});
  }
  closeModal();
}

async function confirmDownload() {
  if (isDownloading) return;
  const url = document.getElementById('urlInput').value.trim();
  if (!url) {
    setStatus('Paste TikTok link first.', 'err');
    closeModal();
    return;
  }
  closeModal();
  isDownloading = true;
  const btn = document.getElementById('dlBtn');
  btn.disabled = true;
  document.getElementById('spinnerWrap').classList.add('show');
  setStatus('', '');

  try {
    const formData = new FormData();
    formData.append('url', url);
    formData.append('quality', selectedQuality);

    const response = await fetch('/download', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      let errMsg = 'Download gagal.';
      try {
        const errData = await response.json();
        if (errData.error) errMsg = errData.error;
      } catch(e) {}
      setStatus(errMsg, 'err');
      return;
    }

    // Trigger file download
    const blob = await response.blob();
    const contentDisposition = response.headers.get('Content-Disposition') || '';
    let filename = 'miitok_video.mp4';
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/);
    if (match) filename = match[1];
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    }, 1000);
    setStatus('Download berhasil!', 'ok');

  } catch(e) {
    setStatus('Terjadi kesalahan, coba lagi.', 'err');
  } finally {
    isDownloading = false;
    btn.disabled = false;
    document.getElementById('spinnerWrap').classList.remove('show');
  }
}
/* ── PHOTO MODE ───────────────────────────────── */
async function fetchPhotos(url) {
  if (isDownloading) return;
  isDownloading = true;
  document.getElementById('spinnerWrap').classList.add('show');
  document.getElementById('photoSection').style.display = 'none';
  setStatus('', '');
  try {
    const fd = new FormData();
    fd.append('url', url);
    const res = await fetch('/photos', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) {
      setStatus(data.error, 'err');
      return;
    }
    renderCarousel(data.photos || [], data.count || 0);
    // Show preview card with photo metadata if available
    if (data.title || data.uploader || data.thumbnail) {
      previewData = {
        title: data.title || '',
        uploader: data.uploader || '',
        thumbnail: data.thumbnail || null,
      };
      document.getElementById('previewTitle').textContent = previewData.title;
      document.getElementById('previewUploader').textContent = previewData.uploader ? '@' + previewData.uploader : '';
      document.getElementById('previewDuration').textContent = '';
      if (previewData.thumbnail) {
        document.getElementById('previewThumb').src = previewData.thumbnail;
      }
      document.getElementById('previewCard').classList.add('show');
    }
  } catch(e) {
    setStatus('Terjadi kesalahan saat mengambil foto.', 'err');
  } finally {
    isDownloading = false;
    document.getElementById('spinnerWrap').classList.remove('show');
  }
}

function renderCarousel(photos, count) {
  if (!isPhotoMode) return;
  const carousel  = document.getElementById('photoCarousel');
  const countEl   = document.getElementById('photoCount');
  const dlAllBtn  = document.getElementById('downloadAllBtn');
  const section   = document.getElementById('photoSection');
  carousel.innerHTML = '';
  if (!photos || !photos.length) {
    setStatus('Tidak ada foto ditemukan. Link ini mungkin video, bukan slideshow.', 'err');
    countEl.textContent = '';
    dlAllBtn.style.display = 'none';
    section.style.display = 'none';   // keep section hidden
    return;
  }
  photoUrls = photos;
  countEl.textContent = 'Photos found: ' + count;
  countEl.style.color = 'rgba(204,0,0,0.8)';
  photos.forEach(function(url, i) {
    const card = document.createElement('div');
    card.className = 'photo-card';
    const img = document.createElement('img');
    img.src     = '/photo-proxy?url=' + encodeURIComponent(url);
    img.alt     = 'Photo ' + (i + 1);
    img.loading = 'lazy';
    const footer = document.createElement('div');
    footer.className = 'photo-card-footer';
    const btn = document.createElement('button');
    btn.className   = 'photo-dl-btn';
    btn.textContent = 'DOWNLOAD PHOTO';
    btn.onclick     = (function(u, idx) { return function() { downloadPhoto(u, idx); }; })(url, i + 1);
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
    const filename = 'miitok_photo_' + index + '.jpg';
    const res = await fetch('/download-photo?url=' + encodeURIComponent(url) + '&filename=' + encodeURIComponent(filename));
    if (!res.ok) { setStatus('Gagal mengunduh foto ' + index, 'err'); return; }
    const blob    = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a       = document.createElement('a');
    a.href        = blobUrl;
    a.download    = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function() { document.body.removeChild(a); URL.revokeObjectURL(blobUrl); }, 1000);
  } catch(e) {
    setStatus('Gagal mengunduh foto ' + index, 'err');
  }
}

async function downloadAllPhotos() {
  if (!photoUrls.length) return;
  setStatus('Mengunduh ' + photoUrls.length + ' foto...', 'ok');
  for (let i = 0; i < photoUrls.length; i++) {
    await downloadPhoto(photoUrls[i], i + 1);
    if (i < photoUrls.length - 1) {
      await new Promise(function(resolve) { setTimeout(resolve, 350); });
    }
  }
  setStatus('Semua foto berhasil diunduh!', 'ok');
}

function carouselScroll(direction) {
  const carousel = document.getElementById('photoCarousel');
  const card     = carousel.querySelector('.photo-card');
  const cardWidth = card ? (card.offsetWidth + 12) : 280;
  carousel.scrollBy({ left: direction * cardWidth, behavior: 'smooth' });
}

/* ── NAVBAR HAMBURGER ─────────────────────────── */
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
  