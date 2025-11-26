/**
 * SheetGPT - Шаблоны для отображения AI ответов
 * Используй эти функции в sidebar.js для рендеринга ответов
 */

// ===== ШАБЛОН: Анимация загрузки =====
function createLoadingMessage() {
  return `
    <div class="loading-message" id="loadingMessage">
      <div class="loading-bubble">
        <div class="loading-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
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

// ===== ШАБЛОН: Ответ с формулой =====
function createFormulaResponse(result) {
  const formulaEscaped = (result.formula || '').replace(/'/g, "\\'");
  return `
    <div class="message ai">
      <div class="message-bubble">
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

// ===== ШАБЛОН: Ответ с анализом (calculate_count и т.д.) =====
function createAnalysisResponse(result) {
  const findings = result.key_findings || result.findings || [];
  const findingsList = findings.length > 0
    ? `<ul class="findings-list">${findings.map(f => `<li>${f}</li>`).join('')}</ul>`
    : '';

  return `
    <div class="message ai">
      <div class="message-bubble">
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
            ${result.value !== undefined ? `
              <div class="result-value">
                <span>${result.value}</span>
              </div>
            ` : ''}
            ${findingsList}
            ${result.explanation ? `<div class="response-explanation">${result.explanation}</div>` : ''}
            ${result.methodology ? `<div class="response-explanation" style="margin-top: 8px; font-size: 12px; opacity: 0.8;">${result.methodology}</div>` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== ШАБЛОН: Ответ с фильтрацией строк =====
function createFilterResponse(result) {
  return `
    <div class="message ai">
      <div class="message-bubble">
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

// ===== ШАБЛОН: Ответ с созданием таблицы (с подтверждением!) =====
function createTableResponse(result) {
  // Если таблица ещё НЕ создана - показываем превью и кнопку подтверждения
  if (!result.created && result.preview) {
    return `
      <div class="message ai">
        <div class="message-bubble">
          <div class="ai-response">
            <div class="response-header">
              <div class="response-type-icon table">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="18" height="18" rx="2"/>
                  <line x1="3" y1="9" x2="21" y2="9"/>
                  <line x1="3" y1="15" x2="21" y2="15"/>
                  <line x1="9" y1="3" x2="9" y2="21"/>
                  <line x1="15" y1="3" x2="15" y2="21"/>
                </svg>
              </div>
              <span class="response-type-label">Новая таблица</span>
            </div>
            <div class="response-body">
              <div class="response-result">Готова таблица: ${result.rows_count || 0} строк</div>
              <div class="response-explanation">${result.description || ''}</div>

              <div class="response-actions">
                <button class="response-btn primary" onclick="confirmCreateTable()">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  Создать лист
                </button>
                <button class="response-btn secondary" onclick="cancelAction()">
                  Отмена
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // Если таблица УЖЕ создана
  return `
    <div class="message ai">
      <div class="message-bubble">
        <div class="ai-response">
          <div class="response-header">
            <div class="response-type-icon table">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="3" x2="9" y2="21"/>
              </svg>
            </div>
            <span class="response-type-label">Таблица создана</span>
          </div>
          <div class="response-body">
            <div class="response-success">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>Лист "${result.sheet_name || 'SheetGPT'}" (${result.rows_count || 0} строк)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== ШАБЛОН: Ответ с подсветкой строк =====
function createHighlightResponse(result) {
  return `
    <div class="message ai">
      <div class="message-bubble">
        <div class="ai-response">
          <div class="response-header">
            <div class="response-type-icon" style="background: rgba(245, 158, 11, 0.15); color: #F59E0B;">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
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
                <span>Строки ${(result.highlight_rows || result.rows || []).join(', ')} выделены</span>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ===== ГЛАВНАЯ ФУНКЦИЯ: выбор шаблона по типу ответа =====
function renderAIResponse(result) {
  // Удаляем loading
  const loading = document.getElementById('loadingMessage');
  if (loading) loading.remove();

  // Определяем тип ответа
  const responseType = result.response_type || 'formula';

  let html = '';

  // Проверяем есть ли highlight_rows
  if (result.highlight_rows && result.highlight_rows.length > 0) {
    html = createHighlightResponse(result);
  } else if (result.structured_data) {
    html = createTableResponse({...result, ...result.structured_data});
  } else {
    switch (responseType) {
      case 'formula':
        if (result.formula) {
          html = createFormulaResponse(result);
        } else {
          html = createAnalysisResponse(result);
        }
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

  // Добавляем в чат
  const container = document.getElementById('chatContainer');
  container.insertAdjacentHTML('beforeend', html);

  // Скролл вниз
  container.scrollTop = container.scrollHeight;
}

// ===== УТИЛИТЫ =====
function copyFormula(formula) {
  navigator.clipboard.writeText(formula).then(() => {
    // Показать feedback
    const btn = event.target.closest('.copy-btn');
    if (btn) {
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
      setTimeout(() => {
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
      }, 2000);
    }
  });
}

// Export для использования в sidebar.js
if (typeof module !== 'undefined') {
  module.exports = {
    createLoadingMessage,
    createFormulaResponse,
    createAnalysisResponse,
    createFilterResponse,
    createTableResponse,
    createHighlightResponse,
    renderAIResponse
  };
}
