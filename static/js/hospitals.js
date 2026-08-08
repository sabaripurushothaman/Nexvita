/* ============================================================
   NexVita – hospitals.js  v2
   Hospital Directory: geolocation → API → rich card render

   Supports:
   - Geoapify fields: address, phone, website, maps URL
   - OpenStreetMap Overpass fallback fields
   - All null fields hidden gracefully (no "not available" text)
   - Source attribution per provider
   ============================================================ */

'use strict';

let hUserLat      = null;
let hUserLng      = null;
let hApiUrl       = '';
let hCurrentData  = [];
let hCurrentRadius = 10;
let hFetching     = false;   // prevent duplicate simultaneous calls

/**
 * Entry point from hospital/index.html
 * @param {string} apiUrl  - URL for /hospital/api/nearby
 */
function initHospitalDirectory(apiUrl) {
  hApiUrl = apiUrl;
  detectAndLoad();
}

// ─────────────────────────────────────────────────────────────────
// Geolocation
// ─────────────────────────────────────────────────────────────────

function detectAndLoad() {
  if (hFetching) return;
  showState('loading', 'Detecting your location…');

  if (!navigator.geolocation) {
    showState('no-geo',
      'Geolocation is not supported by your browser. ' +
      'Please use a modern browser to see nearby hospitals.');
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function (pos) {
      hUserLat = pos.coords.latitude;
      hUserLng = pos.coords.longitude;
      loadHospitals(hCurrentRadius);
    },
    function (err) {
      let msg;
      switch (err.code) {
        case 1:
          msg = 'Location access is required to find nearby hospitals. ' +
                'Please allow location access in your browser settings.';
          break;
        case 2:
          msg = 'Your location could not be determined. Please try again.';
          break;
        case 3:
          msg = 'Location detection timed out. Please check your connection.';
          break;
        default:
          msg = 'Location unavailable.';
      }
      showState('permission-denied', msg);
    },
    { timeout: 12000, maximumAge: 120000, enableHighAccuracy: false }
  );
}

async function loadHospitals(radius) {
  if (hFetching) return;
  if (hUserLat === null || hUserLng === null) {
    detectAndLoad();
    return;
  }

  hFetching     = true;
  hCurrentRadius = radius || 10;
  showState('loading', `Searching for hospitals within ${hCurrentRadius} km…`);

  try {
    const url = `${hApiUrl}?lat=${hUserLat}&lng=${hUserLng}&radius=${hCurrentRadius}`;
    const res  = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.success) {
      showState('api-error', data.error || 'Hospital search failed. Please try again.');
      return;
    }

    hCurrentData = data.hospitals || [];

    if (hCurrentData.length === 0) {
      showState('empty',
        `No hospitals found within ${hCurrentRadius} km of your location.`);
    } else {
      renderHospitals(hCurrentData, data.source, data.attribution);
    }
  } catch (e) {
    showState('api-error',
      'Unable to load nearby hospitals right now. Please try again.');
  } finally {
    hFetching = false;
  }
}

// ─────────────────────────────────────────────────────────────────
// Rendering
// ─────────────────────────────────────────────────────────────────

function renderHospitals(hospitals, source, attribution) {
  const grid      = document.getElementById('hospitalsGrid');
  const countEl   = document.getElementById('hospitalCount');
  const stateEl   = document.getElementById('hospitalState');
  const locEl     = document.getElementById('userLocationInfo');
  const attrEl    = document.getElementById('mapAttribution');
  const sourceEl  = document.getElementById('dataSource');

  if (stateEl)  stateEl.style.display  = 'none';
  if (grid)     grid.style.display     = '';

  if (countEl)  countEl.textContent =
    `${hospitals.length} hospital${hospitals.length !== 1 ? 's' : ''} found`;

  if (locEl && hUserLat !== null)
    locEl.textContent = `Near ${hUserLat.toFixed(4)}, ${hUserLng.toFixed(4)}`;

  // Attribution (OSM licence requires this; Geoapify asks for attribution in their terms)
  if (attrEl) {
    attrEl.innerHTML = attribution
      ? `<span style="color:var(--text-mid);">${escHtml(attribution)}</span>`
      : '';
  }

  if (sourceEl) {
    sourceEl.innerHTML = source === 'geoapify'
      ? '<span class="badge badge-neutral" style="font-size:10px;">Powered by Geoapify</span>'
      : source === 'overpass'
        ? '<span class="badge badge-neutral" style="font-size:10px;">© OpenStreetMap</span>'
        : '';
  }

  if (!grid) return;
  grid.innerHTML = hospitals.map((h, i) => buildCard(h)).join('');
  if (window.lucide) lucide.createIcons();
}

function buildCard(h) {
  // ── Badges ──────────────────────────────────────────────────
  const distBadge = h.distance_km != null
    ? `<span class="badge badge-neutral">📏 ${h.distance_km} km</span>` : '';

  let openBadge = '';
  if (h.open_now === true)        openBadge = '<span class="badge badge-success"><span class="dot"></span> Open now</span>';
  else if (h.open_now === false)  openBadge = '<span class="badge badge-danger">Closed</span>';

  const emergBadge = h.emergency_services === true
    ? '<span class="badge badge-success">24/7 Emergency</span>' : '';

  // Business status — only show non-OPERATIONAL states (Geoapify doesn't provide this; field is null)
  let statusBadge = '';
  if (h.business_status && h.business_status !== 'OPERATIONAL') {
    const statusMap = {
      CLOSED_TEMPORARILY: 'Temporarily Closed',
      CLOSED_PERMANENTLY: 'Permanently Closed',
    };
    statusBadge = `<span class="badge badge-warning">${statusMap[h.business_status] || h.business_status}</span>`;
  }

  // ── Rating ──────────────────────────────────────────────────
  let ratingHtml = '';
  if (h.rating != null) {
    const stars = renderStars(h.rating);
    const count = h.rating_count != null
      ? ` <span style="color:var(--text-mid);font-size:var(--text-xs);">(${h.rating_count.toLocaleString()})</span>`
      : '';
    ratingHtml = `
      <div class="hospital-card__rating">
        ${stars}
        <span class="hospital-card__rating-num">${h.rating.toFixed(1)}</span>
        ${count}
      </div>`;
  }

  // ── Buttons ─────────────────────────────────────────────────
  const mapsUrl = h.maps_url
    || (h.latitude != null ? `https://www.google.com/maps?q=${h.latitude},${h.longitude}` : null);

  const mapBtn = mapsUrl
    ? `<a href="${escAttr(mapsUrl)}" target="_blank" rel="noopener noreferrer"
          class="btn btn-ghost btn-sm">
         <svg data-lucide="map" style="width:14px;height:14px;"></svg> View on Map
       </a>`
    : '';

  const callBtn = h.phone
    ? `<a href="tel:${escAttr(h.phone)}" class="btn btn-primary btn-sm">
         <svg data-lucide="phone" style="width:14px;height:14px;"></svg> Call
       </a>`
    : '';

  // ── Source badge ─────────────────────────────────────────────
  const sourceBadge = h.source === 'geoapify'
    ? '<span class="hospital-card__source" title="Data from Geoapify / OpenStreetMap">Geoapify</span>'
    : '<span class="hospital-card__source" title="Data from OpenStreetMap">OSM</span>';

  return `
    <div class="hospital-card hover-lift">
      <div class="hospital-card__header">
        <div class="hospital-card__icon">
          <svg data-lucide="building-2" style="width:20px;height:20px;color:var(--info);"></svg>
        </div>
        <div class="hospital-card__badges">
          ${distBadge} ${openBadge} ${emergBadge} ${statusBadge}
        </div>
      </div>

      <div class="hospital-card__name">
        ${escHtml(h.name)}
      </div>

      ${h.address ? `
        <div class="hospital-card__addr">
          <svg data-lucide="map-pin" style="width:12px;height:12px;display:inline;margin-right:4px;color:var(--text-mid);flex-shrink:0;"></svg>
          <span>${escHtml(h.address)}</span>
        </div>` : ''}

      ${h.phone ? `
        <div class="hospital-card__phone">
          <svg data-lucide="phone" style="width:12px;height:12px;display:inline;margin-right:4px;color:var(--text-mid);"></svg>
          <a href="tel:${escAttr(h.phone)}" style="color:var(--primary);">${escHtml(h.phone)}</a>
        </div>` : ''}

      ${ratingHtml}

      <div class="hospital-card__footer">
        <div class="hospital-card__actions">
          ${callBtn}
          ${mapBtn}
        </div>
        ${sourceBadge}
      </div>
    </div>`;
}

function renderStars(rating) {
  const full  = Math.floor(rating);
  const half  = rating - full >= 0.5 ? 1 : 0;
  const empty = 5 - full - half;
  let s = '';
  for (let i = 0; i < full;  i++) s += '<span style="color:#F59E0B;">★</span>';
  if (half)                        s += '<span style="color:#F59E0B;">½</span>';
  for (let i = 0; i < empty; i++) s += '<span style="color:var(--border);">★</span>';
  return `<span class="hospital-card__stars">${s}</span>`;
}

// ─────────────────────────────────────────────────────────────────
// State panel (loading / error / empty)
// ─────────────────────────────────────────────────────────────────

function showState(type, message) {
  const grid    = document.getElementById('hospitalsGrid');
  const stateEl = document.getElementById('hospitalState');
  const countEl = document.getElementById('hospitalCount');

  if (grid)    { grid.style.display = 'none'; }
  if (countEl) { countEl.textContent = ''; }
  if (!stateEl) return;

  stateEl.style.display = '';

  const icons = {
    loading:            `<div class="spinner" style="margin:0 auto var(--sp-4);"></div>`,
    empty:              `<svg data-lucide="building-2"></svg>`,
    'permission-denied':`<svg data-lucide="map-pin-off"></svg>`,
    'no-geo':           `<svg data-lucide="map-pin-off"></svg>`,
    'api-error':        `<svg data-lucide="wifi-off"></svg>`,
  };

  const titles = {
    loading:            'Searching…',
    empty:              'No Hospitals Found',
    'permission-denied':'Location Access Required',
    'no-geo':           'Browser Not Supported',
    'api-error':        'Search Unavailable',
  };

  const showRetry     = type !== 'loading' && type !== 'no-geo';
  const showWiderBtn  = type === 'empty' && hCurrentRadius < 30;
  const showCall112   = type === 'permission-denied' || type === 'api-error';

  stateEl.innerHTML = `
    <div class="empty-state">
      ${icons[type] || icons.empty}
      <h3>${titles[type] || 'Unavailable'}</h3>
      <p>${escHtml(message)}</p>
      <div style="display:flex;gap:var(--sp-3);justify-content:center;margin-top:var(--sp-4);flex-wrap:wrap;">
        ${showRetry ? `<button class="btn btn-primary btn-sm" onclick="detectAndLoad()">
          <svg data-lucide="refresh-cw" style="width:14px;height:14px;"></svg> Try Again
        </button>` : ''}
        ${showWiderBtn ? `<button class="btn btn-ghost btn-sm" onclick="loadHospitals(${hCurrentRadius + 10})">
          Search ${hCurrentRadius + 10} km radius
        </button>` : ''}
        ${showCall112 ? `<a href="tel:112" class="btn btn-danger btn-sm">
          <svg data-lucide="phone-call" style="width:14px;height:14px;"></svg> Call 112
        </a>` : ''}
      </div>
    </div>`;
  if (window.lucide) lucide.createIcons();
}

// ─────────────────────────────────────────────────────────────────
// Filter
// ─────────────────────────────────────────────────────────────────

function filterHospitals(query) {
  if (!hCurrentData.length) return;
  const q = query.trim().toLowerCase();
  const filtered = q.length < 2
    ? hCurrentData
    : hCurrentData.filter(h =>
        (h.name    || '').toLowerCase().includes(q) ||
        (h.address || '').toLowerCase().includes(q)
      );

  const grid = document.getElementById('hospitalsGrid');
  const countEl = document.getElementById('hospitalCount');
  if (grid) {
    grid.innerHTML = filtered.map(buildCard).join('');
    if (window.lucide) lucide.createIcons();
  }
  if (countEl) {
    countEl.textContent = `${filtered.length} hospital${filtered.length !== 1 ? 's' : ''} found`;
  }
}

// ─────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}

function escAttr(str) {
  // Safe for use inside href / onclick attr values
  return escHtml(str);
}
