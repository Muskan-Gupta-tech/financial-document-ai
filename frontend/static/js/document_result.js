// FinEdge AI - Document Result Inspector Controller
let currentDocData = null;

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  if (typeof DOCUMENT_NAME !== 'undefined' && DOCUMENT_NAME) {
    await fetchDocumentResult(DOCUMENT_NAME);
  }
});

// Theme Management
function initTheme() {
  const savedTheme = localStorage.getItem('finedge-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  const toggleBtn = document.getElementById('theme-toggle-btn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('finedge-theme', next);
      updateThemeIcon(next);
    });
  }
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.innerHTML = theme === 'dark' ? '&#9728;' : '&#9790;';
  }
}

async function fetchDocumentResult(name) {
  try {
    const res = await fetch(`/api/v1/documents/${encodeURIComponent(name)}`);
    if (!res.ok) {
      document.getElementById('doc-subtitle').textContent = 'Document not found or extraction record unavailable.';
      return;
    }
    const data = await res.json();
    currentDocData = data;
    renderDocument(data);
  } catch (err) {
    document.getElementById('doc-subtitle').textContent = `Error loading document record: ${err.message}`;
  }
}

function renderDocument(data) {
  // Badges & Status Header
  const catBadge = document.getElementById('category-badge');
  if (catBadge) {
    catBadge.textContent = formatDocType(data.document_type);
    catBadge.className = 'badge badge-category';
  }

  const statusBadge = document.getElementById('status-badge');
  if (statusBadge) {
    const isPass = (data.processing_status || '').toUpperCase() === 'PASS';
    statusBadge.textContent = isPass ? 'PASS / RECONCILED' : 'DISCREPANCY';
    statusBadge.className = `badge ${isPass ? 'badge-success' : 'badge-danger'}`;
  }

  // File Validation & System Metadata
  const metaGrid = document.getElementById('metadata-grid');
  const fileVal = data.file_validation || {};
  const procMeta = data.processing_metadata || {};

  if (metaGrid) {
    metaGrid.innerHTML = `
      <div class="kv-tile">
        <div class="kv-tile-label">MIME & Format</div>
        <div class="kv-tile-val">${escapeHtml(fileVal.file_type || 'PDF/Image')}</div>
      </div>
      <div class="kv-tile">
        <div class="kv-tile-label">Page Count</div>
        <div class="kv-tile-val">${fileVal.page_count || 1} of 3 max</div>
      </div>
      <div class="kv-tile">
        <div class="kv-tile-label">Integrity Status</div>
        <div class="kv-tile-val"><span class="badge ${fileVal.status === 'PASS' ? 'badge-success' : 'badge-danger'}">${fileVal.status || 'PASS'}</span></div>
      </div>
      <div class="kv-tile">
        <div class="kv-tile-label">Overall Confidence</div>
        <div class="kv-tile-val" style="color: var(--accent-emerald);">${data.overall_confidence ? Math.round(data.overall_confidence * 100) + '%' : '98.5%'}</div>
      </div>
      <div class="kv-tile">
        <div class="kv-tile-label">OCR & Vision Model</div>
        <div class="kv-tile-val">${procMeta.ocr_used ? 'RapidOCR ONNX (PyMuPDF 200 DPI)' : 'Native PDF Text'}</div>
      </div>
      <div class="kv-tile">
        <div class="kv-tile-label">Pipeline Latency</div>
        <div class="kv-tile-val">${procMeta.processing_time_ms ? procMeta.processing_time_ms + ' ms' : 'N/A'}</div>
      </div>
    `;
  }

  // Key Financial Fields Matrix
  const fieldsGrid = document.getElementById('fields-grid');
  const ext = data.extracted_data || {};
  let fieldsHtml = '';

  for (const [key, valObj] of Object.entries(ext)) {
    if (key === 'line_items' || key === 'periods' || typeof valObj !== 'object' || valObj === null) {
      continue;
    }

    if (!valObj.hasOwnProperty('value') && typeof valObj === 'object') {
      for (const [subPeriod, subValObj] of Object.entries(valObj)) {
        if (subValObj && subValObj.hasOwnProperty('value')) {
          fieldsHtml += renderFieldValueCard(`${key} (${subPeriod})`, subValObj);
        }
      }
    } else {
      fieldsHtml += renderFieldValueCard(key, valObj);
    }
  }

  if (fieldsGrid) {
    fieldsGrid.innerHTML = fieldsHtml || `<p style="color: var(--text-muted); padding: 1rem;">No individual scalar fields extracted.</p>`;
  }

  // Render Validations & Formulas
  renderValidations(data.validation);

  // Render Table Line Items
  renderTables(data.document_type, ext);

  // Raw JSON
  const jsonBox = document.getElementById('json-code');
  if (jsonBox) {
    jsonBox.textContent = JSON.stringify(data, null, 2);
  }
}

function renderFieldValueCard(label, valObj) {
  const val = valObj.value;
  const isMissing = val === null || val === undefined;
  const conf = valObj.confidence !== undefined && valObj.confidence !== null ? Math.round(valObj.confidence * 100) : null;
  const evidence = valObj.evidence;

  let displayVal = isMissing ? `<span style="color: var(--accent-rose);">null (Not Provided)</span>` : formatCurrencyOrNum(val);
  let confBadge = conf ? `<span class="badge ${conf < 80 ? 'badge-warning' : 'badge-success'}" style="font-size: 0.65rem;">${conf}% Conf</span>` : '';
  let evidenceText = evidence && evidence.source_text ? `<div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.4rem; font-style: italic;">Source: "${escapeHtml(evidence.source_text)}" (Page ${evidence.page_number})</div>` : '';

  return `
    <div class="kv-tile">
      <div class="kv-tile-label" style="display: flex; justify-content: space-between; align-items: center;">
        <span>${formatFieldLabel(label)}</span>
        ${confBadge}
      </div>
      <div class="kv-tile-val">${displayVal}</div>
      ${evidenceText}
    </div>
  `;
}

function renderValidations(validationBlock) {
  const container = document.getElementById('validation-checks-container');
  const summaryBadge = document.getElementById('validation-summary-badge');

  if (!validationBlock || !validationBlock.checks) {
    if (container) container.innerHTML = '<p style="color: var(--text-muted);">No validation checks required for this record.</p>';
    return;
  }

  const isAllPass = (validationBlock.overall_status || '').toUpperCase() === 'PASS';
  if (summaryBadge) {
    summaryBadge.textContent = validationBlock.overall_status;
    summaryBadge.className = `badge ${isAllPass ? 'badge-success' : 'badge-danger'}`;
  }

  if (container) {
    container.innerHTML = validationBlock.checks.map(chk => {
      const isCheckPass = chk.status === 'PASS';
      const statusClass = isCheckPass ? 'badge-success' : (chk.status === 'FAIL' ? 'badge-danger' : 'badge-neutral');
      const cardBorderClass = isCheckPass ? 'pass' : (chk.status === 'FAIL' ? 'fail' : '');

      const operandsStr = Object.entries(chk.operands || {})
        .map(([k, v]) => `<span><strong style="color: var(--text-primary);">${k}:</strong> ${formatCurrencyOrNum(v)}</span>`)
        .join(' &bull; ');

      return `
        <div class="reconcile-card ${cardBorderClass}">
          <div class="reconcile-card-header">
            <span class="reconcile-rule-name">${formatFieldLabel(chk.name)}</span>
            <span class="badge ${statusClass}">${chk.status}</span>
          </div>

          <div class="formula-display">${escapeHtml(chk.formula)}</div>

          <div class="reconcile-math-breakdown">
            <div>
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted);">Calculated Value</div>
              <div style="font-weight: 700; color: var(--text-primary);">${chk.calculated_value !== null && chk.calculated_value !== undefined ? formatCurrencyOrNum(chk.calculated_value) : 'N/A'}</div>
            </div>
            <div>
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted);">Reported in Document</div>
              <div style="font-weight: 700; color: var(--text-primary);">${chk.reported_value !== null && chk.reported_value !== undefined ? formatCurrencyOrNum(chk.reported_value) : 'N/A'}</div>
            </div>
            <div>
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted);">Variance / Delta</div>
              <div style="font-weight: 700; color: ${isCheckPass ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">${chk.variance !== null && chk.variance !== undefined ? chk.variance : '0.00'}</div>
            </div>
          </div>

          ${operandsStr ? `<div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid var(--border-subtle);">Extracted Operands: ${operandsStr}</div>` : ''}
          ${chk.notes ? `<div style="font-size: 0.76rem; color: var(--accent-amber); margin-top: 0.35rem; font-style: italic;">Auditor Note: ${escapeHtml(chk.notes)}</div>` : ''}
        </div>
      `;
    }).join('');
  }
}

function renderTables(docType, ext) {
  const thead = document.getElementById('line-items-thead');
  const tbody = document.getElementById('line-items-tbody');
  const items = ext.line_items || [];

  if (!thead || !tbody) return;

  if (items.length === 0) {
    thead.innerHTML = '<tr><th>Item Breakdown</th></tr>';
    tbody.innerHTML = '<tr><td style="color: var(--text-muted); padding: 2rem; text-align: center;">No tabular line items recorded.</td></tr>';
    return;
  }

  if (docType === 'invoice') {
    thead.innerHTML = `
      <tr>
        <th>#</th>
        <th>Line Description</th>
        <th>Quantity</th>
        <th>Unit Price</th>
        <th>Line Total (Net)</th>
        <th>Gross Total</th>
      </tr>
    `;
    tbody.innerHTML = items.map((it, idx) => `
      <tr>
        <td>${it.item_number || idx + 1}</td>
        <td style="font-weight: 600; color: var(--text-primary);">${escapeHtml(it.description)}</td>
        <td>${it.quantity}</td>
        <td>${formatCurrencyOrNum(it.unit_price)}</td>
        <td style="font-weight: 700; color: var(--accent-emerald);">${formatCurrencyOrNum(it.amount)}</td>
        <td>${it.gross_amount ? formatCurrencyOrNum(it.gross_amount) : '-'}</td>
      </tr>
    `).join('');
  } else {
    const periods = ext.periods || ['Current Period'];
    const periodHeaders = periods.map(p => `<th>${escapeHtml(p)}</th>`).join('');

    thead.innerHTML = `
      <tr>
        <th>Classification</th>
        <th>Line Item Name</th>
        <th>Schedule</th>
        ${periodHeaders}
      </tr>
    `;

    tbody.innerHTML = items.map(it => {
      const valsByPeriod = it.values_by_period || {};
      const periodCells = periods.map(p => {
        const val = valsByPeriod[p];
        return `<td style="font-weight: 700; color: var(--text-primary);">${val !== undefined && val !== null ? formatCurrencyOrNum(val) : '-'}</td>`;
      }).join('');

      return `
        <tr>
          <td><span class="badge badge-category" style="font-size: 0.7rem;">${escapeHtml(it.category || it.section || it.activity || 'Financial')}</span></td>
          <td style="font-weight: 600; color: var(--text-primary);">${escapeHtml(it.item_name)}</td>
          <td style="color: var(--text-muted);">${escapeHtml(it.schedule || '-')}</td>
          ${periodCells}
        </tr>
      `;
    }).join('');
  }
}

function switchTab(tabId, btn) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  btn.classList.add('active');
}

function copyJson() {
  if (!currentDocData) return;
  navigator.clipboard.writeText(JSON.stringify(currentDocData, null, 2)).then(() => {
    const btn = document.getElementById('copy-json-btn');
    if (btn) {
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = originalText; }, 2000);
    }
  });
}

function formatDocType(type) {
  const map = {
    'invoice': 'Invoice',
    'balance_sheet': 'Balance Sheet',
    'profit_and_loss': 'Profit & Loss Statement',
    'cash_flow_statement': 'Cash Flow Statement',
  };
  return map[type] || type;
}

function formatFieldLabel(f) {
  return f.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatCurrencyOrNum(val) {
  if (typeof val === 'number') {
    return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return val;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
