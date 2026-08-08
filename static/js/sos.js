/* ============================================================
   NexVita – sos.js  v2
   Emergency SOS page:
     1. Geolocation
     2. Nearby hospital fetch + rich mini-cards
     3. SOS countdown → Twilio SMS → honest status
     4. Explicit 112 call action (tel: link — never faked)
   ============================================================ */

'use strict';

let nearbyApiBase    = '';
let userLat          = null;
let userLng          = null;
let locationResolved = false;
let hospitalFetching = false;

/**
 * Entry point called from sos/index.html
 * @param {string} hospitalsUrl  - GET  /hospital/api/nearby
 */
function initSOS(hospitalsUrl) {
  if (arguments.length >= 2) {
    nearbyApiBase = arguments[1];
  } else {
    nearbyApiBase = hospitalsUrl;
  }
  detectLocation();
}

// ─────────────────────────────────────────────────────────────────
// Geolocation
// ─────────────────────────────────────────────────────────────────

function detectLocation() {
  const infoEl   = document.getElementById('locationInfo');
  const statusEl = document.getElementById('locationStatus');

  if (!navigator.geolocation) {
    setLocationBadge('Unsupported', 'neutral', statusEl);
    if (infoEl) infoEl.innerHTML =
      '<p style="font-size:var(--text-sm);color:var(--text-mid);">' +
      '⚠️ Geolocation is not supported by your browser.</p>';
    renderNearbyError('no-geo');
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function (pos) {
      userLat          = pos.coords.latitude;
      userLng          = pos.coords.longitude;
      locationResolved = true;

      setLocationBadge('Located', 'success', statusEl);

      if (infoEl) infoEl.innerHTML = `
        <div style="display:flex;align-items:center;gap:var(--sp-3);">
          <svg data-lucide="map-pin"
               style="width:20px;height:20px;color:var(--primary);flex-shrink:0;"></svg>
          <div>
            <div style="font-weight:600;font-size:var(--text-sm);">Location detected</div>
            <div style="font-size:var(--text-xs);color:var(--text-mid);">
              ${userLat.toFixed(5)}, ${userLng.toFixed(5)}
            </div>
          </div>
        </div>`;

      if (window.lucide) lucide.createIcons();
      fetchNearbyHospitals(userLat, userLng);
    },
    function (err) {
      locationResolved = false;
      setLocationBadge('Unavailable', 'neutral', statusEl);

      const msgs = {
        1: 'Location access denied. Enable location services for full SOS functionality.',
        2: 'Location could not be determined. Please try again.',
        3: 'Location detection timed out.',
      };
      const msg = msgs[err.code] || 'Location unavailable.';
      if (infoEl) infoEl.innerHTML =
        `<p style="font-size:var(--text-sm);color:var(--text-mid);">⚠️ ${msg}</p>`;

      renderNearbyError('location-denied');
    },
    { timeout: 12000, maximumAge: 60000, enableHighAccuracy: false }
  );
}

function setLocationBadge(text, type, el) {
  if (!el) return;
  el.textContent = text;
  el.className   = `badge badge-${type}`;
}

// ─────────────────────────────────────────────────────────────────
// Nearby Hospitals (SOS mini-panel)
// ─────────────────────────────────────────────────────────────────

async function fetchNearbyHospitals(lat, lng, radius) {
  if (hospitalFetching) return;
  const container = document.getElementById('nearbyHospitalsList');
  const subtitleEl = document.getElementById('nearbyHospitalsSubtitle');
  if (!container) return;

  hospitalFetching = true;
  const r = radius || 10;

  container.innerHTML = `
    <div style="display:flex;align-items:center;gap:var(--sp-3);padding:var(--sp-4);">
      <div class="spinner spinner-sm"></div>
      <span style="font-size:var(--text-sm);color:var(--text-mid);">
        Searching nearby hospitals…
      </span>
    </div>`;

  try {
    const url  = `${nearbyApiBase}?lat=${lat}&lng=${lng}&radius=${r}`;
    const res  = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.success && data.hospitals && data.hospitals.length > 0) {
      if (subtitleEl)
        subtitleEl.textContent = `${data.count} found within ${r} km`;
      renderNearbyList(container, data.hospitals.slice(0, 5), data.source);
    } else {
      if (subtitleEl) subtitleEl.textContent = `Within ${r} km radius`;
      renderNearbyEmpty(container, data.error);
    }
  } catch (e) {
    if (subtitleEl) subtitleEl.textContent = 'Within 10 km radius';
    renderNearbyError('api-error', container);
  } finally {
    hospitalFetching = false;
  }
}

function renderNearbyList(container, hospitals, source) {
  container.innerHTML = hospitals.map(h => buildMiniCard(h)).join('');
  if (window.lucide) lucide.createIcons();
}

function buildMiniCard(h) {
  // Distance badge
  const distBadge = h.distance_km != null
    ? `<span class="badge badge-neutral" style="font-size:10px;">
         ${h.distance_km} km
       </span>` : '';

  // Open/closed badge
  let openBadge = '';
  if (h.open_now === true)  openBadge = '<span class="badge badge-success" style="font-size:10px;">Open</span>';
  if (h.open_now === false) openBadge = '<span class="badge badge-danger"  style="font-size:10px;">Closed</span>';

  // Rating
  const ratingText = (h.rating != null)
    ? `<span style="font-size:10px;color:var(--text-mid);">⭐ ${h.rating.toFixed(1)}</span>` : '';

  // Call button (only if phone present)
  const callBtn = h.phone
    ? `<a href="tel:${escHtml(h.phone)}" class="btn btn-primary btn-icon btn-sm"
           title="Call ${escHtml(h.name)}">
         <svg data-lucide="phone" style="width:13px;height:13px;"></svg>
       </a>` : '';

  // Map button
  const mapsUrl = h.maps_url
    || (h.latitude != null
        ? `https://www.google.com/maps?q=${h.latitude},${h.longitude}` : null);
  const mapBtn  = mapsUrl
    ? `<a href="${escHtml(mapsUrl)}" target="_blank" rel="noopener noreferrer"
           class="btn btn-ghost btn-icon btn-sm" title="View on Map">
         <svg data-lucide="map-pin" style="width:13px;height:13px;"></svg>
       </a>` : '';

  return `
    <div class="hospital-mini-item">
      <div class="hospital-mini-icon">
        <svg data-lucide="building-2" style="width:16px;height:16px;color:var(--info);"></svg>
      </div>
      <div class="hospital-mini-body">
        <div class="hospital-mini-name">${escHtml(h.name)}</div>
        ${h.address ? `<div class="hospital-mini-addr">${escHtml(h.address)}</div>` : ''}
        ${h.phone   ? `<div class="hospital-mini-phone">
          <svg data-lucide="phone" style="width:10px;height:10px;display:inline;margin-right:3px;"></svg>
          <a href="tel:${escHtml(h.phone)}" style="color:var(--primary);font-size:var(--text-xs);">
            ${escHtml(h.phone)}
          </a>
        </div>` : ''}
      </div>
      <div class="hospital-mini-meta">
        ${distBadge}
        ${openBadge}
        ${ratingText}
        ${callBtn}
        ${mapBtn}
      </div>
    </div>`;
}

function renderNearbyEmpty(container, errMsg) {
  container.innerHTML = `
    <div class="empty-state" style="padding:var(--sp-5);">
      <svg data-lucide="building-2" style="width:32px;height:32px;"></svg>
      <h3 style="font-size:var(--text-base);">No hospitals found</h3>
      <p style="font-size:var(--text-sm);">
        ${escHtml(errMsg || 'No hospitals found nearby.')}
      </p>
      <button class="btn btn-ghost btn-sm" style="margin-top:var(--sp-3);"
              onclick="fetchNearbyHospitals(${userLat}, ${userLng}, 20)">
        Search 20 km radius
      </button>
    </div>`;
  if (window.lucide) lucide.createIcons();
}

function renderNearbyError(type, container) {
  const el = container || document.getElementById('nearbyHospitalsList');
  if (!el) return;

  if (type === 'location-denied' || type === 'no-geo') {
    el.innerHTML = `
      <div class="empty-state" style="padding:var(--sp-5);">
        <svg data-lucide="map-pin-off" style="width:32px;height:32px;"></svg>
        <h3 style="font-size:var(--text-base);">Location unavailable</h3>
        <p style="font-size:var(--text-sm);">
          Allow location access to find nearby hospitals.
        </p>
        <a href="tel:112" class="btn btn-danger btn-sm" style="margin-top:var(--sp-3);"
           onclick="showCall112Toast()">
          <svg data-lucide="phone-call" style="width:13px;height:13px;"></svg> Call 112
        </a>
      </div>`;
  } else {
    el.innerHTML = `
      <div class="empty-state" style="padding:var(--sp-5);">
        <svg data-lucide="wifi-off" style="width:32px;height:32px;"></svg>
        <h3 style="font-size:var(--text-base);">Search unavailable</h3>
        <p style="font-size:var(--text-sm);">Hospital search is temporarily unavailable.</p>
        <button class="btn btn-ghost btn-sm" style="margin-top:var(--sp-3);"
                onclick="fetchNearbyHospitals(${userLat ?? 0}, ${userLng ?? 0})">
          Retry
        </button>
      </div>`;
  }
  if (window.lucide) lucide.createIcons();
}

// ─────────────────────────────────────────────────────────────────
// 112 Emergency Call — explicit user action only
// ─────────────────────────────────────────────────────────────────

/**
 * Called when the "Call 112" button is clicked.
 * Shows feedback toast, then lets the href="tel:112" proceed normally.
 * NEVER calls any backend API, NEVER sends an SMS to 112.
 */
function showCall112Toast() {
  // This is ONLY a UI feedback — the actual call is initiated by href="tel:112"
  // The browser/device handles dialling; we cannot know if the call was placed.
  showFlash(
    '📞 Opening your phone to call 112. If it does not open, please dial 112 manually.',
    'info'
  );
}

// ─────────────────────────────────────────────────────────────────
// Share Location
// ─────────────────────────────────────────────────────────────────

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
    navigator.clipboard.writeText(url)
      .then(() => showFlash('Location link copied to clipboard!', 'success'))
      .catch(() => showFlash(`Location: ${url}`, 'info'));
  }
}

// ─────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
