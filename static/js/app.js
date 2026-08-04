/* ============================================================
   NexVita – app.js
   Global utilities: ripple, modals, scroll reveal, CSRF
   ============================================================ */

'use strict';

// ===== Modal Helpers =====
function openModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.add('open'); document.body.style.overflow = 'hidden'; }
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.remove('open'); document.body.style.overflow = ''; }
}

// Close modal on overlay click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// Close modal on Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => {
      m.classList.remove('open');
      document.body.style.overflow = '';
    });
  }
});

// ===== Ripple Effect =====
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.btn-ripple').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      ripple.classList.add('ripple-effect');
      const rect = this.getBoundingClientRect();
      ripple.style.left = (e.clientX - rect.left) + 'px';
      ripple.style.top  = (e.clientY - rect.top) + 'px';
      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 600);
    });
  });
});

// ===== Scroll Reveal =====
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));
});

// ===== Format Helpers =====
function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatTime(dateStr) {
  return new Date(dateStr).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// ===== Fetch with CSRF =====
async function fetchJSON(url, method = 'GET', data = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
  };
  if (data && method !== 'GET') opts.body = JSON.stringify(data);
  const res = await fetch(url, opts);
  return res.json();
}

// ===== Flash Toast (programmatic) =====
function showFlash(msg, type = 'info') {
  const icons = { success: 'check-circle', danger: 'x-circle', warning: 'alert-triangle', info: 'info' };
  const container = document.getElementById('flashContainer');
  if (!container) return;

  const el = document.createElement('div');
  el.className = `flash ${type}`;
  el.innerHTML = `
    <svg class="flash__icon" data-lucide="${icons[type] || 'info'}"></svg>
    <div class="flash__body"><p class="flash__msg">${msg}</p></div>
    <button class="flash__close" onclick="this.closest('.flash').remove()">
      <svg data-lucide="x"></svg>
    </button>
  `;
  container.appendChild(el);
  if (window.lucide) lucide.createIcons({ nodes: [el] });

  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(100%)';
    el.style.transition = 'all 0.4s ease';
    setTimeout(() => el.remove(), 400);
  }, 5000);
}
