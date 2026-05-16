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
    section.style.display = 'none';
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
