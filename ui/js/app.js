// /js/app.js
'use strict';

// ---------- helpers ----------
const $ = sel => document.querySelector(sel);

function getCfg() {
  const baseUrl = ($('#baseUrl').value || '').trim().replace(/\/+$/, '');
  const apiKey = ($('#apiKey').value || '').trim();
  return { baseUrl, apiKey };
}
function headersJSON(apiKey) {
  return { 'Content-Type': 'application/json', 'x-api-key': apiKey };
}
function headersForm(apiKey) {
  return { 'x-api-key': apiKey };
}
function saveCfg() {
  const { baseUrl, apiKey } = getCfg();
  localStorage.setItem('civic_baseUrl', baseUrl);
  localStorage.setItem('civic_apiKey', apiKey);
  $('#connMsg').textContent = `Saved. Base=${baseUrl}`;
}
function loadCfg() {
  // Default to https://<host>/api, but keep any saved values
  const defaultBase = (location.origin || '').replace(/\/+$/, '') + '/api';
  const baseUrl = (localStorage.getItem('civic_baseUrl') || defaultBase).replace(/\/+$/, '');
  const apiKey = localStorage.getItem('civic_apiKey') || '';
  $('#baseUrl').value = baseUrl;
  $('#apiKey').value = apiKey;
  $('#connMsg').textContent = `Loaded. Base=${baseUrl}`;
}
function fmtAmount(x) {
  try { return Number(x).toFixed(2); } catch { return x; }
}

async function apiGet(path) {
  const { baseUrl, apiKey } = getCfg();
  const r = await fetch(baseUrl + path, { headers: headersForm(apiKey) });
  const text = await r.text();
  let body = null;
  try { body = JSON.parse(text); } catch { body = text; }
  return { ok: r.ok, status: r.status, body };
}

async function apiPostJSON(path, obj) {
  const { baseUrl, apiKey } = getCfg();
  const r = await fetch(baseUrl + path, {
    method: 'POST',
    headers: headersJSON(apiKey),
    body: JSON.stringify(obj)
  });
  const text = await r.text();
  let body = null;
  try { body = JSON.parse(text); } catch { body = text; }
  return { ok: r.ok, status: r.status, body };
}

async function apiPostForm(path, formData) {
  const { baseUrl, apiKey } = getCfg();
  const r = await fetch(baseUrl + path, {
    method: 'POST',
    headers: headersForm(apiKey),
    body: formData
  });
  const text = await r.text();
  let body = null;
  try { body = JSON.parse(text); } catch { body = text; }
  return { ok: r.ok, status: r.status, body };
}

// ---------- UI wiring ----------
function wireUI() {
  $('#saveConn')?.addEventListener('click', saveCfg);

  // Health
  $('#btnHealth')?.addEventListener('click', async () => {
    const res = await apiGet('/');
    $('#healthOut').textContent = typeof res.body === 'string'
      ? res.body
      : JSON.stringify(res.body, null, 2);
  });

  // Upload file
  $('#btnUploadFile')?.addEventListener('click', async () => {
    const f = $('#billFile').files[0];
    if (!f) { $('#upMsg').innerHTML = '<span class="err">Choose a file</span>'; return; }
    const fd = new FormData();
    fd.append('file', f);
    const res = await apiPostForm('/upload', fd);
    if (res.ok) {
      $('#upMsg').innerHTML = `<span class="ok">Uploaded successfully.</span>`;
      await loadBills();
    } else {
      $('#upMsg').innerHTML = `<span class="err">Upload failed (${res.status}): ${escapeHtml(JSON.stringify(res.body))}</span>`;
    }
  });

  // Upload manual fields
  $('#btnUploadForm')?.addEventListener('click', async () => {
    const vendor = $('#vendor').value.trim();
    const amount = $('#amount').value;
    const due = $('#due').value;
    const note = $('#note').value.trim();
    if (!vendor || !amount || !due) {
      $('#upMsg').innerHTML = '<span class="err">Provide vendor, amount, and due date.</span>'; return;
    }
    const fd = new FormData();
    fd.append('vendor', vendor);
    fd.append('amount', amount);
    fd.append('due_date', due);
    if (note) fd.append('note', note);
    const res = await apiPostForm('/upload', fd);
    if (res.ok) {
      $('#upMsg').innerHTML = `<span class="ok">Uploaded successfully.</span>`;
      await loadBills();
    } else {
      $('#upMsg').innerHTML = `<span class="err">Upload failed (${res.status}): ${escapeHtml(JSON.stringify(res.body))}</span>`;
    }
  });

  // Load bills
  $('#btnLoadBills')?.addEventListener('click', loadBills);
  $('#statusFilter')?.addEventListener('change', loadBills);
}

async function loadBills() {
  const filt = $('#statusFilter').value;
  const path = filt ? `/bills?status=${encodeURIComponent(filt)}` : '/bills';
  const res = await apiGet(path);
  const tbody = $('#billsTbl tbody');
  tbody.innerHTML = '';
  if (!res.ok) {
    $('#listMsg').innerHTML = `<span class="err">Load failed (${res.status}): ${escapeHtml(JSON.stringify(res.body))}</span>`;
    return;
  }
  const items = (res.body && res.body.items) || [];
  for (const b of items) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(b.id)}</td>
      <td>${escapeHtml(b.vendor)}</td>
      <td class="right">${fmtAmount(b.amount)}</td>
      <td>${escapeHtml(b.due_date)}</td>
      <td>${escapeHtml(b.status)}</td>
      <td>
        <button data-id="${b.id}" class="btnPaid">Mark Paid</button>
        <button data-id="${b.id}" class="btnNotify">Notify</button>
      </td>
    `;
    tbody.appendChild(tr);
  }

  // wire actions
  tbody.querySelectorAll('.btnPaid').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      const res = await apiPostJSON(`/bills/${id}/mark_paid`, {});
      if (res.ok) {
        await loadBills();
      } else {
        alert(`Mark paid failed (${res.status}): ${JSON.stringify(res.body)}`);
      }
    });
  });

  tbody.querySelectorAll('.btnNotify').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      const to = prompt("SMS number (E.164) or leave blank for console:", "");
      const payload = { bill_id: id, channel: to ? "sms" : "auto", to: to || undefined };
      const res = await apiPostJSON(`/notify`, payload);
      if (res.ok) {
        alert("Notification sent via " + (res.body.sent_via?.channel || 'console'));
      } else {
        alert(`Notify failed (${res.status}): ${JSON.stringify(res.body)}`);
      }
    });
  });

  $('#listMsg').textContent = items.length ? '' : 'No bills yet.';
}

// utility
function escapeHtml(s) {
  return String(s).replace(/[&<>"'`=\/]/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','`':'&#x60;','=':'&#x3D;'
  }[c]));
}

// auto init after DOM is ready
window.addEventListener('DOMContentLoaded', async () => {
  loadCfg();
  wireUI();
  // auto ping & load (may 401 if key missing)
  try { $('#btnHealth')?.click(); } catch {}
  try { loadBills(); } catch {}
});

