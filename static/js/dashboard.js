/* ============================================================
   NexVita – dashboard.js
   Chart.js initialisation, period tabs, stat animations
   ============================================================ */

'use strict';

let healthChart = null;

function initHealthChart(canvasId, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  const chartColors = {
    systolic:  { border: '#EF4444', bg: 'rgba(239,68,68,.08)' },
    diastolic: { border: '#3B82F6', bg: 'rgba(59,130,246,.08)' },
    heartRate: { border: '#10B981', bg: 'rgba(16,185,129,.08)' },
    weight:    { border: '#8B5CF6', bg: 'rgba(139,92,246,.08)' },
  };

  const buildDatasets = (d) => {
    const sets = [];
    if (d.datasets && d.datasets.length) {
      const labels = ['Systolic BP', 'Diastolic BP', 'Heart Rate', 'Weight (kg)'];
      const colours = [chartColors.systolic, chartColors.diastolic, chartColors.heartRate, chartColors.weight];
      d.datasets.forEach((ds, i) => {
        if (ds.data && ds.data.length) {
          sets.push({
            label: labels[i] || ds.label,
            data: ds.data,
            borderColor: colours[i]?.border || ds.borderColor,
            backgroundColor: colours[i]?.bg || 'transparent',
            fill: true,
            tension: 0.4,
            pointRadius: 5,
            pointHoverRadius: 8,
            pointBackgroundColor: colours[i]?.border || ds.borderColor,
            borderWidth: 2.5,
          });
        }
      });
    }
    return sets;
  };

  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.font.size = 12;

  healthChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels || [],
      datasets: buildDatasets(data),
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: 20,
            font: { weight: '500' },
          },
        },
        tooltip: {
          backgroundColor: 'rgba(255,255,255,.98)',
          titleColor: '#1A1A2E',
          bodyColor: '#64748B',
          borderColor: '#E2E8F0',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          boxPadding: 4,
        },
      },
      scales: {
        x: {
          grid: { color: '#F0F4F8', drawBorder: false },
          ticks: { color: '#94A3B8' },
        },
        y: {
          grid: { color: '#F0F4F8', drawBorder: false },
          ticks: { color: '#94A3B8' },
          beginAtZero: false,
        },
      },
    },
  });

  // Period tab buttons — fetch real data for the selected period
  document.querySelectorAll('#chartTabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', async function () {
      if (this.classList.contains('active')) return;
      document.querySelectorAll('#chartTabs .tab-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');

      const days = parseInt(this.dataset.period, 10) || 7;
      try {
        const res  = await fetch(`/dashboard/chart-data?days=${days}`);
        const json = await res.json();
        if (!res.ok || json.error) return;

        // Update chart labels and datasets
        healthChart.data.labels = json.labels || [];
        const datasets = buildDatasets(json);
        healthChart.data.datasets = datasets;
        healthChart.update();

        // Show or hide empty-state overlay
        const emptyEl = document.getElementById('chartEmpty');
        if (emptyEl) {
          emptyEl.style.display = (!json.labels || json.labels.length === 0) ? 'flex' : 'none';
        }
      } catch (err) {
        // Silently ignore network errors on tab switch; existing data remains visible
        console.warn('Chart period fetch failed:', err);
      }
    });
  });
}
