/* ============================================================
   NexVita – sos.js
   SOS button, geolocation, countdown, trigger SOS API
   ============================================================ */

'use strict';

let sosEndpoint   = '';
let userLat       = null;
let userLng       = null;
let countdownTimer = null;
let sosCancelled  = false;

function initSOS(endpoint) {
  sosEndpoint = endpoint;
  detectLocation();
}

// ===== Geolocation =====
function detectLocation() {
  const info   = document.getElementById('locationInfo');
  const status = document.getElementById('locationStatus');

  if (!navigator.geolocation) {
    if (info) info.innerHTML = '<p style="color:var(--text-mid);font-size:var(--text-sm);">Geolocation not supported by your browser.</p>';
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function(pos) {
      userLat = pos.coords.latitude;
      userLng = pos.coords.longitude;

      if (status) { status.textContent = 'Located'; status.className = 'badge badge-success'; }
      if (info) {
        info.innerHTML = `
          <div style="display:flex;align-items:center;gap:var(--sp-3);">
            <svg data-lucide="map-pin" style="width:20px;height:20px;color:var(--primary);"></svg>
            <div>
              <div style="font-weight:600;font-size:var(--text-sm);">Location detected</div>
              <div style="font-size:var(--text-xs);color:var(--text-mid);">Lat: ${userLat.toFixed(5)}, Lng: ${userLng.toFixed(5)}</div>
            </div>
          </div>
        `;
      }
      if (window.lucide) lucide.createIcons();
    },
    function(err) {
      if (status) { status.textContent = 'Unavailable'; status.className = 'badge badge-neutral'; }
      if (info) {
        info.innerHTML = `
          <p style="font-size:var(--text-sm);color:var(--text-mid);">
            ⚠️ Location access denied. Please enable location services in your browser for full SOS functionality.
          </p>
        `;
      }
    },
    { timeout: 8000, maximumAge: 60000 }
  );
}

// ===== SOS Trigger =====
function triggerSOS() {
  sosCancelled = false;
  const overlay = document.getElementById('sosOverlay');
  if (overlay) overlay.classList.add('active');

  let count = 3;
  const countEl = document.getElementById('sosCountdown');

  countdownTimer = setInterval(() => {
    if (sosCancelled) { clearInterval(countdownTimer); return; }
    count--;
    if (countEl) countEl.textContent = count;
    if (count <= 0) {
      clearInterval(countdownTimer);
      sendSOSAlert();
    }
  }, 1000);
}

function cancelSOS() {
  sosCancelled = true;
  clearInterval(countdownTimer);
  const overlay = document.getElementById('sosOverlay');
  if (overlay) overlay.classList.remove('active');
  showFlash('SOS cancelled.', 'info');
}

async function sendSOSAlert() {
  const overlay = document.getElementById('sosOverlay');
  try {
    const res = await fetch(sosEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latitude: userLat, longitude: userLng }),
    });
    const data = await res.json();
    if (overlay) overlay.classList.remove('active');
    if (data.success) {
      showFlash('🚨 Emergency alert sent! Help is on the way.', 'success');
    } else {
      showFlash('Alert sent with limited info. Please call emergency services directly.', 'warning');
    }
  } catch {
    if (overlay) overlay.classList.remove('active');
    showFlash('Failed to send alert. Please call 112 directly.', 'danger');
  }
}

// ===== Share Location =====
function shareLocation() {
  if (!userLat || !userLng) {
    showFlash('Location not yet detected. Please wait or enable location services.', 'warning');
    return;
  }
  const url = `https://maps.google.com/?q=${userLat},${userLng}`;
  if (navigator.share) {
    navigator.share({ title: 'My Location – NexVita SOS', url })
      .then(() => showFlash('Location shared!', 'success'))
      .catch(() => {});
  } else {
    navigator.clipboard.writeText(url).then(() => showFlash('Location link copied to clipboard!', 'success'));
  }
}
