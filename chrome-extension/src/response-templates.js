/**
 * SheetGPT - Response Templates
 * Шаблоны для отображения AI ответов
 */

console.log('[ResponseTemplates] Loading...');

// ===== LOADING MESSAGE =====
function createLoadingMessage() {
  return `
    <div class="loading-message" id="loadingMessage">
      <div class="loading-bubble">
        <div class="loading-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <line x1="3" y1="9" x2="21" y2="9"/>
            <line x1="9" y1="3" x2="9" y2="21"/>
          </svg>
        </div>
        <div class="loading-content">
          <div class="loading-title">Анализирую данные...</div>
          <div class="loading-status">
            <div class="loading-progress">
              <div class="loading-progress-bar"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== FORMULA RESPONSE =====
function createFormulaResponse(result) {
  const formulaEscaped = (result.formula || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
  return `
    <div class="message message-ai">
      <div class="bubble">
        <div class="ai-response">
          <div class="response-header">
            <div class="response-type-icon formula">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM17 14v7M14 17h6"/>
              </svg>
            </div>
            <span class="response-type-label">Формула</span>
          </div>
          <div class="response-body">
            <div class="formula-block">
              <code>${result.formula || ''}</code>
              <button class="copy-btn" onclick="copyFormula('${formulaEscaped}')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
              </button>
            </div>
            ${result.explanation ? `<div class="response-explanation">${result.explanation}</div>` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== ANALYSIS RESPONSE =====
function createAnalysisResponse(result) {
  const findings = result.key_findings || result.findings || [];
  const findingsList = findings.length > 0
    ? `<ul class="findings-list">${findings.map(f => `<li>${f}</li>`).join('')}</ul>`
    : '';

  return `
    <div class="message message-ai">
      <div class="bubble">
        <div class="ai-response">
          <div class="response-header">
            <div class="response-type-icon analysis">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 3v18h18"/>
                <path d="M7 12l4-4 4 4 5-5"/>
              </svg>
            </div>
            <span class="response-type-label">Анализ</span>
          </div>
          <div class="response-body">
            <div class="response-result">${result.summary || result.explanation || 'Результат'}</div>
            ${result.value !== undefined ? `
              <div class="result-value">
                <span>${result.value}</span>
              </div>
            ` : ''}
            ${findingsList}
            ${result.methodology ? `<div class="response-explanation">${result.methodology}</div>` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== ANALYSIS WITH SHEET OFFER =====
function createAnalysisWithSheetOffer(result) {
  const findings = result.key_findings || result.findings || [];
  const findingsList = findings.length > 0
    ? `<ul class="findings-list">${findings.map(f => `<li>${f}</li>`).join('')}</ul>`
    : '';

  const structuredDataJson = JSON.stringify(result.structured_data || {}).replace(/'/g, "\\'").replace(/"/g, '&quot;');

  return `
    <div class="message message-ai">
      <div class="bubble">
        <div class="ai-response">
          <div class="response-header">
            <div class="response-type-icon analysis">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 3v18h18"/>
                <path d="M7 12l4-4 4 4 5-5"/>
              </svg>
            </div>
            <span class="response-type-label">Анализ</span>
          </div>
          <div class="response-body">
            <div class="response-result">${result.summary || 'Результат анализа'}</div>
            ${findingsList}
            ${result.explanation ? `<div class="response-explanation">${result.explanation}</div>` : ''}
            <div class="sheet-offer">
              <div>📊 ${result.rowCount || 0} строк — создать отдельный лист?</div>
              <div style="display: flex; gap: 8px;">
                <button onclick="createSheetFromOffer('${structuredDataJson}')">✓ Создать лист</button>
                <button onclick="this.closest('.sheet-offer').style.display='none'">✗ Не нужно</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== FILTER RESPONSE =====
function createFilterResponse(result) {
  return `
    <div class="message message-ai">
      <div class="bubble">
        <div class="ai-response">
          <div class="response-header">
            <div class="response-type-icon filter">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
              </svg>
            </div>
            <span class="response-type-label">Фильтр</span>
          </div>
          <div class="response-body">
            <div class="response-result">Найдено ${result.rows_count || 0} строк</div>
            ${result.filter_params ? `
              <div class="response-explanation">
                Фильтр: <strong>${result.filter_params.column}</strong> ${result.filter_params.operator} <strong>${result.filter_params.value}</strong>
              </div>
            ` : ''}
            ${result.created_sheet ? `
              <div class="response-success">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                  <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                <span>Таблица создана: "${result.created_sheet}"</span>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== TABLE RESPONSE =====
function createTableResponse(result) {
  const actualRowCount = result.rows_count || result.structured_data?.rows?.length || 0;

  return `
    <div class="message message-ai">
      <div class="bubble">
        <div class="ai-response">
          <div class="response-header">
            <div class="response-type-icon table">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="3" x2="9" y2="21"/>
              </svg>
            </div>
            <span class="response-type-label">Таблица</span>
          </div>
          <div class="response-body">
            <div class="response-success">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>Лист "${result.sheet_name || 'SheetGPT'}" создан (${actualRowCount} строк)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== HIGHLIGHT RESPONSE =====
function createHighlightResponse(result) {
  const rowList = (result.highlight_rows || result.rows || []).join(', ');
  
  return `
    <div class="message message-ai">
      <div class="bubble">
        <div class="ai-response">
          <div class="response-header">
            <div class="response-type-icon" style="background: rgba(245, 158, 11, 0.15); color: #F59E0B;">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <path d="M3 9h18"/>
                <rect x="3" y="9" width="18" height="6" fill="currentColor" opacity="0.3"/>
              </svg>
            </div>
            <span class="response-type-label">Выделение</span>
          </div>
          <div class="response-body">
            <div class="response-result">Выделено строк: ${result.highlighted_count || result.highlight_rows?.length || 0}</div>
            ${result.success !== false ? `
              <div class="response-success">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                  <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                <span>Строки ${rowList} выделены</span>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== MAIN RENDER FUNCTION =====
function renderAIResponse(result) {
  const loading = document.getElementById('loadingMessage');
  if (loading) loading.remove();

  const responseType = result.response_type || 'formula';
  let html = '';

  const userQuery = (window.lastUserQuery || '').toLowerCase();
  const wantsNewSheet = userQuery.includes('отдельн') || userQuery.includes('новом листе') ||
                       userQuery.includes('новый лист') || userQuery.includes('создай лист') ||
                       userQuery.includes('создай таблицу') || userQuery.includes('в листе') ||
                       userQuery.includes('на листе') || userQuery.includes('в таблиц');
  const rowCount = result.structured_data?.rows?.length || 0;

  let displayMode;
  if (wantsNewSheet) {
    displayMode = 'create_sheet';
  } else if (rowCount > 50) {
    displayMode = 'create_sheet';
  } else {
    displayMode = result.structured_data?.display_mode || 'sidebar_only';
  }

  if (result.highlight_rows && result.highlight_rows.length > 0) {
    html = createHighlightResponse(result);
  } else if (result.structured_data && wantsNewSheet) {
    html = createAnalysisResponse({
      ...result,
      summary: result.summary || `Создаю таблицу (${rowCount} строк)...`
    });
  } else if (result.structured_data) {
    if (rowCount > 20) {
      html = createAnalysisWithSheetOffer({
        ...result,
        summary: result.summary || `Найдено ${rowCount} записей`,
        rowCount: rowCount
      });
    } else {
      html = createAnalysisResponse({
        ...result,
        summary: result.summary || `Найдено ${rowCount} записей`
      });
    }
  } else {
    switch (responseType) {
      case 'formula':
        html = result.formula ? createFormulaResponse(result) : createAnalysisResponse(result);
        break;
      case 'analysis':
      case 'calculate':
        html = createAnalysisResponse(result);
        break;
      case 'filter':
      case 'filter_rows':
        html = createFilterResponse(result);
        break;
      case 'table':
      case 'generate':
      case 'structured_data':
        html = createTableResponse(result);
        break;
      case 'highlight':
        html = createHighlightResponse(result);
        break;
      default:
        html = createAnalysisResponse(result);
    }
  }

  const container = document.getElementById('chatContainer');
  container.insertAdjacentHTML('beforeend', html);
  container.scrollTop = container.scrollHeight;
}

// ===== UTILITIES =====
function copyFormula(formula) {
  const decoded = formula.replace(/&quot;/g, '"').replace(/&#39;/g, "'");
  navigator.clipboard.writeText(decoded).then(() => {
    const btn = event.target.closest('.copy-btn');
    if (btn) {
      const originalHTML = btn.innerHTML;
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
      setTimeout(() => { btn.innerHTML = originalHTML; }, 2000);
    }
  });
}

function createSheetFromOffer(structuredDataJson) {
  try {
    const decoded = structuredDataJson.replace(/&quot;/g, '"').replace(/&#39;/g, "'");
    const structuredData = JSON.parse(decoded);
    
    if (typeof google !== 'undefined' && google.script && google.script.run) {
      google.script.run
        .withSuccessHandler(function(result) {
          const container = document.getElementById('chatContainer');
          const successHtml = `
            <div class="message message-ai">
              <div class="bubble">
                <div class="content-box success">
                  ✅ ${result.message || 'Таблица создана успешно'}
                </div>
              </div>
            </div>
          `;
          container.insertAdjacentHTML('beforeend', successHtml);
          container.scrollTop = container.scrollHeight;
        })
        .withFailureHandler(function(error) {
          alert('Ошибка создания таблицы: ' + error.message);
        })
        .createTableAndChart(structuredData);
    }
  } catch (e) {
    alert('Ошибка обработки данных');
  }
}

console.log('[ResponseTemplates] Loaded');
