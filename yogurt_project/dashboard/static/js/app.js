/* Yogurt Processing System — Frontend Controller */

let currentUser = null;

document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  initSidebar();
  initSidebarToggle();
  document.getElementById('qc-form')?.addEventListener('submit', handleQCSubmit);
});

// ================================================================
// AUTH
// ================================================================
function initAuth() {
  const token = sessionStorage.getItem('yogurt_user');
  if (token) {
    currentUser = JSON.parse(token);
    showApp();
    return;
  }
  document.getElementById('auth-overlay').classList.remove('hidden');
  document.getElementById('login-form').addEventListener('submit', handleLogin);
  document.getElementById('signup-form').addEventListener('submit', handleSignup);
  document.getElementById('show-signup').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('signup-form').classList.remove('hidden');
    document.getElementById('auth-error').classList.add('hidden');
  });
  document.getElementById('show-login').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('signup-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('auth-error').classList.add('hidden');
  });
  document.getElementById('logout-btn').addEventListener('click', () => {
    sessionStorage.removeItem('yogurt_user');
    location.reload();
  });
}

async function handleLogin(e) {
  e.preventDefault();
  const res = await fetch('/api/login/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: document.getElementById('login-user').value, password: document.getElementById('login-pass').value})
  });
  const data = await res.json();
  if (data.status === 'success') {
    currentUser = data.user;
    sessionStorage.setItem('yogurt_user', JSON.stringify(data.user));
    showApp();
  } else {
    showAuthError(data.message || 'Invalid credentials');
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const pass = document.getElementById('signup-pass').value;
  const confirm = document.getElementById('signup-confirm').value;
  if (pass !== confirm) return showAuthError('Passwords do not match');
  const res = await fetch('/api/signup/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: document.getElementById('signup-user').value, password: pass})
  });
  const data = await res.json();
  if (data.status === 'success') {
    showToast('Account created! Please sign in.', 'success');
    document.getElementById('show-login').click();
  } else {
    showAuthError(data.message || 'Signup failed');
  }
}

function showAuthError(msg) {
  const el = document.getElementById('auth-error');
  el.textContent = msg;
  el.classList.remove('hidden');
}

function showApp() {
  document.getElementById('auth-overlay').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  document.getElementById('sidebar-user').textContent = currentUser?.username || 'signed in';
  document.getElementById('sidebar-role').textContent = currentUser?.role || '';
  filterSidebarByRole(currentUser?.role);
  document.getElementById('dash-welcome').textContent = getRoleWelcome(currentUser?.role);
  loadDashboard();
}

function getRoleWelcome(role) {
  const msgs = {
    admin: 'Full system access — manage users and oversee all modules',
    manager: 'Production oversight — monitor batches, inventory, and quality',
    operator: 'Daily operations — track production and machine status',
    inspector: 'Quality assurance — record and review inspection results',
    viewer: 'Read-only view of system dashboards and audit logs'
  };
  return msgs[role] || 'Factory overview at a glance';
}

function filterSidebarByRole(role) {
  document.querySelectorAll('.nav-item').forEach(btn => {
    const roles = (btn.dataset.roles || '').split(',');
    btn.style.display = roles.includes(role) ? '' : 'none';
  });
  // activate the first visible tab
  const first = document.querySelector('.nav-item:not([style*="display: none"])');
  if (first) first.click();
}

// ================================================================
// SIDEBAR
// ================================================================
function initSidebar() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tab = btn.dataset.tab;
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      const target = document.getElementById('tab-' + tab);
      if (target) target.classList.add('active');
      switch (tab) {
        case 'dashboard': loadDashboard(); break;
        case 'inventory': loadInventory(); break;
        case 'batches': loadBatches(); break;
        case 'qc': loadQC(); break;
        case 'machines': loadMachines(); break;
        case 'audit': loadAudit(); break;
        case 'purchasing': loadPurchasing(); break;
        case 'sales': loadSales(); break;
        case 'admin': loadAdmin(); break;
      }
    });
  });
}

// ================================================================
// SIDEBAR TOGGLE (mobile)
// ================================================================
function initSidebarToggle() {
  const toggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!toggle || !sidebar || !overlay) return;
  function open() { sidebar.classList.add('open'); overlay.classList.add('show'); }
  function close() { sidebar.classList.remove('open'); overlay.classList.remove('show'); }
  toggle.addEventListener('click', () => { sidebar.classList.contains('open') ? close() : open(); });
  overlay.addEventListener('click', close);
  // close on nav click (mobile)
  sidebar.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => { if (window.innerWidth < 768) close(); });
  });
  // close on escape
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
}

// ================================================================
// DASHBOARD
// ================================================================
async function loadDashboard() {
  try {
    const res = await fetch('/api/dashboard/');
    const d = await res.json();
    if (d.status !== 'success') return showToast('Dashboard error', 'error');
    const m = d.data;
    document.getElementById('metric-grid').innerHTML = `
      <div class="metric-card"><div class="metric-value">${m.active_batches}</div><div class="metric-label">Active Batches</div></div>
      <div class="metric-card"><div class="metric-value">${m.completed_batches}</div><div class="metric-label">Completed</div></div>
      <div class="metric-card"><div class="metric-value">${m.raw_stock}</div><div class="metric-label">Raw Stock</div></div>
      <div class="metric-card"><div class="metric-value">${m.prod_stock}</div><div class="metric-label">Finished Stock</div></div>
      <div class="metric-card"><div class="metric-value">${m.qc_fails}</div><div class="metric-label">QC Failures</div></div>
      <div class="metric-card"><div class="metric-value">${m.machines_operational}</div><div class="metric-label">Machine Up</div></div>
      <div class="metric-card"><div class="metric-value">${m.pending_orders}</div><div class="metric-label">Pending Orders</div></div>
      <div class="metric-card"><div class="metric-value">${m.recent_audits}</div><div class="metric-label">24h Changes</div></div>
    `;
    // Quick batch & QC
    const br = await fetch('/api/batches/');
    const bd = await br.json();
    if (bd.status === 'success') {
      document.getElementById('dash-batches').innerHTML = bd.batches.slice(0, 5).map(b =>
        `<tr><td data-label="Batch">${b.id}</td><td data-label="Product">${esc(b.product)}</td><td data-label="Status"><span class="badge" style="background:${statusBg(b.status)}15;color:${statusBg(b.status)}">${b.status}</span></td><td data-label="Date">${b.date}</td></tr>`
      ).join('') || '<tr><td colspan="4" class="loading-msg">No data</td></tr>';
    }
    const qr = await fetch('/api/qc/');
    const qd = await qr.json();
    if (qd.status === 'success') {
      document.getElementById('dash-qc').innerHTML = qd.records.slice(0, 5).map(q =>
        `<tr><td data-label="Batch">${q.batch}</td><td data-label="Result" style="color:${q.status === 'Pass' ? 'var(--success)' : q.status === 'Fail' ? 'var(--danger)' : 'var(--warn)'}">${q.status}</td><td data-label="Inspector">${esc(q.inspector||'')}</td></tr>`
      ).join('') || '<tr><td colspan="3" class="loading-msg">No data</td></tr>';
    }
  } catch(e) { showToast('Connection error', 'error'); }
}

// ================================================================
// INVENTORY
// ================================================================
async function loadInventory() {
  try {
    const res = await fetch('/api/inventory/');
    const d = await res.json();
    if (d.status !== 'success') return showToast('Inventory error: '+d.message, 'error');
    document.getElementById('inv-raw-body').innerHTML = d.raw_materials.map(i =>
      `<tr><td data-label="Material">${esc(i.material)}</td><td data-label="On Hand">${i.qty}</td><td data-label="Reserved">${i.reserved}</td><td data-label="UOM">${i.uom}</td><td data-label="Lot">${esc(i.lot)}</td><td data-label="Expiry">${i.expiry||'—'}</td></tr>`
    ).join('') || '<tr><td colspan="6" class="loading-msg">No data</td></tr>';
    document.getElementById('inv-raw-count').textContent = d.raw_materials.length + ' items';
    document.getElementById('inv-prod-body').innerHTML = d.finished_goods.map(i =>
      `<tr><td data-label="Product">${esc(i.product)}</td><td data-label="On Hand">${i.qty}</td><td data-label="Reserved">${i.reserved}</td><td data-label="UOM">${i.uom}</td><td data-label="Batch">${i.batch||'—'}</td><td data-label="Expiry">${i.expiry||'—'}</td></tr>`
    ).join('') || '<tr><td colspan="6" class="loading-msg">No data</td></tr>';
    document.getElementById('inv-prod-count').textContent = d.finished_goods.length + ' items';
  } catch(e) { showToast('Connection error', 'error'); }
}

// ================================================================
// PRODUCTION BATCHES
// ================================================================
async function loadBatches() {
  try {
    const res = await fetch('/api/batches/');
    const d = await res.json();
    if (d.status !== 'success') return showToast('Batches error', 'error');
    document.getElementById('batch-table-body').innerHTML = d.batches.map(b =>
      `<tr><td data-label="ID">${b.id}</td><td data-label="Product">${esc(b.product)}</td><td data-label="Date">${b.date}</td><td data-label="Planned">${b.planned}</td><td data-label="Actual">${b.actual||'—'}</td><td data-label="Status"><span class="badge" style="background:${statusBg(b.status)}15;color:${statusBg(b.status)}">${b.status}</span></td><td data-label="Recipe">${esc(b.recipe||'')}</td><td data-label="By">${esc(b.created_by||'')}</td></tr>`
    ).join('') || '<tr><td colspan="8" class="loading-msg">No data</td></tr>';
  } catch(e) { showToast('Connection error', 'error'); }
}

// ================================================================
// QUALITY CONTROL
// ================================================================
async function loadQC() {
  try {
    const res = await fetch('/api/qc/');
    const d = await res.json();
    if (d.status !== 'success') return;
    document.getElementById('qc-table-body').innerHTML = d.records.map(q =>
      `<tr><td data-label="ID">${q.id}</td><td data-label="Batch">${q.batch}</td><td data-label="Inspector">${esc(q.inspector||'')}</td><td data-label="Result" style="color:${q.status==='Pass'?'var(--success)':q.status==='Fail'?'var(--danger)':'var(--warn)'}">${q.status}</td><td data-label="Remarks">${esc(q.remarks||'')}</td><td data-label="Date">${q.date}</td></tr>`
    ).join('') || '<tr><td colspan="6" class="loading-msg">No data</td></tr>';
  } catch(e) {}
}

async function handleQCSubmit(e) {
  e.preventDefault();
  const payload = {
    batch_id: document.getElementById('qc-batch').value.trim(),
    inspector: document.getElementById('qc-inspector').value.trim(),
    status: document.getElementById('qc-status').value,
    remarks: document.getElementById('qc-remarks').value.trim()
  };
  try {
    const res = await fetch('/api/qc/', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const d = await res.json();
    if (res.ok && d.status === 'success') {
      showToast('QC recorded.', 'success');
      document.getElementById('qc-form').reset();
      loadQC();
    } else showToast(d.message || 'QC failed', 'error');
  } catch(e) { showToast('Network error', 'error'); }
}

// ================================================================
// MACHINES
// ================================================================
async function loadMachines() {
  try {
    const res = await fetch('/api/machines/');
    const d = await res.json();
    if (d.status !== 'success') return;
    document.getElementById('machine-table-body').innerHTML = d.machines.map(m =>
      `<tr><td data-label="ID">${m.id}</td><td data-label="Name">${esc(m.name)}</td><td data-label="Type">${esc(m.type||'')}</td><td data-label="Location">${esc(m.location||'')}</td><td data-label="Status" style="color:${m.status==='Operational'?'var(--success)':'var(--warn)'}">${m.status}</td><td data-label="Purchased">${m.purchased||'—'}</td><td data-label="Maintenance">${m.maint_count}</td><td data-label="Next Due">${m.next_maint||'—'}</td></tr>`
    ).join('') || '<tr><td colspan="8" class="loading-msg">No data</td></tr>';
  } catch(e) { showToast('Connection error', 'error'); }
}

// ================================================================
// AUDIT TRAIL
// ================================================================
async function loadAudit() {
  try {
    const res = await fetch('/api/audit/');
    const d = await res.json();
    if (d.status !== 'success') return;
    document.getElementById('audit-table-body').innerHTML = d.entries.slice(0, 50).map(a =>
      `<tr><td data-label="ID">${a.id}</td><td data-label="Table">${a.table}</td><td data-label="Operation" style="color:${a.operation==='INSERT'?'var(--success)':a.operation==='UPDATE'?'var(--warn)':'var(--danger)'}">${a.operation}</td><td data-label="Record">${a.record_id}</td><td data-label="Changed By">${esc(a.changed_by)}</td><td data-label="Timestamp">${a.changed_at}</td></tr>`
    ).join('') || '<tr><td colspan="6" class="loading-msg">No data</td></tr>';
  } catch(e) { showToast('Connection error', 'error'); }
}

// ================================================================
// PURCHASING
// ================================================================
async function loadPurchasing() {
  try {
    const res = await fetch('/api/purchasing/');
    const d = await res.json();
    if (d.status !== 'success') return;
    document.getElementById('purchase-table-body').innerHTML = d.orders.map(o =>
      `<tr><td data-label="PO#">${o.id}</td><td data-label="Supplier">${esc(o.supplier)}</td><td data-label="Date">${o.date}</td><td data-label="Status">${o.status}</td><td data-label="Total">$${o.total}</td><td data-label="Lines">${o.lines}</td></tr>`
    ).join('') || '<tr><td colspan="6" class="loading-msg">No data</td></tr>';
  } catch(e) { showToast('Connection error', 'error'); }
}

// ================================================================
// SALES
// ================================================================
async function loadSales() {
  try {
    const res = await fetch('/api/sales/');
    const d = await res.json();
    if (d.status !== 'success') return;
    document.getElementById('sales-table-body').innerHTML = d.orders.map(o =>
      `<tr><td data-label="SO#">${o.id}</td><td data-label="Customer">${esc(o.customer)}</td><td data-label="Date">${o.date}</td><td data-label="Status">${o.status}</td><td data-label="Total">$${o.total}</td><td data-label="Lines">${o.lines}</td></tr>`
    ).join('') || '<tr><td colspan="6" class="loading-msg">No data</td></tr>';
  } catch(e) { showToast('Connection error', 'error'); }
}

// ================================================================
// SECURITY TESTS
// ================================================================
async function runTest(type) {
  const placeholder = document.getElementById('sec-result-placeholder');
  const content = document.getElementById('sec-result-content');
  const badge = document.getElementById('sec-result-badge');
  const msg = document.getElementById('sec-result-message');
  placeholder.classList.add('hidden');
  content.classList.remove('hidden');
  badge.textContent = '⏳ Testing...';
  badge.className = 'result-badge';
  msg.textContent = 'Sending request...';
  msg.className = 'result-message';
  try {
    const res = await fetch('/api/trigger-test/', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({test: type, batch_id: 1, qcid: 1, username: 'admin'})});
    const d = await res.json();
    if (res.ok && d.status === 'success') {
      badge.className = 'result-badge success';
      badge.textContent = '⚠ Unexpected Success';
      msg.className = 'result-message';
      msg.textContent = d.message + '\n\nThe constraint did NOT fire!';
      showToast('WARNING: Constraint did not block!', 'error');
    } else {
      badge.className = 'result-badge error';
      badge.textContent = '🔒 Constraint Engaged';
      msg.className = 'result-message err';
      msg.textContent = d.message || 'Unknown error from database.';
      showToast('SECURITY: Database constraint blocked the operation.', 'info');
    }
  } catch(e) {
    badge.className = 'result-badge error';
    badge.textContent = 'Connection Error';
    msg.textContent = 'Could not reach the server.';
  }
}

// ================================================================
// SQL EXPLORER
// ================================================================
async function runSQL() {
  const query = document.getElementById('sql-query').value.trim();
  if (!query) return showToast('Enter a query', 'error');
  try {
    const res = await fetch('/api/sql-explorer/', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query})});
    const d = await res.json();
    if (d.status !== 'success') return showToast(d.message, 'error');
    document.getElementById('sql-count').textContent = d.count + ' rows';
    if (d.columns) {
      document.getElementById('sql-thead').innerHTML = '<tr>' + d.columns.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr>';
      document.getElementById('sql-tbody').innerHTML = d.rows.map(r =>
        '<tr>' + r.map((v, ci) => '<td data-label="' + esc(String(d.columns[ci] ?? '')) + '">' + esc(String(v ?? 'NULL')) + '</td>').join('') + '</tr>'
      ).join('') || '<tr><td colspan="' + d.columns.length + '" class="loading-msg">No results</td></tr>';
    } else {
      document.getElementById('sql-thead').innerHTML = '';
      document.getElementById('sql-tbody').innerHTML = '<tr><td class="loading-msg">' + (d.message || 'Done.') + '</td></tr>';
    }
  } catch(e) { showToast('Query error', 'error'); }
}

// ================================================================
// ADMIN — User Management
// ================================================================
function loadAdmin() {
  loadUsers();
  const form = document.getElementById('admin-user-form');
  form.onsubmit = handleCreateUser;
}

async function loadUsers() {
  try {
    const res = await fetch('/api/users/', {
      headers: {'X-Username': currentUser?.username || ''}
    });
    const d = await res.json();
    if (d.status !== 'success') return showToast(d.message || 'Failed to load users', 'error');
    document.getElementById('admin-user-count').textContent = d.users.length + ' users';
    document.getElementById('admin-users-body').innerHTML = d.users.map(u => `
      <tr>
        <td data-label="ID">${u.id}</td>
        <td data-label="Username">${esc(u.username)}</td>
        <td data-label="Role"><span class="role-badge-sm role-${u.role}">${u.role}</span></td>
        <td data-label="Employee">${esc(u.employee_name) || '—'}</td>
        <td data-label="Active">${u.is_active ? '<span style="color:var(--success)">● Active</span>' : '<span style="color:var(--text-sec)">○ Inactive</span>'}</td>
        <td data-label="Actions">
          ${u.username !== 'admin' ? `<button class="btn-sm btn-danger-sm" onclick="deleteUser(${u.id})">Delete</button>` : '<span style="color:var(--text-sec);font-size:0.7rem">—</span>'}
        </td>
      </tr>
    `).join('');
  } catch(e) { showToast('Connection error', 'error'); }
}

async function handleCreateUser(e) {
  e.preventDefault();
  const payload = {
    username: document.getElementById('admin-username').value.trim(),
    password: document.getElementById('admin-password').value,
    role: document.getElementById('admin-role').value,
    employee_name: document.getElementById('admin-employee').value.trim()
  };
  if (!payload.username || !payload.password) return showToast('Username and password required', 'error');
  try {
    const res = await fetch('/api/users/', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Username': currentUser?.username || ''},
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    if (d.status === 'success') {
      showToast('User created!', 'success');
      document.getElementById('admin-user-form').reset();
      loadUsers();
    } else {
      showToast(d.message || 'Creation failed', 'error');
    }
  } catch(e) { showToast('Network error', 'error'); }
}

async function deleteUser(userId) {
  if (!confirm('Delete this user? This cannot be undone.')) return;
  try {
    const res = await fetch('/api/users/' + userId + '/', {
      method: 'DELETE',
      headers: {'X-Username': currentUser?.username || ''}
    });
    const d = await res.json();
    if (d.status === 'success') {
      showToast('User deleted.', 'info');
      loadUsers();
    } else {
      showToast(d.message || 'Delete failed', 'error');
    }
  } catch(e) { showToast('Network error', 'error'); }
}

// ================================================================
// TOAST
// ================================================================
function showToast(msg, type) {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => { t.classList.add('leave'); setTimeout(() => t.remove(), 250); }, 4000);
}

// ================================================================
// UTILITY
// ================================================================
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function statusBg(s) {
  if (s === 'Completed' || s === 'Pass') return '#22c55e';
  if (s === 'InProgress' || s === 'Processing') return '#f59e0b';
  if (s === 'Planned' || s === 'Pending') return '#3b82f6';
  if (s === 'Fail' || s === 'Cancelled') return '#ef4444';
  return 'var(--text-sec)';
}
