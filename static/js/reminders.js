/* ============================================================
   NexVita – reminders.js
   Toggle, edit modal population, delete confirm, filter
   ============================================================ */

'use strict';

async function toggleReminder(id, checkbox) {
  const card = document.getElementById('card-' + id);
  try {
    const res = await fetch(`/reminders/toggle/${id}`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      if (card) card.classList.toggle('inactive', !data.is_active);
      showFlash(data.is_active ? 'Reminder activated!' : 'Reminder paused.', data.is_active ? 'success' : 'info');
    } else {
      checkbox.checked = !checkbox.checked; // revert
    }
  } catch {
    checkbox.checked = !checkbox.checked;
    showFlash('Failed to update reminder.', 'danger');
  }
}

async function deleteReminder(id) {
  if (!confirm('Delete this reminder?')) return;
  try {
    const res = await fetch(`/reminders/delete/${id}`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      const card = document.getElementById('card-' + id);
      if (card) {
        card.style.opacity = '0';
        card.style.transform = 'scale(0.9)';
        card.style.transition = 'all 0.3s ease';
        setTimeout(() => card.remove(), 300);
      }
      showFlash('Reminder deleted.', 'success');
    }
  } catch {
    showFlash('Failed to delete reminder.', 'danger');
  }
}

function openEditModal(id, title, category, time, frequency, notes) {
  document.getElementById('editTitle').value    = title;
  document.getElementById('editTime').value     = time;
  document.getElementById('editNotes').value    = notes;

  const catSel = document.getElementById('editCategory');
  if (catSel) catSel.value = category;

  const freqSel = document.getElementById('editFrequency');
  if (freqSel) freqSel.value = frequency;

  const form = document.getElementById('editReminderForm');
  if (form) form.action = `/reminders/edit/${id}`;

  openModal('editModal');
}

// Filter hospitals in the reminder list (client-side search fallback)
function filterHospitals(q) {
  const items = document.querySelectorAll('.hospital-list-item');
  items.forEach(item => {
    const name = (item.dataset.name || '').toLowerCase();
    const city = (item.dataset.city || '').toLowerCase();
    item.style.display = (name.includes(q.toLowerCase()) || city.includes(q.toLowerCase())) ? '' : 'none';
  });
}
