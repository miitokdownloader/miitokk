/* ── DOWNLOADER ────────────────────────────────── */

async function fetchPreview(url) {
  try {
    const fd = new FormData();
    fd.append('url', url);
    const res = await fetch('/preview', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error || !data.title) return;
    previewData = data;
    lastPreviewUrl = url;
    document.getElementById('previewTitle').textContent = data.title || '';
    document.getElementById('previewUploader').textContent = data.uploader ? '@' + data.uploader : '';
    if (data.duration) {
      const m = Math.floor(data.duration / 60);
      const s = data.duration % 60;
      document.getElementById('previewDuration').textContent = m + ':' + String(s).padStart(2,'0');
    }
    const thumb = document.getElementById('previewThumb');
    if (data.thumbnail) {
      thumb.src = data.thumbnail;
      thumb.classList.remove('preview-thumb-fallback');
      thumb.onerror = function() {
        thumb.classList.add('preview-thumb-fallback');
        thumb.alt = 'MII';
        thumb.src = '';
      };
    } else {
      thumb.classList.add('preview-thumb-fallback');
      thumb.alt = 'MII';
      thumb.src = '';
    }
    document.getElementById('previewCard').classList.add('show');
  } catch(e) {}
}

async function downloadAudio() {
  if (isDownloadingAudio) return;
  const url = document.getElementById('urlInput').value.trim();
  if (!url) {
    setStatus('Paste TikTok link first.', 'err');
    return;
  }
  isDownloadingAudio = true;
  const mp3Btn = document.querySelector('.mp3-btn');
  if (mp3Btn) mp3Btn.classList.add('loading');
  setStatus('', '');

  try {
    const response = await fetch('/download-audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });

    if (!response.ok) {
      let errMsg = 'Audio belum bisa diproses. Coba video lain.';
      try {
        const errData = await response.json();
        if (errData.error) errMsg = errData.error;
      } catch(e) {}
      setStatus(errMsg, 'err');
      return;
    }

    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = 'miitok_audio.mp3';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    }, 1000);
    setStatus('Audio download berhasil!', 'ok');
  } catch(e) {
    setStatus('Audio belum bisa diproses. Coba video lain.', 'err');
  } finally {
    isDownloadingAudio = false;
    if (mp3Btn) mp3Btn.classList.remove('loading');
  }
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
  trackEvent('download_click');
  isDownloading = true;
  const btn = document.getElementById('dlBtn');
  btn.disabled = true;
  document.getElementById('spinnerWrap').classList.add('show');
  const spinnerLabel = document.getElementById('spinnerLabel');
  if (spinnerLabel) {
    spinnerLabel.textContent = '> LINK DETECTED\n> QUALITY: ' + (qualityLabel[selectedQuality] || 'BEST') + '\n> CONVERTING MP4\u2026';
  }
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
    trackEvent('download_success');

  } catch(e) {
    setStatus('Terjadi kesalahan, coba lagi.', 'err');
  } finally {
    isDownloading = false;
    btn.disabled = false;
    document.getElementById('spinnerWrap').classList.remove('show');
    const spinnerLabelEl = document.getElementById('spinnerLabel');
    if (spinnerLabelEl) spinnerLabelEl.textContent = 'MEMPROSES\u2026';
  }
}
