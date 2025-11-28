/**
 * SheetGPT - Response Templates
 * Чистые, минималистичные шаблоны для чата
 */

console.log('[ResponseTemplates] Loading...');

// ===== LOADING =====
function createLoadingMessage() {
  return `
    <div class="message message-ai" id="loadingMessage">
      <div class="ai-bubble">
        <div class="typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  `;
}

// ===== USER MESSAGE =====
function createUserMessage(text) {
  return `
    <div class="message message-user">
      <div class="user-bubble">${escapeHtml(text)}</div>
    </div>
  `;
}

// ===== AI MESSAGE — простой текст =====
function createAIMessage(text) {
  return `
    <div class="message message-ai">
      <div class="ai-bubble">${text}</div>
    </div>
  `;
}

// ===== FORMULA RESPONSE =====
function createFormulaResponse(result) {
  const formula = result.formula || '';
  const explanation = result.explanation || '';
  
  return `
    <div class="message message-ai">
      <div class="ai-bubble">
        <div class="formula-box">
          <code>${escapeHtml(formula)}</code>
          <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(formula).replace(/'/g, "\\'")}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
        </div>
        ${explanation ? `<p class="explanation">${explanation}</p>` : ''}
      </div>
    </div>
  `;
}

// ===== ANALYSIS RESPONSE =====
function createAnalysisResponse(result) {
  const summary = result.summary || result.explanation || '';
  const value = result.value;
  const findings = result.key_findings || [];
  
  let html = `<div class="message message-ai"><div class="ai-bubble">`;
  
  // Если есть конкретное значение — показываем его крупно
  if (value !== undefined && value !== null) {
    html += `<div class="result-highlight">${value}</div>`;
  }
  
  // Основной текст
  if (summary) {
    html += `<p>${summary}</p>`;
  }
  
  // Ключевые находки
  if (findings.length > 0) {
    html += `<ul class="findings">`;
    findings.forEach(f => {
      html += `<li>${f}</li>`;
    });
    html += `</ul>`;
  }
  
  html += `</div></div>`;
  return html;
}

// ===== HIGHLIGHT RESPONSE =====
function createHighlightResponse(result) {
  const count = result.highlighted_count || result.highlight_rows?.length || 0;
  const rows = (result.highlight_rows || []).slice(0, 10).join(', ');
  const hasMore = (result.highlight_rows || []).length > 10;
  
  return `
    <div class="message message-ai">
      <div class="ai-bubble">
        <div class="result-highlight">${count}</div>
        <p>строк выделено${rows ? `: ${rows}${hasMore ? '...' : ''}` : ''}</p>
      </div>
    </div>
  `;
}

// ===== TABLE/DATA RESPONSE =====
function createTableResponse(result) {
  const rowCount = result.rows_count || result.structured_data?.rows?.length || 0;
  const sheetName = result.sheet_name || 'SheetGPT';
  
  return `
    <div class="message message-ai">
      <div class="ai-bubble">
        <div class="success-msg">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          Таблица «${escapeHtml(sheetName)}» создана — ${rowCount} строк
        </div>
      </div>
    </div>
  `;
}

// ===== MAIN RENDER FUNCTION =====
function renderAIResponse(result) {
  // Удаляем loading
  const loading = document.getElementById('loadingMessage');
  if (loading) loading.remove();

  const container = document.getElementById('chatContainer');
  let html = '';

  // Определяем тип ответа
  const responseType = result.response_type || 'analysis';

  // Подсветка строк
  if (result.highlight_rows && result.highlight_rows.length > 0) {
    html = createHighlightResponse(result);
  }
  // Формула
  else if (result.formula) {
    html = createFormulaResponse(result);
  }
  // Таблица создана
  else if (result.sheet_name || (result.structured_data && result.created)) {
    html = createTableResponse(result);
  }
  // Обычный анализ
  else {
    html = createAnalysisResponse(result);
  }

  container.insertAdjacentHTML('beforeend', html);
  container.scrollTop = container.scrollHeight;
}

// ===== UTILITIES =====
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    const btn = event.target.closest('.copy-btn');
    if (btn) {
      btn.classList.add('copied');
      setTimeout(() => btn.classList.remove('copied'), 1500);
    }
  });
}

console.log('[ResponseTemplates] Loaded');
