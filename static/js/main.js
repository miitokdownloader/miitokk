/* ── MAIN ORCHESTRATION ────────────────────────── */

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
