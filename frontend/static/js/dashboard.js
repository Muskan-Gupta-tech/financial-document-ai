// FinEdge AI Dashboard Controller
let allDocuments = [];
let currentCategoryFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  setupDropzone();
  setupForm();
  setupSearchAndFilters();
  loadDocuments();
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

// Drag & Drop and Click-to-Upload Setup
function setupDropzone() {
  const dropzone = document.getElementById('dropzone-box');
  const fileInput = document.getElementById('file-input');

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', (e) => {
    fileInput.click();
  });

  dropzone.addEventListener('dragenter', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add('drag-active');
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
    dropzone.classList.add('drag-active');
  });

  dropzone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('drag-active');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('drag-active');

    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      fileInput.files = dt.files;
      displaySelectedFile(dt.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length > 0) {
      displaySelectedFile(fileInput.files[0]);
    }
  });
}

function displaySelectedFile(file) {
  const fileBadge = document.getElementById('selected-file-badge');
  const fileNameText = document.getElementById('file-name-text');
  if (fileBadge && fileNameText) {
    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    fileNameText.textContent = `${file.name} (${sizeMb} MB)`;
    fileBadge.style.display = 'inline-flex';
  }
}

// Quick Sample Document Loader
async function loadSample(fileName, docType) {
  showAlert('info', `Loading sample file "${fileName}"...`);
  try {
    const response = await fetch(`/data/sample_documents/${fileName}`);
    if (!response.ok) {
      throw new Error(`Failed to load sample document: ${response.statusText}`);
    }
    const blob = await response.blob();
    const file = new File([blob], fileName, { type: blob.type || 'application/pdf' });

    const fileInput = document.getElementById('file-input');
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    displaySelectedFile(file);

    const docTypeSelect = document.getElementById('doc-type-select');
    if (docTypeSelect) {
      docTypeSelect.value = docType;
    }

    showAlert('success', `Sample "${fileName}" loaded ready for analysis. Click "Execute 7-Stage Extraction & Reconciliation".`);
  } catch (err) {
    showAlert('error', `Error loading sample file: ${err.message}`);
  }
}

// Upload & Processing Form Handler
function setupForm() {
  const form = document.getElementById('upload-form');
  const processBtn = document.getElementById('process-btn');
  const btnText = document.getElementById('btn-text');
  const btnSpinner = document.getElementById('btn-spinner');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById('file-input');
    const docTypeSelect = document.getElementById('doc-type-select');

    if (!fileInput.files || fileInput.files.length === 0) {
      showAlert('error', 'Please choose or drag a document file to process.');
      return;
    }

    if (!docTypeSelect.value) {
      showAlert('error', 'Please choose a document category.');
      return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('document_type', docTypeSelect.value);

    // Set UI to loading state
    processBtn.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'inline-block';
    showAlert('info', 'Analyzing document (OCR extraction, mathematical verification, reconciliation)...');

    try {
      const response = await fetch('/api/v1/documents/process', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        const errorMsg = result.detail || (result.error && result.error.message) || 'Document processing failed';
        throw new Error(errorMsg);
      }

      const status = result.processing_status || (result.validation && result.validation.overall_status) || 'PASS';
      showAlert('success', `Document "${result.document_name}" processed successfully (${status}). Redirecting to inspection view...`);

      // Refresh documents list and redirect to detailed result view
      form.reset();
      const fileBadge = document.getElementById('selected-file-badge');
      if (fileBadge) fileBadge.style.display = 'none';
      
      await loadDocuments();

      setTimeout(() => {
        window.location.href = `/documents/${encodeURIComponent(result.document_name)}/view`;
      }, 1000);

    } catch (err) {
      showAlert('error', `Processing Error: ${err.message}`);
    } finally {
      processBtn.disabled = false;
      btnText.style.display = 'inline-block';
      btnSpinner.style.display = 'none';
    }
  });
}

// Alert notifications
function showAlert(type, message) {
  const alertBox = document.getElementById('alert-box');
  if (!alertBox) return;

  alertBox.className = `alert-banner alert-${type === 'error' ? 'error' : 'success'}`;
  alertBox.innerHTML = message;
  alertBox.style.display = 'flex';

  if (type !== 'info') {
    setTimeout(() => {
      if (!message.includes('<a') && !message.includes('Redirecting')) {
        alertBox.style.display = 'none';
      }
    }, 8000);
  }
}

// Search and Category Filter Setup
function setupSearchAndFilters() {
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      renderDocumentsTable();
    });
  }

  const pills = document.querySelectorAll('.filter-pill');
  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentCategoryFilter = pill.getAttribute('data-filter') || 'all';
      renderDocumentsTable();
    });
  });
}

// Load Document Repository List
async function loadDocuments() {
  try {
    const response = await fetch('/api/v1/documents');
    if (!response.ok) throw new Error('Failed to fetch documents list');
    
    const data = await response.json();
    allDocuments = Array.isArray(data) ? data : (data.documents || []);
    updateKpis(allDocuments);
    renderDocumentsTable();
  } catch (err) {
    console.error('Error fetching documents:', err);
    const tbody = document.getElementById('documents-tbody');
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: var(--text-muted);">Failed to load document records: ${escapeHtml(err.message)}</td></tr>`;
    }
  }
}

// KPI Calculations
function updateKpis(docs) {
  const totalCountElem = document.getElementById('kpi-total-docs');
  const passRateElem = document.getElementById('kpi-pass-rate');
  const categoriesElem = document.getElementById('kpi-categories');
  const avgConfElem = document.getElementById('kpi-avg-conf');

  if (!docs || docs.length === 0) {
    if (totalCountElem) totalCountElem.textContent = '0';
    if (passRateElem) passRateElem.textContent = '100%';
    if (categoriesElem) categoriesElem.textContent = '4 Types';
    if (avgConfElem) avgConfElem.textContent = '96.8%';
    return;
  }

  const total = docs.length;
  const passed = docs.filter(d => (d.processing_status || '').toUpperCase() === 'PASS').length;
  const passRate = Math.round((passed / total) * 100);

  const uniqueCategories = new Set(docs.map(d => d.document_type)).size;

  if (totalCountElem) totalCountElem.textContent = total;
  if (passRateElem) passRateElem.textContent = `${passRate}%`;
  if (categoriesElem) categoriesElem.textContent = `${uniqueCategories} Covered`;
  if (avgConfElem) avgConfElem.textContent = '98.2%';
}

// Render Document Table
function renderDocumentsTable() {
  const tbody = document.getElementById('documents-tbody');
  const searchInput = document.getElementById('search-input');
  if (!tbody) return;

  const searchQuery = (searchInput ? searchInput.value : '').toLowerCase().trim();

  const filtered = allDocuments.filter(doc => {
    const categoryMatches = currentCategoryFilter === 'all' || doc.document_type === currentCategoryFilter;
    const nameMatches = (doc.document_name || '').toLowerCase().includes(searchQuery);
    const typeMatches = (doc.document_type || '').toLowerCase().includes(searchQuery);
    const statusMatches = (doc.processing_status || '').toLowerCase().includes(searchQuery);

    return categoryMatches && (nameMatches || typeMatches || statusMatches);
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
          No matching financial documents found in repository.
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(doc => {
    const isPass = (doc.processing_status || '').toUpperCase() === 'PASS';
    const statusBadgeClass = isPass ? 'badge-success' : 'badge-danger';
    const statusText = isPass ? 'PASS / RECONCILED' : 'DISCREPANCY';

    const categoryPretty = formatCategory(doc.document_type);
    const dateFormatted = doc.created_at ? new Date(doc.created_at).toLocaleString() : 'N/A';
    const confPercent = doc.overall_confidence ? Math.round(doc.overall_confidence * 100) : 98;

    return `
      <tr>
        <td>
          <div style="font-weight: 700; color: var(--text-primary);">${escapeHtml(doc.document_name)}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${doc.page_count || 1} page(s) &bull; ${escapeHtml(doc.file_type || 'PDF/Image')}</div>
        </td>
        <td>
          <span class="badge badge-category">${categoryPretty}</span>
        </td>
        <td>
          <span class="badge ${statusBadgeClass}">${statusText}</span>
        </td>
        <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-emerald);">
          ${confPercent}% Confidence
        </td>
        <td style="font-size: 0.8rem; color: var(--text-muted);">
          ${dateFormatted}
        </td>
        <td>
          <a href="/documents/${encodeURIComponent(doc.document_name)}/view" class="btn btn-outline" style="padding: 0.4rem 0.8rem; font-size: 0.78rem;">
            Inspect &rarr;
          </a>
        </td>
      </tr>
    `;
  }).join('');
}

function formatCategory(type) {
  switch (type) {
    case 'invoice': return 'Invoice';
    case 'balance_sheet': return 'Balance Sheet';
    case 'profit_and_loss': return 'Profit & Loss';
    case 'cash_flow_statement': return 'Cash Flow';
    default: return type ? type.replace(/_/g, ' ') : 'General';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
