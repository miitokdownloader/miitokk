/* ── ANALYTICS ─────────────────────────────────── */

function trackEvent(eventType) {
  fetch('/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type: eventType })
  }).catch(function() {});
}

function animateCounter(element, targetValue) {
  var start = 0;
  var duration = 1500;
  var startTime = null;

  function easeOut(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function step(timestamp) {
    if (!startTime) startTime = timestamp;
    var elapsed = timestamp - startTime;
    var progress = Math.min(elapsed / duration, 1);
    var easedProgress = easeOut(progress);
    var current = Math.floor(easedProgress * targetValue);
    element.textContent = current;
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      element.textContent = targetValue;
    }
  }

  requestAnimationFrame(step);
}

function loadStats() {
  fetch('/stats')
    .then(function(res) { return res.json(); })
    .then(function(data) {
      var viewsEl = document.getElementById('statViews');
      var downloadsEl = document.getElementById('statDownloads');
      var visitorsEl = document.getElementById('statVisitors');
      if (viewsEl && data.total_views !== undefined) {
        animateCounter(viewsEl, data.total_views);
      }
      if (downloadsEl && data.total_downloads !== undefined) {
        animateCounter(downloadsEl, data.total_downloads);
      }
      if (visitorsEl && data.total_visitors !== undefined) {
        animateCounter(visitorsEl, data.total_visitors);
      }
    })
    .catch(function() {});
}

document.addEventListener('DOMContentLoaded', function() {
  trackEvent('page_view');
  trackEvent('visitor');
  loadStats();

  // Social link click tracking
  var instagramEls = document.querySelectorAll('.social-btn.instagram, .instagram-link');
  instagramEls.forEach(function(el) {
    el.addEventListener('click', function() { trackEvent('instagram_click'); });
  });

  var telegramEls = document.querySelectorAll('.social-btn.telegram, .telegram-link');
  telegramEls.forEach(function(el) {
    el.addEventListener('click', function() { trackEvent('telegram_click'); });
  });

  var whatsappEls = document.querySelectorAll('.social-btn.whatsapp, .whatsapp-link');
  whatsappEls.forEach(function(el) {
    el.addEventListener('click', function() { trackEvent('whatsapp_click'); });
  });

  var storeEls = document.querySelectorAll('.social-btn.store, .lynkid-link');
  storeEls.forEach(function(el) {
    el.addEventListener('click', function() { trackEvent('lynkid_click'); });
  });
});
