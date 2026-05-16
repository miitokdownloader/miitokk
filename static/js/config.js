/* ── MIITOK CONFIG / NAMESPACE ────────────────── */
/* First script in the load order. Defines the global namespace
   window.MII used by ui.js / downloader.js / photo.js. No DOM
   access happens here; this file is pure data. */

(function () {
  if (window.MII) return;

  window.MII = {
    state: {
      selectedQuality: 'best',
      isDownloading: false,
      previewData: null,
      previewTimer: null,
      photoUrls: [],
      isPhotoMode: false
    },
    labels: {
      quality: { best: 'BEST', '1080': '1080P', '720': '720P', photo: 'PHOTO' },
      type:    { best: 'MP4',  '1080': 'MP4',   '720': 'MP4',   photo: 'IMAGE' }
    },
    endpoints: {
      preview:       '/preview',
      download:      '/download',
      photos:        '/photos',
      photoProxy:    '/photo-proxy',
      downloadPhoto: '/download-photo'
    },
    debounceMs: 900
  };
})();
