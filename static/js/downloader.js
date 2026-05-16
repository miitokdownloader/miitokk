/* ── VIDEO PREVIEW + DOWNLOAD ─────────────────── */
/* Depends on: config.js, ui.js. Owns the /preview and /download flow. */

(function () {
  var MII = window.MII;
  if (!MII) {
    console.error('[miitok] downloader.js loaded before config.js - window.MII missing');
    return;
  }

  function $(id) { return document.getElementById(id); }

  async function fetchPreview(url) {
    try {
      var fd = new FormData();
      fd.append('url', url);
      var res = await fetch(MII.endpoints.preview, { method: 'POST', body: fd });
      var data = await res.json();
      if (data.error || !data.title) return;
      MII.state.previewData = data;

      var titleEl    = $('previewTitle');
      var uploaderEl = $('previewUploader');
      var durationEl = $('previewDuration');
      var thumbEl    = $('previewThumb');
      var card       = $('previewCard');

      if (titleEl)    titleEl.textContent = data.title || '';
      if (uploaderEl) uploaderEl.textContent = data.uploader ? '@' + data.uploader : '';
      if (durationEl) {
        if (data.duration) {
          var m = Math.floor(data.duration / 60);
          var s = data.duration % 60;
          durationEl.textContent = m + ':' + String(s).padStart(2, '0');
        } else {
          durationEl.textContent = '';
        }
      }
      if (thumbEl && data.thumbnail) thumbEl.src = data.thumbnail;
      if (card) card.classList.add('show');
    } catch (e) { /* swallow - preview is best-effort */ }
  }

  async function confirmDownload() {
    if (MII.state.isDownloading) return;
    var input = $('urlInput');
    var url = input ? input.value.trim() : '';
    if (!url) {
      if (typeof window.setStatus === 'function') window.setStatus('Paste TikTok link first.', 'err');
      if (typeof window.closeModal === 'function') window.closeModal();
      return;
    }
    if (typeof window.closeModal === 'function') window.closeModal();

    MII.state.isDownloading = true;
    var btn     = $('dlBtn');
    var spinner = $('spinnerWrap');
    if (btn)     btn.disabled = true;
    if (spinner) spinner.classList.add('show');
    if (typeof window.setStatus === 'function') window.setStatus('', '');

    try {
      var formData = new FormData();
      formData.append('url', url);
      formData.append('quality', MII.state.selectedQuality);

      var response = await fetch(MII.endpoints.download, { method: 'POST', body: formData });

      if (!response.ok) {
        var errMsg = 'Download gagal.';
        try {
          var errData = await response.json();
          if (errData.error) errMsg = errData.error;
        } catch (e) { /* non-JSON error body */ }
        if (typeof window.setStatus === 'function') window.setStatus(errMsg, 'err');
        return;
      }

      var blob = await response.blob();
      var disposition = response.headers.get('Content-Disposition') || '';
      var filename = 'miitok_video.mp4';
      var match = disposition.match(/filename="?([^";\n]+)"?/);
      if (match) filename = match[1];

      var blobUrl = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
      }, 1000);

      if (typeof window.setStatus === 'function') window.setStatus('Download berhasil!', 'ok');
    } catch (e) {
      if (typeof window.setStatus === 'function') window.setStatus('Terjadi kesalahan, coba lagi.', 'err');
    } finally {
      MII.state.isDownloading = false;
      if (btn)     btn.disabled = false;
      if (spinner) spinner.classList.remove('show');
    }
  }

  window.fetchPreview    = fetchPreview;
  window.confirmDownload = confirmDownload;
})();
