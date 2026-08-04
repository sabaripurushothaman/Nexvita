/* ============================================================
   NexVita – maps.js
   Leaflet.js hospital map initialisation
   ============================================================ */

'use strict';

let map = null;

function initHospitalMap(containerId, hospitals, userLat, userLng) {
  const container = document.getElementById(containerId);
  if (!container || typeof L === 'undefined') return;

  // Default center (India) if no location
  const center = (userLat && userLng) ? [userLat, userLng] : [20.5937, 78.9629];
  const zoom   = (userLat && userLng) ? 13 : 5;

  map = L.map(containerId, { zoomControl: true }).setView(center, zoom);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
    maxZoom: 18,
  }).addTo(map);

  // User location marker
  if (userLat && userLng) {
    const userIcon = L.divIcon({
      className: '',
      html: `<div style="width:16px;height:16px;background:#00C897;border:3px solid white;border-radius:50%;box-shadow:0 2px 8px rgba(0,200,151,.5);"></div>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    });

    L.marker([userLat, userLng], { icon: userIcon })
      .addTo(map)
      .bindPopup('<b>You are here</b>')
      .openPopup();
  }

  // Hospital markers
  const hospitalIcon = L.divIcon({
    className: '',
    html: `<div style="width:28px;height:28px;background:#EF4444;border:2px solid white;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(239,68,68,.4);">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
    </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });

  const bounds = [];
  if (userLat && userLng) bounds.push([userLat, userLng]);

  hospitals.forEach((h, idx) => {
    if (!h.lat || !h.lng) return;
    bounds.push([h.lat, h.lng]);

    const marker = L.marker([h.lat, h.lng], { icon: hospitalIcon }).addTo(map);
    marker.bindPopup(`
      <div style="min-width:200px;font-family:Inter,sans-serif;">
        <div style="font-weight:700;font-size:14px;margin-bottom:4px;">${h.name}</div>
        <div style="font-size:12px;color:#64748B;margin-bottom:6px;">${h.address}${h.city ? ', ' + h.city : ''}</div>
        ${h.emergency ? '<span style="background:#D1FAE5;color:#10B981;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;">24/7 Emergency</span>' : ''}
        ${h.phone ? `<div style="margin-top:8px;"><a href="tel:${h.phone}" style="color:#00C897;font-size:12px;font-weight:500;">📞 ${h.phone}</a></div>` : ''}
      </div>
    `);

    // Highlight list item on marker click
    marker.on('click', () => {
      document.querySelectorAll('.hospital-list-item').forEach((el, i) => {
        el.classList.toggle('active', i === idx);
      });
    });
  });

  if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [40, 40] });
  }
}

// Focus map on a hospital when list item clicked
function focusHospital(idx) {
  if (!map) return;
  const items = document.querySelectorAll('.hospital-list-item');
  items.forEach((el, i) => el.classList.toggle('active', i === idx));
  // Trigger layer click — handled via marker.on('click')
}
