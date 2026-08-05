/**
 * health.js — Dynamic Medical Records Management
 * Handles: modal, tag chips, file upload, search/filter,
 *          view toggle, table sort, async delete/duplicate,
 *          BMI calc, charts, print.
 */

/* ── Constants ─────────────────────────────────────────────── */
const PRESET_TYPES = window.PRESET_TYPES || [];
const CATEGORIES   = window.CATEGORIES   || {};

/* ── DOM Helpers ────────────────────────────────────────────── */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

/* ── Modal ──────────────────────────────────────────────────── */
const overlay   = $('#healthModalOverlay');
const modalForm = $('#healthRecordForm');

function openModal(mode = 'add', recordData = null) {
  if (!overlay) return;
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';

  const title = $('#modalTitle');
  if (mode === 'add') {
    title && (title.textContent = 'Add Health Record');
    modalForm && modalForm.reset();
    clearTagChips();
    clearFilePreview();
    setBMIDisplay(null);
    modalForm && (modalForm.action = '/health/add');
    $('#modalMethodField') && ($('#modalMethodField').value = '');
  } else if (mode === 'edit' && recordData) {
    title && (title.textContent = 'Edit Health Record');
    populateForm(recordData);
    modalForm && (modalForm.action = `/health/edit/${recordData.id}`);
  }
  // Re-init Lucide icons inside modal
  if (window.lucide) lucide.createIcons();
}

function closeModal() {
  if (!overlay) return;
  overlay.classList.remove('open');
  document.body.style.overflow = '';
}
// Expose to global for inline onclick attributes
window.closeModal = closeModal;
window.openModal  = openModal;

// Close on overlay click or ESC
overlay && overlay.addEventListener('click', e => {
  if (e.target === overlay) closeModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// Open modal buttons
$$('[data-open-modal="add"]').forEach(btn => {
  btn.addEventListener('click', () => openModal('add'));
});

/* ── Populate Edit Form ─────────────────────────────────────── */
function populateForm(data) {
  const set = (name, val) => {
    const el = modalForm ? modalForm.querySelector(`[name="${name}"]`) : null;
    if (!el) return;
    el.value = val || '';
  };

  set('record_type',   data.record_type);
  set('title',         data.title);
  set('category',      data.category);
  set('description',   data.description);
  set('result_value',  data.result_value);
  set('result_unit',   data.result_unit);
  set('severity',      data.severity);
  set('status',        data.status);
  set('doctor_name',   data.doctor_name);
  set('hospital_name', data.hospital_name);
  set('notes',         data.notes);

  // Dates — strip time for date inputs
  if (data.record_date) set('record_date', data.record_date.slice(0,16));
  if (data.follow_up_date) set('follow_up_date', data.follow_up_date.slice(0,16));

  // Tags
  clearTagChips();
  (data.tags || []).forEach(addTagChip);

  // Highlight preset type btn
  $$('.preset-type-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.value === data.record_type);
  });

  // Highlight category
  highlightCategory(data.category);
}

/* ── Preset Type Buttons ────────────────────────────────────── */
$$('.preset-type-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const val = btn.dataset.value;
    const cat = btn.dataset.category;
    $$('.preset-type-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');

    const rtField = modalForm && modalForm.querySelector('[name="record_type"]');
    const catField = modalForm && modalForm.querySelector('[name="category"]');
    if (rtField) rtField.value = val;
    if (catField) { catField.value = cat; highlightCategory(cat); }

    // Auto-fill title if empty
    const titleField = modalForm && modalForm.querySelector('[name="title"]');
    if (titleField && !titleField.value) titleField.value = btn.textContent.trim();
  });
});

function highlightCategory(cat) {
  $$('.modal-cat-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.cat === cat);
  });
}

/* ── Tag Chip Input ─────────────────────────────────────────── */
const tagWrap    = $('#tagInputWrap');
const tagHidden  = $('#tagsHiddenInput');
const tagField   = $('#tagTextField');
let tagList = [];

function addTagChip(tag) {
  tag = tag.trim().toLowerCase();
  if (!tag || tagList.includes(tag)) return;
  tagList.push(tag);

  const chip = document.createElement('span');
  chip.className = 'tag-chip-item';
  chip.innerHTML = `${tag}<button type="button" onclick="removeTag('${tag}', this)">
    <svg data-lucide="x"></svg></button>`;
  tagWrap && tagWrap.insertBefore(chip, tagField);
  if (window.lucide) lucide.createIcons();
  syncTagsHidden();
}

function removeTag(tag, btn) {
  tagList = tagList.filter(t => t !== tag);
  btn.closest('.tag-chip-item').remove();
  syncTagsHidden();
}
window.removeTag = removeTag;

function clearTagChips() {
  tagList = [];
  $$('.tag-chip-item', tagWrap || document).forEach(c => c.remove());
  syncTagsHidden();
}

function syncTagsHidden() {
  if (tagHidden) tagHidden.value = tagList.join(',');
}

tagField && tagField.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault();
    addTagChip(tagField.value);
    tagField.value = '';
  }
  if (e.key === 'Backspace' && !tagField.value && tagList.length) {
    removeTag(tagList[tagList.length - 1], tagWrap.querySelector('.tag-chip-item:last-of-type button'));
  }
});
tagWrap && tagWrap.addEventListener('click', () => tagField && tagField.focus());

/* ── File Upload Zone ───────────────────────────────────────── */
const uploadZone = $('#fileUploadZone');
const fileInput  = $('#attachmentInput');
const filePreviewEl = $('#filePreviewArea');

fileInput && fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (file) showFilePreview(file);
});

uploadZone && uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
uploadZone && uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('drag-over');
});
uploadZone && uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && fileInput) {
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    showFilePreview(file);
  }
});

function showFilePreview(file) {
  if (!filePreviewEl) return;
  uploadZone && uploadZone.classList.add('has-file');
  const size = (file.size / 1024).toFixed(1);
  filePreviewEl.innerHTML = `
    <div class="file-preview">
      <svg data-lucide="file-check"></svg>
      <div class="file-preview-info">
        <div class="file-preview-name">${file.name}</div>
        <div class="file-preview-meta">${size} KB</div>
      </div>
      <button type="button" class="file-preview-remove" onclick="clearFilePreview()">
        <svg data-lucide="x"></svg>
      </button>
    </div>`;
  filePreviewEl.style.display = 'block';
  if (window.lucide) lucide.createIcons();
}

function clearFilePreview() {
  if (fileInput) fileInput.value = '';
  if (filePreviewEl) { filePreviewEl.innerHTML = ''; filePreviewEl.style.display = 'none'; }
  uploadZone && uploadZone.classList.remove('has-file');
}
window.clearFilePreview = clearFilePreview;

/* ── BMI Calculator ─────────────────────────────────────────── */
const weightInput = $('#weightInput');
const heightInput = $('#heightInput');
const bmiDisplay  = $('#bmiDisplay');

function calcBMI() {
  const w = parseFloat(weightInput && weightInput.value);
  const h = parseFloat(heightInput && heightInput.value);
  if (!w || !h || h <= 0) { setBMIDisplay(null); return; }
  const bmi = w / ((h / 100) ** 2);
  setBMIDisplay(bmi);
}
window.calcBMI = calcBMI;

function setBMIDisplay(bmi) {
  if (!bmiDisplay) return;
  if (!bmi) { bmiDisplay.style.display = 'none'; return; }
  let label = '', cls = '';
  if (bmi < 18.5)      { label = 'Underweight'; cls = 'badge-warning'; }
  else if (bmi < 25)   { label = 'Normal';      cls = 'badge-success'; }
  else if (bmi < 30)   { label = 'Overweight';  cls = 'badge-warning'; }
  else                 { label = 'Obese';        cls = 'badge-danger';  }

  bmiDisplay.style.display = 'flex';
  bmiDisplay.className = `bmi-badge ${cls}`;
  bmiDisplay.innerHTML = `<svg data-lucide="calculator"></svg>BMI: <strong>${bmi.toFixed(1)}</strong> — ${label}`;
  if (window.lucide) lucide.createIcons();
}

weightInput && weightInput.addEventListener('input', calcBMI);
heightInput && heightInput.addEventListener('input', calcBMI);

/* ── View Toggle (Table / Timeline) ────────────────────────── */
const tableView    = $('#tableView');
const timelineView = $('#timelineView');

$$('.view-toggle-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.view;
    $$('.view-toggle-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    if (mode === 'table') {
      tableView    && (tableView.style.display = '');
      timelineView && (timelineView.style.display = 'none');
    } else {
      tableView    && (tableView.style.display = 'none');
      timelineView && (timelineView.style.display = '');
    }
    // Persist preference in URL without page reload
    const url = new URL(window.location);
    url.searchParams.set('view', mode);
    window.history.replaceState({}, '', url);
  });
});

/* ── Live Search / Filter (client-side for current page) ───── */
const searchInput = $('#healthSearchInput');

searchInput && searchInput.addEventListener('input', debounce(function() {
  const q = this.value.toLowerCase();
  $$('.health-table tbody tr').forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(q) ? '' : 'none';
  });
  $$('.timeline-entry').forEach(entry => {
    const text = entry.textContent.toLowerCase();
    entry.style.display = text.includes(q) ? '' : 'none';
  });
}, 200));

/* ── Server-side filter form auto-submit ─────────────────────  */
$$('.health-filter-select, .health-date-input').forEach(el => {
  el.addEventListener('change', () => {
    const form = el.closest('form');
    if (form) form.submit();
  });
});

/* ── Table Sort ─────────────────────────────────────────────── */
let sortCol = -1, sortAsc = true;

$$('.health-table th[data-sort]').forEach((th, idx) => {
  th.addEventListener('click', () => {
    const tbody = th.closest('table').querySelector('tbody');
    if (!tbody) return;
    sortAsc = sortCol === idx ? !sortAsc : true;
    sortCol = idx;

    $$('.health-table th').forEach(h => h.classList.remove('sorted'));
    th.classList.add('sorted');

    const rows = [...tbody.querySelectorAll('tr')];
    rows.sort((a, b) => {
      const aT = a.cells[idx]?.textContent.trim() || '';
      const bT = b.cells[idx]?.textContent.trim() || '';
      return sortAsc ? aT.localeCompare(bT) : bT.localeCompare(aT);
    });
    rows.forEach(r => tbody.appendChild(r));
  });
});

/* ── Async Delete ───────────────────────────────────────────── */
$$('.delete-record-btn').forEach(btn => {
  btn.addEventListener('click', async function() {
    const id   = this.dataset.id;
    const name = this.dataset.name || 'this record';
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;

    try {
      const res = await fetch(`/health/delete/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (data.success) {
        // Remove row from table
        const row = this.closest('tr');
        if (row) {
          row.style.transition = 'opacity 0.3s, transform 0.3s';
          row.style.opacity = '0';
          row.style.transform = 'translateX(20px)';
          setTimeout(() => { row.remove(); updateRecordCount(-1); }, 300);
        }
        // Remove timeline entry
        const tlEntry = document.querySelector(`.timeline-entry[data-id="${id}"]`);
        if (tlEntry) {
          tlEntry.style.opacity = '0';
          setTimeout(() => tlEntry.remove(), 300);
        }
        showToast('Record deleted successfully', 'success');
      } else {
        showToast(data.message || 'Delete failed', 'danger');
      }
    } catch (err) {
      showToast('Network error. Please try again.', 'danger');
    }
  });
});

/* ── Async Duplicate ────────────────────────────────────────── */
$$('.duplicate-record-btn').forEach(btn => {
  btn.addEventListener('click', async function() {
    const id = this.dataset.id;
    try {
      const res  = await fetch(`/health/duplicate/${id}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showToast('Record duplicated! Refresh to see it.', 'success');
        setTimeout(() => window.location.reload(), 1200);
      } else {
        showToast(data.message || 'Duplicate failed', 'danger');
      }
    } catch {
      showToast('Network error.', 'danger');
    }
  });
});

/* ── Edit Record (fetch data + open modal) ───────────────────── */
$$('.edit-record-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    const data = JSON.parse(this.dataset.record || '{}');
    openModal('edit', data);
  });
});

/* ── Print Record ────────────────────────────────────────────── */
$$('.print-record-btn').forEach(btn => {
  btn.addEventListener('click', () => window.print());
});

/* ── Record count badge ──────────────────────────────────────── */
function updateRecordCount(delta) {
  const el = $('#recordCountBadge');
  if (!el) return;
  const cur = parseInt(el.textContent) || 0;
  el.textContent = Math.max(0, cur + delta);
}

/* ── Toast notifications ─────────────────────────────────────── */
function showToast(msg, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  const colors = { success: '#10B981', danger: '#EF4444', info: '#3B82F6', warning: '#F59E0B' };
  toast.style.cssText = `
    background:${colors[type] || colors.info};color:white;
    padding:12px 20px;border-radius:10px;font-size:14px;font-weight:600;
    box-shadow:0 4px 16px rgba(0,0,0,.2);
    animation:slideInRight .3s ease;max-width:320px;
  `;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity .3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

/* ── Chart Initialization (charts.html) ─────────────────────── */
async function initCharts() {
  const canvas = document.querySelectorAll('[data-chart]');
  if (!canvas.length) return;
  if (!window.Chart) return;

  try {
    const res  = await fetch('/health/api/chart-data?limit=30');
    const data = await res.json();
    const labels = data.labels;
    const ds     = data.datasets;

    const chartDefs = [
      {
        id: 'bpChart', title: 'Blood Pressure',
        datasets: [
          { label: 'Systolic (mmHg)',  data: ds.systolic_bp,  borderColor: '#EF4444', backgroundColor: 'rgba(239,68,68,.1)', tension: .4 },
          { label: 'Diastolic (mmHg)', data: ds.diastolic_bp, borderColor: '#3B82F6', backgroundColor: 'rgba(59,130,246,.1)', tension: .4 },
        ]
      },
      {
        id: 'hrChart', title: 'Heart Rate',
        datasets: [{ label: 'Heart Rate (bpm)', data: ds.heart_rate, borderColor: '#F59E0B', backgroundColor: 'rgba(245,158,11,.1)', tension: .4 }]
      },
      {
        id: 'glucoseChart', title: 'Blood Sugar',
        datasets: [{ label: 'Glucose (mg/dL)', data: ds.glucose_level, borderColor: '#7C3AED', backgroundColor: 'rgba(124,58,237,.1)', tension: .4 }]
      },
      {
        id: 'weightChart', title: 'Weight Trend',
        datasets: [{ label: 'Weight (kg)', data: ds.weight, borderColor: '#00C897', backgroundColor: 'rgba(0,200,151,.1)', tension: .4, fill: true }]
      },
      {
        id: 'bmiChart', title: 'BMI Trend',
        datasets: [{ label: 'BMI', data: ds.bmi, borderColor: '#10B981', backgroundColor: 'rgba(16,185,129,.1)', tension: .4, fill: true }]
      },
      {
        id: 'tempChart', title: 'Temperature',
        datasets: [{ label: 'Temperature (°C)', data: ds.temperature, borderColor: '#EC4899', backgroundColor: 'rgba(236,72,153,.1)', tension: .4 }]
      },
    ];

    chartDefs.forEach(def => {
      const canvas = document.getElementById(def.id);
      if (!canvas) return;
      new Chart(canvas, {
        type: 'line',
        data: { labels, datasets: def.datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: def.datasets.length > 1, position: 'top', labels: { font: { size: 11, family: 'Inter' }, boxWidth: 12 } },
            tooltip: { backgroundColor: '#1A1A2E', titleFont: { family: 'Inter', size: 12 }, bodyFont: { family: 'Inter', size: 11 }, padding: 10, cornerRadius: 8 }
          },
          scales: {
            x: { grid: { color: '#E2E8F0' }, ticks: { font: { size: 10, family: 'Inter' }, color: '#64748B', maxTicksLimit: 8 } },
            y: { grid: { color: '#E2E8F0' }, ticks: { font: { size: 10, family: 'Inter' }, color: '#64748B' } }
          }
        }
      });
    });
  } catch (err) {
    console.warn('Chart data fetch failed:', err);
  }
}

/* ── Utility: Debounce ───────────────────────────────────────── */
function debounce(fn, wait) {
  let t;
  return function(...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), wait); };
}

/* ── Init on DOMContentLoaded ────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initCharts();

  // Auto-open modal if directed by server (e.g., validation error)
  if (window.OPEN_MODAL) openModal('add');

  // Sync view toggle with URL param on load
  const urlView = new URLSearchParams(window.location.search).get('view');
  if (urlView) {
    const btn = document.querySelector(`.view-toggle-btn[data-view="${urlView}"]`);
    if (btn) btn.click();
  }
});
