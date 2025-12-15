/**
 * SheetGPT Sidebar - Main Application Script
 * Handles authentication, chat, and all UI interactions
 */

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
  API_URL: 'https://sheetgpt-production.up.railway.app',
  MAX_RETRIES: 3,
  RETRY_DELAYS: [1000, 3000, 10000],
  MAX_HISTORY_ITEMS: 20,
  FREE_DAILY_LIMIT: 10,
  PRO_DAILY_LIMIT: 1000
};

// ============================================
// STATE MANAGEMENT
// ============================================
const state = {
  isAuthenticated: false,
  user: null,
  licenseKey: null,
  theme: 'dark',
  customContext: '',
  chatHistory: [],
  usageCount: 0,
  usageLimit: CONFIG.FREE_DAILY_LIMIT,
  isLoading: false,
  premiumUntil: null  // v9.1.0: Premium subscription expiration date
};

// ============================================
// UNDO SYSTEM - Save state before changes
// ============================================
let undoSnapshot = null;  // Stores sheet data before last change
let undoActionName = '';  // Description of what was done

/**
 * Save current sheet state before making changes
 * @param {string} actionName - Description of the action being performed
 */
async function saveSheetSnapshot(actionName, extraData = null) {
  try {
    console.log('[Sidebar] 📸 Saving snapshot before:', actionName);
    const response = await sendToContentScript('GET_SHEET_DATA_FOR_UNDO', {});
    if (response && response.success && response.data) {
      undoSnapshot = response.data;
      // Save extra data (e.g., highlighted rows for undo)
      if (extraData) {
        undoSnapshot.extraData = extraData;
      }
      undoActionName = actionName;
      // Show undo button
      const undoBtn = document.getElementById('undoBtn');
      if (undoBtn) {
        undoBtn.classList.add('visible');
        undoBtn.title = `Отменить: ${actionName}`;
      }
      console.log('[Sidebar] ✅ Snapshot saved:', undoSnapshot.values?.length, 'rows');
    }
  } catch (error) {
    console.error('[Sidebar] ❌ Failed to save snapshot:', error);
  }
}

/**
 * Undo last action by restoring saved snapshot
 */
async function undoLastAction() {
  if (!undoSnapshot) {
    console.log('[Sidebar] ⚠️ Nothing to undo');
    return;
  }

  try {
    console.log('[Sidebar] ↩️ Restoring snapshot...');

    let response;

    // For highlight actions, just clear the colors instead of restoring all data
    if (undoSnapshot.extraData?.highlightedRows) {
      console.log('[Sidebar] ↩️ Clearing highlight colors from rows:', undoSnapshot.extraData.highlightedRows);
      response = await sendToContentScript('CLEAR_ROW_COLORS', {
        rows: undoSnapshot.extraData.highlightedRows,
        sheetName: undoSnapshot.sheetName
      });
    } else if (undoSnapshot.extraData?.addedColumn) {
      // For add_formula actions, delete the added column
      console.log('[Sidebar] ↩️ Deleting added column:', undoSnapshot.extraData.addedColumn);
      response = await sendToContentScript('DELETE_COLUMN', {
        column: undoSnapshot.extraData.addedColumn,
        sheetName: undoSnapshot.sheetName
      });
    } else {
      // For other actions, restore the full data
      response = await sendToContentScript('RESTORE_SHEET_DATA', {
        data: undoSnapshot
      });
    }

    if (response && response.success) {
      addAIMessage({
        type: 'analysis',
        text: `Действие "${undoActionName}" отменено`
      });
      console.log('[Sidebar] ✅ Undo successful');
    } else {
      addAIMessage({
        type: 'error',
        text: 'Не удалось отменить действие: ' + (response?.message || 'Неизвестная ошибка')
      });
    }

    // Clear snapshot and hide button
    undoSnapshot = null;
    undoActionName = '';
    const undoBtn = document.getElementById('undoBtn');
    if (undoBtn) {
      undoBtn.classList.remove('visible');
    }
  } catch (error) {
    console.error('[Sidebar] ❌ Undo failed:', error);
    addAIMessage({
      type: 'error',
      text: 'Ошибка отмены: ' + error.message
    });
  }
}

// ============================================
// TEXT FORMATTING UTILITIES (v9.1.0)
// ============================================

function cleanResponseText(text, preserveNewlines = false) {
  if (!text) return '';
  // Remove emoji
  let cleaned = text.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]/gu, '');
  // Remove markdown bold/italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '$1');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '$1');
  cleaned = cleaned.replace(/__([^_]+)__/g, '$1');
  cleaned = cleaned.replace(/_([^_]+)_/g, '$1');
  // Clean whitespace (v9.2.2: optionally preserve newlines)
  if (preserveNewlines) {
    cleaned = cleaned.replace(/[^\S\n]+/g, ' ');
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  } else {
    cleaned = cleaned.replace(/\s+/g, ' ');
  }
  return cleaned.trim();
}

// ============================================
// CROSS-SHEET VLOOKUP SUPPORT (v9.2.0)
// ============================================

function detectCrossSheetQuery(query) {
  console.log('[Sidebar] 🔍 detectCrossSheetQuery:', query);
  const lowerQuery = query.toLowerCase();
  // v10.0.8: Simplified patterns - support all common quote types
  // All quotes (open/close): " ' « » " " ' '
  const anyQuote = '["\'\u00AB\u00BB\u201C\u201D\u2018\u2019]';
  const notQuote = '[^"\'\u00AB\u00BB\u201C\u201D\u2018\u2019]';

  const patterns = [
    // Pattern 1: из/с/from листа "name" (with quotes)
    new RegExp('(?:из|с|from)\\s+(?:листа|sheet|таблицы)\\s+' + anyQuote + '(' + notQuote + '+)' + anyQuote, 'i'),
    // Pattern 2: из/с/from листа name (without quotes, single word)
    /(?:из|с|from)\s+(?:листа|sheet|таблицы)\s+([^\s,]+)/i,
    // Pattern 3: впр/vlookup из "name"
    new RegExp('(?:впр|vlookup)\\s+(?:из|from|с)\\s+' + anyQuote + '(' + notQuote + '+)' + anyQuote, 'i'),
    /(?:впр|vlookup)\s+(?:из|from|с)\s+([^\s,]+)/i,
    // Pattern 4: по/в/in листе "name"
    new RegExp('(?:по|в|in)\\s+(?:листе|листу|sheet)\\s+' + anyQuote + '(' + notQuote + '+)' + anyQuote, 'i'),
    /(?:по|в|in)\s+(?:листе|листу|sheet)\s+([^\s,]+)/i,
    // Pattern 5: подтяни из листа "name"
    new RegExp('подтян[иьу]\\s+(?:из|с)\\s+(?:листа|sheet)\\s+' + anyQuote + '(' + notQuote + '+)' + anyQuote, 'i'),
  ];
  for (let i = 0; i < patterns.length; i++) {
    const pattern = patterns[i];
    const match = query.match(pattern);
    if (match && match[1]) {
      console.log('[Sidebar] ✅ Pattern matched! Sheet name:', match[1].trim());
      return { sheetName: match[1].trim() };
    }
  }
  // Fallback: check for reference keywords in query
  const refKeywords = ['прайс', 'справочник', 'каталог', 'price', 'catalog', 'reference'];
  for (const keyword of refKeywords) {
    if (lowerQuery.includes(keyword)) {
      console.log('[Sidebar] ✅ Keyword matched:', keyword);
      return { sheetName: keyword };
    }
  }
  console.log('[Sidebar] ❌ No cross-sheet pattern detected');
  return null;
}

async function getReferenceSheetData(sheetNameHint) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      { action: 'GET_REFERENCE_SHEET_DATA', sheetNameHint: sheetNameHint },
      (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else if (response && response.success && response.result) {
          console.log('[Sidebar] 📦 getReferenceSheetData result:', response.result);
          resolve({ name: response.result.sheetName, headers: response.result.headers, data: response.result.data });
        } else {
          console.error('[Sidebar] getReferenceSheetData failed:', response);
          reject(new Error(response?.error || 'Failed to get reference sheet'));
        }
      }
    );
  });
}




// v9.3.0: Умный парсер для структурированных ответов
function formatAnalysisResponse(text) {
  if (!text) return '';

  // Очистка текста от эмодзи и лишних символов
  let cleaned = text
    .replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]/gu, '')
    .replace(/≡/g, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .trim();

  const lines = cleaned.split(/\n/).map(l => l.trim()).filter(l => l);
  let html = '';
  let dataRows = [];
  let headerText = '';
  let conclusionText = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^(АНАЛИЗ|Лидер|Вывод|Итог|Рейтинг):?$/i.test(line)) continue;

    if (i === 0 || /^(Самый|Лидер|Победитель|Лучший|Худший|Топ)/i.test(line)) {
      if (line.includes('—') || line.includes(':') || line.includes('-')) {
        headerText = line;
      } else if (!headerText) {
        headerText = line;
      }
      continue;
    }

    // v11.9: Fix rankMatch to not split on hyphens inside words like "Веб-камера"
    // Match: "1. Label: value" or "1. Label — value" (use colon or em-dash as separator, not hyphen)
    const rankMatch = line.match(/^(\d+)[.\)]\s*(.+?):\s*(.+)$/);
    if (rankMatch) {
      dataRows.push({ label: rankMatch[2].trim(), value: rankMatch[3].trim() });
      continue;
    }

    // v11.8: Fix regex to NOT allow colons in value - forces greedy backtracking
    // This ensures "Веб: камера: 49.0 шт." parses as label="Веб: камера", value="49.0 шт."
    const metricMatch = line.match(/^(.+):\s*(\d[\d\s,.]*(?:руб|₽|%|шт)?\.?|[^:]+)$/i);
    if (metricMatch) {
      let label = metricMatch[1].trim();
      const value = metricMatch[2].trim();
      // Clean up any extra colons in label (from malformed data)
      label = label.replace(/:\s*$/, '').trim();
      if (value && !/^(Рейтинг|Вывод|Итог|Анализ)$/i.test(label)) {
        // Fix concatenated words like "Ивановчек" -> "ср. чек"
        const fixedValue = value.replace(/(\d)чек/gi, '$1 чек').replace(/срчек/gi, 'ср. чек').replace(/(\d)руб/gi, '$1 руб');
        dataRows.push({ label, value: fixedValue });
      }
      continue;
    }

    if (/^(Вывод|Итог|Заключение)[:\s]/i.test(line)) {
      const match = line.match(/^(?:Вывод|Итог|Заключение)[:\s]*(.+)$/i);
      if (match && match[1]) conclusionText = match[1].trim();
      continue;
    }

    if (line.startsWith('•') || line.startsWith('·') || line.startsWith('-')) {
      const cleanLine = line.replace(/^[•·\-]\s*/, '').trim();
      // v11.7: Use greedy match like main metric regex to handle "Веб: камера: 49.0 шт." correctly
      // Match everything up to the LAST colon that's followed by a number/value
      const bulletMetric = cleanLine.match(/^(.+):\s*(\d[\d\s,.]*(?:руб|₽|%|шт)?\.?|[^:]+)$/i);
      if (bulletMetric) {
        dataRows.push({ label: bulletMetric[1].trim(), value: bulletMetric[2].trim() });
      } else if (cleanLine.length > 3) {
        dataRows.push({ label: cleanLine, value: '' });
      }
      continue;
    }
  }

  // Render HTML
  if (headerText) {
    html += '<div style="font-weight: 600; font-size: 14px; margin-bottom: 12px;">' + escapeHtml(headerText) + '</div>';
  }

  if (dataRows.length > 0) {
    html += '<div class="data-block">';
    for (const row of dataRows) {
      if (row.value) {
        html += '<div class="data-row"><span class="data-label">' + escapeHtml(row.label) + '</span><span class="data-value">' + escapeHtml(row.value) + '</span></div>';
      } else {
        html += '<div style="padding: 4px 0; font-size: 13px;">' + escapeHtml(row.label) + '</div>';
      }
    }
    html += '</div>';
  }

  if (conclusionText) {
    html += '<div style="margin-top: 12px; padding: 8px 12px; background: var(--accent-subtle); border-left: 3px solid var(--accent); border-radius: 0 8px 8px 0; font-size: 13px;">' + escapeHtml(conclusionText) + '</div>';
  }

  if (!html) {
    html = '<p>' + escapeHtml(cleaned) + '</p>';
  }

  return html;
}

function parseResponseContent(text) {
  if (!text) return { paragraphs: [], metrics: [], items: [] };
  // v9.2.2: Preserve newlines for better structure parsing
  const cleaned = cleanResponseText(text, true);
  const result = { paragraphs: [], metrics: [], items: [] };

  // v9.2.2: Split by newlines first, then by bullet points
  let lines = cleaned.split(/\n/).filter(l => l.trim());
  if (lines.length <= 1) {
    lines = cleaned.split(/[•·]\s+/).filter(l => l.trim());
  }

  for (const line of lines) {
    const trimmed = line.trim();
    // Skip section headers (lines ending with : alone)
    if (trimmed.endsWith(':') && trimmed.length < 50) {
      result.items.push(trimmed);
      continue;
    }
    // Check if numeric metric (contains : and number)
    const numericMatch = trimmed.match(/^([^:]+):\s*([0-9.,\s]+(?:руб|₽|%|шт)?\.?)\s*(?:\(([^)]+)\))?/i);
    if (numericMatch) {
      result.metrics.push({
        label: numericMatch[1].trim(),
        value: numericMatch[2].trim(),
        subtext: numericMatch[3] ? numericMatch[3].trim() : null
      });
    }
    // v9.2.2: Also match text key-value pairs like "Лидер: Иванов"
    else {
      const textMatch = trimmed.match(/^([^:]{2,25}):\s+(.+)$/);
      if (textMatch && !trimmed.includes('http')) {
        result.metrics.push({
          label: textMatch[1].trim(),
          value: textMatch[2].trim(),
          subtext: null
        });
      } else if (trimmed.length > 0) {
        result.items.push(trimmed);
      }
    }
  }

  // If nothing found, split into paragraphs
  if (result.metrics.length === 0 && result.items.length === 0) {
    const sentences = cleaned.split(/(?<=[.!?])\s+/);
    let currentParagraph = '';
    for (const sentence of sentences) {
      currentParagraph += sentence + ' ';
      if (currentParagraph.split(/[.!?]/).length > 3) {
        result.paragraphs.push(currentParagraph.trim());
        currentParagraph = '';
      }
    }
    if (currentParagraph.trim()) {
      result.paragraphs.push(currentParagraph.trim());
    }
  }

  return result;
}



// ============================================
// DOM ELEMENTS
// ============================================
// Elements will be initialized after DOM is ready
let elements = {};

function initElements() {
  elements = {
    // Screens
    loginScreen: document.getElementById('loginScreen'),
    mainApp: document.getElementById('mainApp'),
    
    // Login
    licenseInput: document.getElementById('licenseInput'),
    loginBtn: document.getElementById('loginBtn'),
    loginError: document.getElementById('loginError'),
    
    // User Info
    userAvatar: document.getElementById('userAvatar'),
    userName: document.getElementById('userName'),
    planBadge: document.getElementById('planBadge'),
    usageCount: document.getElementById('usageCount'),
    usageLimit: document.getElementById('usageLimit'),
    usageBarFill: document.getElementById('usageBarFill'),
    usageContainer: document.getElementById('usageContainer'),
    
    // Chat
    chatContainer: document.getElementById('chatContainer'),
    emptyState: document.getElementById('emptyState'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    
    // Header
    themeToggle: document.getElementById('themeToggle'),
    historyBtn: document.getElementById('historyBtn'),
    settingsBtn: document.getElementById('settingsBtn'),
    historyDropdown: document.getElementById('historyDropdown'),
    historyList: document.getElementById('historyList'),
    
    // Settings Modal
    settingsModal: document.getElementById('settingsModal'),
    closeSettingsBtn: document.getElementById('closeSettingsBtn'),
    cancelSettingsBtn: document.getElementById('cancelSettingsBtn'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
    settingsAvatar: document.getElementById('settingsAvatar'),
    settingsUserName: document.getElementById('settingsUserName'),
    settingsPlan: document.getElementById('settingsPlan'),
    settingsLicenseKey: document.getElementById('settingsLicenseKey'),
    customContextInput: document.getElementById('customContextInput'),
    userNameInput: document.getElementById('userNameInput'),
    charCount: document.getElementById('charCount'),
    logoutBtn: document.getElementById('logoutBtn'),

    // Personalization Modal (Design System v1.2)
    personalizeBtn: document.getElementById('personalizeBtn'),
    personalizationModal: document.getElementById('personalizationModal'),
    closePersonalizationBtn: document.getElementById('closePersonalizationBtn'),
    cancelPersonalizationBtn: document.getElementById('cancelPersonalizationBtn'),
    savePersonalizationBtn: document.getElementById('savePersonalizationBtn'),
    personalizationContextInput: document.getElementById('personalizationContextInput')
  };
  
  // Debug: log which elements are null
  const nullElements = Object.entries(elements).filter(([k, v]) => v === null).map(([k]) => k);
  if (nullElements.length > 0) {
    console.warn('[Sidebar] Missing DOM elements:', nullElements);
  }
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', init);

function init() {
  initElements();
  loadState();
  setupEventListeners();
  applyTheme();
  checkAuthentication();
  // v8.0.1: Sync customContext with chrome.storage.local on startup
  if (state.customContext) {
    sendToContentScript('SAVE_CUSTOM_CONTEXT', { context: state.customContext });
  }
}

function loadState() {
  try {
    const savedState = localStorage.getItem('sheetgpt_state');
    if (savedState) {
      const parsed = JSON.parse(savedState);
      // v10.1: Don't load usage from localStorage - always get from server
      const { usageCount, usageLimit, ...safeState } = parsed;
      Object.assign(state, safeState);
      state.usageCount = 0;  // Will be set by checkAuthentication()
      state.usageLimit = 10; // Default, will be set by checkAuthentication()
      console.log('[LoadState] Ignoring cached usage, will sync from server');
    }
    
    // Load chat history separately
    const savedHistory = localStorage.getItem('sheetgpt_history');
    if (savedHistory) {
      state.chatHistory = JSON.parse(savedHistory);
    }
    
    // v10.0: Server is source of truth for usage
    console.log('[LoadState] Loaded usageCount:', state.usageCount);
  } catch (e) {
    console.error('Error loading state:', e);
  }
}

function saveState() {
  try {
    const stateToSave = {
      isAuthenticated: state.isAuthenticated,
      user: state.user,
      licenseKey: state.licenseKey,
      theme: state.theme,
      customContext: state.customContext
      // v10.1: usageCount/usageLimit NOT saved - always from server
    };
    localStorage.setItem('sheetgpt_state', JSON.stringify(stateToSave));
    localStorage.setItem('sheetgpt_history', JSON.stringify(state.chatHistory.slice(0, CONFIG.MAX_HISTORY_ITEMS)));
  } catch (e) {
    console.error('Error saving state:', e);
  }
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
  // Login
  elements.loginBtn.addEventListener('click', handleLogin);
  elements.licenseInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleLogin();
  });
  elements.licenseInput.addEventListener('input', formatLicenseKey);
  
  // Theme toggle
  elements.themeToggle.addEventListener('click', toggleTheme);

  // Undo button
  const undoBtn = document.getElementById('undoBtn');
  if (undoBtn) {
    undoBtn.addEventListener('click', undoLastAction);
  }

  // History dropdown
  elements.historyBtn.addEventListener('click', toggleHistoryDropdown);
  document.addEventListener('click', (e) => {
    if (!elements.historyBtn.contains(e.target) && !elements.historyDropdown.contains(e.target)) {
      elements.historyDropdown.classList.remove('show');
    }
  });
  
  // Settings
  elements.settingsBtn.addEventListener('click', openSettings);
  elements.closeSettingsBtn.addEventListener('click', closeSettings);
  elements.cancelSettingsBtn.addEventListener('click', closeSettings);
  elements.saveSettingsBtn.addEventListener('click', saveSettings);
  elements.settingsModal.addEventListener('click', (e) => {
    if (e.target === elements.settingsModal) closeSettings();
  });
  
  // Logout
  elements.logoutBtn.addEventListener('click', handleLogout);
  
  // Character counter
  elements.customContextInput.addEventListener('input', updateCharCounter);
  
  // Message input
  elements.messageInput.addEventListener('input', handleInputChange);
  elements.messageInput.addEventListener('keydown', handleInputKeydown);
  elements.sendBtn.addEventListener('click', sendMessage);
  
  // Quick actions
  document.querySelectorAll('.action-card').forEach(card => {
    card.addEventListener('click', () => {
      const query = card.dataset.query;
      if (query) {
        elements.messageInput.value = query;
        handleInputChange();
        sendMessage();
      }
    });
  });

  // Event delegation for action buttons (CSP-compliant)
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    
    const action = btn.dataset.action;
    console.log('[Sidebar] Action button clicked:', action);
    
    switch (action) {
      case 'insertFormula':
        insertFormula(btn.dataset.formula);
        break;
      case 'copyToClipboard':
        copyToClipboard(btn.dataset.text);
        break;
      case 'insertTable':
        insertTable();
        break;
      case 'insertPivotTable':
        insertPivotTable();
        break;
      case 'applySplitData':
        applySplitData();
        break;
      case 'insertCleanedData':
        insertCleanedData();
        break;
      case 'overwriteWithCleanedData':
        overwriteWithCleanedData();
        break;
      case 'insertFilteredData':
        insertFilteredData();
        break;
      case 'highlightFilteredRows':
        highlightFilteredRows();
        break;
    }
  });

  // Personalization Modal (Design System v1.2)
  if (elements.personalizeBtn) {
    elements.personalizeBtn.addEventListener('click', openPersonalization);
  }
  if (elements.closePersonalizationBtn) {
    elements.closePersonalizationBtn.addEventListener('click', closePersonalization);
  }
  if (elements.cancelPersonalizationBtn) {
    elements.cancelPersonalizationBtn.addEventListener('click', closePersonalization);
  }
  if (elements.savePersonalizationBtn) {
    elements.savePersonalizationBtn.addEventListener('click', savePersonalization);
  }
  if (elements.personalizationModal) {
    elements.personalizationModal.addEventListener('click', (e) => {
      if (e.target === elements.personalizationModal) closePersonalization();
    });
  }

  // Role preset cards (Design System v1.2)
  document.querySelectorAll('.preset-card').forEach(preset => {
    preset.addEventListener('click', () => {
      // Remove selected from all
      document.querySelectorAll('.preset-card').forEach(p => p.classList.remove('selected'));
      // Add selected to clicked
      preset.classList.add('selected');
      // Set context based on preset type
      const presetType = preset.dataset.preset;
      const context = getPresetContext(presetType);
      if (context && elements.personalizationContextInput) {
        elements.personalizationContextInput.value = context;
      }
    });
  });
}

// Get context text for preset role
function getPresetContext(presetType) {
  const presets = {
    analyst: 'Я аналитик данных. Мне важны KPI, метрики производительности, тренды и визуализация данных. Помогай с анализом данных, построением отчётов и выявлением закономерностей.',
    accountant: 'Я бухгалтер. Работаю с финансовой отчётностью, расчётами налогов, сверками и учётом. Помогай с формулами для финансовых расчётов и проверки данных.',
    marketer: 'Я маркетолог. Работаю с метриками ROI, конверсий, воронок продаж и эффективности рекламных кампаний. Помогай анализировать маркетинговые данные.',
    sales: 'Я менеджер по продажам. Работаю с CRM-данными, сделками, планами продаж и клиентской базой. Помогай с анализом продаж и прогнозированием.',
    hr: 'Я HR-специалист. Работаю с кадровыми данными, зарплатами, отпусками и учётом сотрудников. Помогай с расчётами и анализом HR-метрик.',
    logistics: 'Я логист. Работаю с данными склада, доставки, маршрутов и запасов. Помогай с анализом логистических операций и оптимизацией.'
  };
  return presets[presetType] || '';
}

// ============================================
// AUTHENTICATION
// ============================================
async function checkAuthentication() {
  if (state.isAuthenticated && state.licenseKey) {
    // Re-validate license with server
    try {
      const response = await fetch(`${CONFIG.API_URL}/api/v1/telegram/license/validate/${encodeURIComponent(state.licenseKey)}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success || data.valid || data.status === 'active') {
          // Update user info from server
          state.user = {
            name: data.user_name || data.userName || data.telegram_username || state.user?.name || 'Пользователь',
            plan: data.subscription_tier || data.plan || data.subscription_type || state.user?.plan || 'free',
            email: data.email || state.user?.email || ''
          };
          // v9.1.0: Check premium expiration
          let isPremium = ['premium', 'pro', 'unlimited'].includes(data.subscription_tier) ||
                          ['premium', 'pro', 'unlimited'].includes(data.plan);

          // Check if premium has expired
          if (isPremium && data.premium_until) {
            const premiumUntil = new Date(data.premium_until);
            if (new Date() > premiumUntil) {
              console.log('[Sidebar] Premium subscription expired');
              isPremium = false;
            }
            state.premiumUntil = data.premium_until;
          }

          // Sync usage from server
          console.log('[Auth] ====== SERVER USAGE SYNC ======');
          console.log('[Auth] Server response:', JSON.stringify(data));
          console.log('[Auth] queries_used_today from server:', data.queries_used_today);
          console.log('[Auth] queries_limit from server:', data.queries_limit);
          if (data.queries_used_today !== undefined) {
            state.usageCount = data.queries_used_today;
            console.log('[Auth] Updated usageCount to:', state.usageCount);
          }
          if (data.queries_limit !== undefined && data.queries_limit > 0) {
            state.usageLimit = data.queries_limit;
          } else {
            state.usageLimit = isPremium ? CONFIG.PRO_DAILY_LIMIT : CONFIG.FREE_DAILY_LIMIT;
          }
          saveState();
          showMainApp();
          updateUserUI();
          renderHistory();
          return;
        }
      }
      // License invalid - logout
      console.log('[Auth] License no longer valid, logging out');
      handleLogout();
    } catch (error) {
      // Network error - use cached state
      console.log('[Auth] Network error, using cached state');
      showMainApp();
      updateUserUI();
      renderHistory();
    }
  } else {
    showLoginScreen();
  }
}

function showLoginScreen() {
  elements.loginScreen.classList.remove('hidden');
  elements.mainApp.classList.remove('active');
}

function showMainApp() {
  elements.loginScreen.classList.add('hidden');
  elements.mainApp.classList.add('active');
}

async function handleLogin() {
  const licenseKey = elements.licenseInput.value.trim().toUpperCase();

  // Support both 3-group and 4-group license formats
  const isValid3Group = /^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/i.test(licenseKey);
  const isValid4Group = /^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/i.test(licenseKey);

  if (!licenseKey || (!isValid3Group && !isValid4Group)) {
    showLoginError('Введите корректный ключ (формат: XXXX-XXXX-XXXX)');
    return;
  }

  elements.loginBtn.disabled = true;
  elements.loginBtn.textContent = 'Проверка...';

  try {
    // Validate license key with correct API endpoint
    const response = await fetch(`${CONFIG.API_URL}/api/v1/telegram/license/validate/${encodeURIComponent(licenseKey)}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });

    console.log('[Login] API response status:', response.status);

    if (response.ok) {
      const data = await response.json();
      console.log('[Login] API response data:', data);

      // Check if license is valid (API returns success: true)
      if (data.success || data.valid || data.status === 'active') {
        state.isAuthenticated = true;
        state.licenseKey = licenseKey;
        state.user = {
          name: data.user_name || data.userName || data.telegram_username || 'Пользователь',
          plan: data.subscription_tier || data.plan || data.subscription_type || 'free',
          email: data.email || ''
        };
        // v9.1.0: Check for premium/pro/unlimited subscription with expiration
        let isPremium = ['premium', 'pro', 'unlimited'].includes(data.subscription_tier) ||
                        ['premium', 'pro', 'unlimited'].includes(data.plan) ||
                        ['premium', 'pro', 'unlimited'].includes(data.subscription_type);

        // Check premium expiration
        if (isPremium && data.premium_until) {
          const premiumUntil = new Date(data.premium_until);
          if (new Date() > premiumUntil) {
            console.log('[Sidebar] Premium subscription expired');
            isPremium = false;
          }
          state.premiumUntil = data.premium_until;
        }

        // Sync usage from server
        if (data.queries_used_today !== undefined) {
          state.usageCount = data.queries_used_today;
        }
        if (data.queries_limit !== undefined && data.queries_limit > 0) {
          state.usageLimit = data.queries_limit;
        } else {
          state.usageLimit = isPremium ? CONFIG.PRO_DAILY_LIMIT : CONFIG.FREE_DAILY_LIMIT;
        }

        saveState();
        showMainApp();
        updateUserUI();
        hideLoginError();
      } else {
        showLoginError('Лицензия недействительна или истекла');
      }
    } else {
      const errorData = await response.json().catch(() => ({}));
      showLoginError(errorData.message || 'Неверный лицензионный ключ');
    }
  } catch (error) {
    console.error('[Login] Error:', error);
    showLoginError('Ошибка подключения к серверу. Попробуйте позже.');
  }

  elements.loginBtn.disabled = false;
  elements.loginBtn.textContent = 'Активировать';
}

function handleLogout() {
  state.isAuthenticated = false;
  state.licenseKey = null;
  state.user = null;
  state.usageCount = 0;
  
  localStorage.removeItem('sheetgpt_state');
  
  closeSettings();
  showLoginScreen();
  elements.licenseInput.value = '';
}

function showLoginError(message) {
  elements.loginError.textContent = message;
  elements.loginError.classList.add('show');
}

function hideLoginError() {
  elements.loginError.classList.remove('show');
}

function formatLicenseKey(e) {
  let value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
  let formatted = '';
  
  for (let i = 0; i < value.length && i < 16; i++) {
    if (i > 0 && i % 4 === 0) {
      formatted += '-';
    }
    formatted += value[i];
  }
  
  e.target.value = formatted;
}

// ============================================
// USER UI
// ============================================
function updateUserUI() {
  if (!state.user) return;

  const name = state.user.name || 'Пользователь';
  const initial = name.charAt(0).toUpperCase();
  const plan = (state.user.plan || 'free').toLowerCase();
  const isPro = ['pro', 'premium', 'unlimited'].includes(plan);
  
  // Main UI
  elements.userAvatar.textContent = initial;
  elements.userName.textContent = name;
  elements.planBadge.textContent = isPro ? 'PRO' : 'FREE';
  elements.planBadge.classList.toggle('pro', isPro);
  
  // Usage bar
  elements.usageCount.textContent = state.usageCount;
  elements.usageLimit.textContent = state.usageLimit;
  const percentage = (state.usageCount / state.usageLimit) * 100;
  elements.usageBarFill.style.width = `${Math.min(percentage, 100)}%`;
  elements.usageBarFill.classList.toggle('warning', percentage >= 80);
  
  // Hide usage bar for pro users
  elements.usageContainer.style.display = isPro ? 'none' : 'block';
  
  // Settings modal
  elements.settingsAvatar.textContent = initial;
  elements.settingsUserName.textContent = name;
  elements.settingsPlan.textContent = isPro ? 'PRO план' : 'Бесплатный план';
  elements.settingsLicenseKey.value = state.licenseKey || '';
  elements.customContextInput.value = state.customContext || '';
  elements.userNameInput.value = name;
  updateCharCounter();
}

function updateUsage() {
  state.usageCount++;
  saveState();
  updateUserUI();
}

// ============================================
// THEME
// ============================================
function toggleTheme() {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  applyTheme();
  saveState();
}

function applyTheme() {
  document.body.setAttribute('data-theme', state.theme);
}

// ============================================
// HISTORY
// ============================================
function toggleHistoryDropdown() {
  elements.historyDropdown.classList.toggle('show');
}

function renderHistory() {
  // Filter out invalid history items
  const validHistory = state.chatHistory.filter(item => item && item.query);

  if (validHistory.length === 0) {
    elements.historyList.innerHTML = '<li class="dropdown-empty">История пуста</li>';
    return;
  }

  elements.historyList.innerHTML = validHistory.slice(0, 10).map((item, index) => {
    const queryText = item.query || '';
    return `
      <li class="dropdown-item" data-index="${index}" data-query="${escapeHtml(queryText)}">
        <div class="dropdown-item-title">${escapeHtml(queryText.substring(0, 40))}${queryText.length > 40 ? '...' : ''}</div>
        <div class="dropdown-item-meta">${formatTime(item.timestamp)}</div>
      </li>
    `;
  }).join('');

  // Add click handlers
  elements.historyList.querySelectorAll('.dropdown-item').forEach(item => {
    item.addEventListener('click', () => {
      const query = item.dataset.query;
      if (query) {
        elements.messageInput.value = query;
        handleInputChange();
        elements.historyDropdown.classList.remove('show');
      }
    });
  });
}

function addToHistory(query, response = null) {
  state.chatHistory.unshift({
    query,
    response: response, // Store response for conversation context
    timestamp: Date.now()
  });
  
  // Limit history size
  if (state.chatHistory.length > CONFIG.MAX_HISTORY_ITEMS) {
    state.chatHistory = state.chatHistory.slice(0, CONFIG.MAX_HISTORY_ITEMS);
  }
  
  saveState();
  renderHistory();
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  }
  
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

// ============================================
// SETTINGS
// ============================================
function openSettings() {
  elements.settingsModal.classList.add('show');
  updateUserUI();
}

function closeSettings() {
  elements.settingsModal.classList.remove('show');
}

function saveSettings() {
  const newName = elements.userNameInput.value.trim() || 'Пользователь';
  const newContext = elements.customContextInput.value.trim();

  state.user.name = newName;
  state.customContext = newContext;

  saveState();
  // v8.0.1: Sync customContext with chrome.storage.local for content.js access
  sendToContentScript('SAVE_CUSTOM_CONTEXT', { context: state.customContext });
  updateUserUI();
  closeSettings();
}

function updateCharCounter() {
  const count = elements.customContextInput.value.length;
  elements.charCount.textContent = count;
}

// ============================================
// PERSONALIZATION (Design System v1.2)
// ============================================
function openPersonalization() {
  if (elements.personalizationModal) {
    elements.personalizationModal.classList.add('show');
    // Set current context in textarea
    if (elements.personalizationContextInput) {
      elements.personalizationContextInput.value = state.customContext || '';
    }
  }
}

function closePersonalization() {
  if (elements.personalizationModal) {
    elements.personalizationModal.classList.remove('show');
  }
}

function savePersonalization() {
  if (elements.personalizationContextInput) {
    state.customContext = elements.personalizationContextInput.value.trim();
    // Also sync with settings modal
    if (elements.customContextInput) {
      elements.customContextInput.value = state.customContext;
      updateCharCounter();
    }
    saveState();
    // v8.0.1: Sync customContext with chrome.storage.local for content.js access
    sendToContentScript('SAVE_CUSTOM_CONTEXT', { context: state.customContext });
  }
  closePersonalization();
}

// ============================================
// CHAT
// ============================================
function handleInputChange() {
  const hasContent = elements.messageInput.value.trim().length > 0;
  elements.sendBtn.disabled = !hasContent || state.isLoading;
  
  // Auto-resize textarea
  elements.messageInput.style.height = 'auto';
  elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 80) + 'px';
}

function handleInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!elements.sendBtn.disabled) {
      sendMessage();
    }
  }
}

async function sendMessage() {
  const query = elements.messageInput.value.trim();
  if (!query || state.isLoading) return;
  
  // Check usage limit for free users
  const userPlan = (state.user.plan || 'free').toLowerCase();
  const isPremiumUser = ['pro', 'premium', 'unlimited'].includes(userPlan);
  if (!isPremiumUser && state.usageCount >= state.usageLimit) {
    addAIMessage({
      type: 'error',
      text: 'Вы исчерпали лимит запросов на сегодня. Обновите план до PRO для безлимитного доступа.'
    });
    return;
  }
  
  // Hide empty state
  elements.emptyState.style.display = 'none';
  
  // Add user message
  addUserMessage(query);
  
  // Clear input
  elements.messageInput.value = '';
  handleInputChange();
  
  // History will be updated after response
  const currentQuery = query; // Save for history
  
  // Show loading
  state.isLoading = true;
  elements.sendBtn.disabled = true;
  const loadingEl = addLoadingIndicator();
  
  try {
    // Use PROCESS_QUERY action via content.js (it handles sheet data and API call)
    // Build conversation history for context (last 5 exchanges)
    const conversationHistory = state.chatHistory
      .slice(0, 5)
      .filter(item => item.query && item.response)
      .map(item => ({ query: item.query, response: item.response }))
      .reverse(); // oldest first

    // v9.2.0: Detect and handle cross-sheet VLOOKUP
    let referenceSheet = null;
    const crossSheetPattern = detectCrossSheetQuery(query);
    
    if (crossSheetPattern) {
      console.log('[Sidebar] Cross-sheet query detected:', crossSheetPattern);
      try {
        // Get reference sheet data from background
        referenceSheet = await getReferenceSheetData(crossSheetPattern.sheetName);
        console.log('[Sidebar] Reference sheet loaded:', referenceSheet?.name, referenceSheet?.headers?.length, 'cols');
      } catch (e) {
        console.warn('[Sidebar] Could not load reference sheet:', e);
      }
    }
    
    console.log('[Sidebar] 🚀 Sending PROCESS_QUERY with referenceSheet:', referenceSheet);
    const result = await sendToContentScript('PROCESS_QUERY', {
      query,
      history: conversationHistory,
      referenceSheet: referenceSheet,
      licenseKey: state.licenseKey  // v10.2: CRITICAL - pass license for usage tracking!
    });
    console.log('[Sidebar] Sent PROCESS_QUERY with licenseKey:', state.licenseKey ? 'YES' : 'NO');
    console.log('[Sidebar] referenceSheet in data:', referenceSheet ? 'YES' : 'NO');

    // Remove loading
    loadingEl.remove();

    // Transform and display AI response
    // v10.1.5: Pass full referenceSheet data and query for frontend VLOOKUP
    const response = transformAPIResponse(result, {
      isVlookup: !!referenceSheet,
      referenceSheetName: referenceSheet?.name,
      referenceSheetHeaders: referenceSheet?.headers,
      referenceSheetData: referenceSheet?.data,
      lastQuery: query  // Pass query for fallback column detection
    });
    addAIMessage(response);

    // v9.1.0: Sync usage from server response
    if (result._usage) {
      state.usageCount = result._usage.queries_used || state.usageCount + 1;
      state.usageLimit = result._usage.queries_limit || state.usageLimit;
      saveState();
      updateUserUI();
      console.log('[Sidebar] Usage synced from server:', result._usage);
    } else {
      // Fallback to local increment
      updateUsage();
    }

    // Add to history with response
    addToHistory(currentQuery, result.summary || result.explanation || null);

  } catch (error) {
    loadingEl.remove();
    addAIMessage({
      type: 'error',
      text: error.message || 'Произошла ошибка при обработке запроса'
    });
  }
  
  state.isLoading = false;
  handleInputChange();
}

function addUserMessage(text) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message user';
  messageDiv.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
  elements.chatContainer.appendChild(messageDiv);
  scrollToBottom();
}

function addAIMessage(response) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message ai';

  let content = '';

  // Error response
  if (response.type === 'error') {
    content = `
      <div class="status-box error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        <span>${escapeHtml(cleanResponseText(response.text))}</span>
      </div>
    `;
  }

  // Formula response
  else if (response.type === 'formula') {
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 3v18"/></svg>
        Формула
      </div>
      <div class="formula-block">${escapeHtml(response.formula)}</div>
      ${response.explanation ? `<div class="response-content"><p>${escapeHtml(cleanResponseText(response.explanation))}</p></div>` : ''}
      <div class="action-buttons">
        <button class="action-btn" data-action="insertFormula" data-formula="${escapeHtml(response.formula)}">Вставить</button>
        <button class="action-btn secondary" data-action="copyToClipboard" data-text="${escapeHtml(response.formula)}">Копировать</button>
      </div>
    `;
  }

  // Analysis response
  else if (response.type === 'analysis') {
    // v9.3.0: Use formatAnalysisResponse for structured display
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        Анализ
      </div>
      <div class="response-content">${formatAnalysisResponse(response.text)}</div>
    `;
  }

  // Table response
  else if (response.type === 'table') {
    const rowCount = response.data?.rows?.length || 0;
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 3v18"/></svg>
        Таблица
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Таблица готова к вставке')}</p>
      </div>
      <div class="summary-box">${rowCount} записей</div>
      <div class="action-buttons">
        <button class="action-btn" data-action="insertTable">Вставить таблицу</button>
      </div>
    `;
  }

  // Highlight response
  else if (response.type === 'highlight') {
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/></svg>
        Выделение
      </div>
      <div class="status-box success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <span>${escapeHtml(cleanResponseText(response.text) || 'Строки выделены')}</span>
      </div>
    `;
  }

  // Chart response
  else if (response.type === 'chart') {
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        Диаграмма
      </div>
      <div class="status-box success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <span>${escapeHtml(cleanResponseText(response.text) || 'Диаграмма создана')}</span>
      </div>
    `;
  }

  // Chat response (AI answering a question or providing info)
  else if (response.type === 'chat') {
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        Ответ
      </div>
      <div class="response-content">${formatAnalysisResponse(response.text)}</div>
    `;
  }

  // Conditional format / Color scale
  else if (response.type === 'conditional_format' || response.type === 'color_scale') {
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 3v18"/></svg>
        Форматирование
      </div>
      <div class="status-box success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <span>${escapeHtml(cleanResponseText(response.text) || 'Форматирование применено')}</span>
      </div>
    `;
  }

  // Pivot table response
  else if (response.type === 'pivot_table') {
    const rowCount = response.pivotData?.rows?.length || 0;
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 3v18"/><path d="M9 15h6"/></svg>
        Сводная таблица
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Сводная таблица готова')}</p>
      </div>
      <div class="summary-box">${rowCount} групп</div>
      <div class="action-buttons">
        <button class="action-btn" data-action="insertPivotTable">Вставить таблицу</button>
      </div>
    `;
  }

  // v11.0: Write data response with full methodology (CleanAnalyst)
  else if (response.type === 'write_data') {
    const rowCount = response.rowCount || 0;

    // Build methodology section
    let methodologyHtml = '';
    if (response.methodology) {
      const copyableFormula = response.methodology.copyable_formula;
      methodologyHtml = `
        <div class="methodology-section">
          <div class="methodology-header">📊 Методология: ${escapeHtml(response.methodology.name || 'расчёт')}</div>
          ${response.methodology.reason ? `<div class="methodology-reason">${escapeHtml(response.methodology.reason)}</div>` : ''}
          ${response.methodology.formula ? `<div class="formula-block">${escapeHtml(response.methodology.formula)}</div>` : ''}
          ${copyableFormula ? `
            <div class="copyable-formula-section">
              <div class="copyable-formula-label">📋 Формула для копирования:</div>
              <div class="copyable-formula-row">
                <code class="copyable-formula">${escapeHtml(copyableFormula)}</code>
                <button class="copy-formula-btn" data-action="copyToClipboard" data-text="${escapeHtml(copyableFormula)}">Копировать</button>
              </div>
            </div>
          ` : ''}
        </div>
      `;
    }

    // Build examples section (show 2-3 examples max)
    let examplesHtml = '';
    if (response.examples && response.examples.length > 0) {
      const examplesToShow = response.examples.slice(0, 3);
      examplesHtml = `
        <div class="examples-section">
          <div class="examples-header">📝 Примеры расчёта:</div>
          ${examplesToShow.map(ex => `
            <div class="example-item">
              <div class="example-name">${escapeHtml(ex.item || '')}</div>
              <div class="example-input">${escapeHtml(ex.input || '')}</div>
              <div class="example-calc">${escapeHtml(ex.calculation || '')}</div>
              <div class="example-result">= ${escapeHtml(String(ex.result || ''))}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // Build warnings section
    let warningsHtml = '';
    if (response.warnings && response.warnings.length > 0) {
      warningsHtml = `
        <div class="warnings-section">
          ${response.warnings.map(w => `<div class="warning-item">⚠️ ${escapeHtml(w)}</div>`).join('')}
        </div>
      `;
    }

    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        Прогноз / Расчёт
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Расчёт выполнен')}</p>
      </div>
      ${methodologyHtml}
      ${examplesHtml}
      ${warningsHtml}
      <div class="summary-box">${rowCount} строк рассчитано</div>
    `;
  }

  // v11.1: Fill column response (direct column write without key matching)
  else if (response.type === 'fill_column') {
    const rowCount = response.rowCount || 0;

    // Build methodology section (same as write_data)
    let methodologyHtml = '';
    if (response.methodology) {
      const copyableFormula = response.methodology.copyable_formula;
      methodologyHtml = `
        <div class="methodology-section">
          <div class="methodology-header">📊 Методология: ${escapeHtml(response.methodology.name || 'заполнение')}</div>
          ${response.methodology.reason ? `<div class="methodology-reason">${escapeHtml(response.methodology.reason)}</div>` : ''}
          ${response.methodology.formula ? `<div class="formula-block">${escapeHtml(response.methodology.formula)}</div>` : ''}
          ${copyableFormula ? `
            <div class="copyable-formula-section">
              <div class="copyable-formula-label">📋 Формула для копирования:</div>
              <div class="copyable-formula-row">
                <code class="copyable-formula">${escapeHtml(copyableFormula)}</code>
                <button class="copy-formula-btn" data-action="copyToClipboard" data-text="${escapeHtml(copyableFormula)}">Копировать</button>
              </div>
            </div>
          ` : ''}
        </div>
      `;
    }

    // Build examples section
    let examplesHtml = '';
    if (response.examples && response.examples.length > 0) {
      const examplesToShow = response.examples.slice(0, 3);
      examplesHtml = `
        <div class="examples-section">
          <div class="examples-header">📝 Примеры:</div>
          ${examplesToShow.map(ex => `
            <div class="example-item">
              <div class="example-name">${escapeHtml(ex.item || '')}</div>
              <div class="example-input">${escapeHtml(ex.input || '')}</div>
              <div class="example-calc">${escapeHtml(ex.calculation || '')}</div>
              <div class="example-result">= ${escapeHtml(String(ex.result || ''))}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // Build warnings section
    let warningsHtml = '';
    if (response.warnings && response.warnings.length > 0) {
      warningsHtml = `
        <div class="warnings-section">
          ${response.warnings.map(w => `<div class="warning-item">⚠️ ${escapeHtml(w)}</div>`).join('')}
        </div>
      `;
    }

    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>
        Заполнение колонки
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Колонка заполнена')}</p>
      </div>
      ${methodologyHtml}
      ${examplesHtml}
      ${warningsHtml}
      <div class="summary-box">${rowCount} значений записано</div>
    `;
  }

  // v11.3: Fill multiple columns response
  else if (response.type === 'fill_columns') {
    const rowCount = response.rowCount || 0;
    const columnCount = response.columnCount || 0;

    // Build methodology section
    let methodologyHtml = '';
    if (response.methodology) {
      const copyableFormula = response.methodology.copyable_formula;
      methodologyHtml = `
        <div class="methodology-section">
          <div class="methodology-header">📊 Методология: ${escapeHtml(response.methodology.name || 'прогноз')}</div>
          ${response.methodology.reason ? `<div class="methodology-reason">${escapeHtml(response.methodology.reason)}</div>` : ''}
          ${response.methodology.formula ? `<div class="formula-block">${escapeHtml(response.methodology.formula)}</div>` : ''}
          ${copyableFormula ? `
            <div class="copyable-formula-section">
              <div class="copyable-formula-label">📋 Формула:</div>
              <div class="copyable-formula-row">
                <code class="copyable-formula">${escapeHtml(copyableFormula)}</code>
                <button class="copy-formula-btn" data-action="copyToClipboard" data-text="${escapeHtml(copyableFormula)}">Копировать</button>
              </div>
            </div>
          ` : ''}
        </div>
      `;
    }

    // Build warnings section
    let warningsHtml = '';
    if (response.warnings && response.warnings.length > 0) {
      warningsHtml = `
        <div class="warnings-section">
          ${response.warnings.map(w => `<div class="warning-item">⚠️ ${escapeHtml(w)}</div>`).join('')}
        </div>
      `;
    }

    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>
        Заполнение колонок
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Колонки заполнены')}</p>
      </div>
      ${methodologyHtml}
      ${warningsHtml}
      <div class="summary-box">${columnCount} колонок × ${rowCount} строк</div>
    `;
  }

  // CSV split (legacy)
  else if (response.type === 'csv_split') {
    const newRows = response.newRows || 0;
    const newCols = response.newCols || 0;
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
        Разбиение
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Данные разбиты')}</p>
      </div>
      <div class="summary-box">${newRows} строк x ${newCols} колонок</div>
      <div class="action-buttons">
        <button class="action-btn" data-action="applySplitData">Заменить данные</button>
      </div>
    `;
  }

  // v11.1: Replace data response (auto-executed)
  else if (response.type === 'replace_data') {
    const rowCount = response.rowCount || 0;
    const colCount = response.structuredData?.headers?.length || 0;

    // Build methodology section
    let methodologyHtml = '';
    if (response.methodology) {
      methodologyHtml = `
        <div class="methodology-section">
          <div class="methodology-header">📊 Методология: ${escapeHtml(response.methodology.name || 'структурирование')}</div>
          ${response.methodology.reason ? `<div class="methodology-reason">${escapeHtml(response.methodology.reason)}</div>` : ''}
        </div>
      `;
    }

    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
        Замена данных
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Данные заменены')}</p>
      </div>
      ${methodologyHtml}
      <div class="summary-box">${rowCount} строк × ${colCount} колонок</div>
    `;
  }

  // Clean data response
  else if (response.type === 'clean_data') {
    const originalRows = response.originalRows || 0;
    const finalRows = response.finalRows || 0;
    const removedRows = originalRows - finalRows;

    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
        Очистка данных
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Данные очищены')}</p>
      </div>
      <div class="data-block">
        <div class="data-row">
          <span class="data-label">Было строк</span>
          <span class="data-value">${originalRows}</span>
        </div>
        <div class="data-row">
          <span class="data-label">Стало строк</span>
          <span class="data-value">${finalRows}</span>
        </div>
        ${removedRows > 0 ? `
        <div class="data-row">
          <span class="data-label">Удалено</span>
          <span class="data-value" style="color: var(--error);">-${removedRows}</span>
        </div>
        ` : ''}
      </div>
      <div class="action-buttons">
        <button class="action-btn" data-action="insertCleanedData">Новый лист</button>
        <button class="action-btn secondary" data-action="overwriteWithCleanedData">Заменить</button>
      </div>
    `;
  }

  // Filter response
  else if (response.type === 'filter_data') {
    const originalRows = response.originalRows || 0;
    const filteredRows = response.filteredRows || 0;

    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46"/></svg>
        Фильтрация
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Данные отфильтрованы')}</p>
      </div>
      ${response.conditionStr ? `<div class="summary-box">${escapeHtml(response.conditionStr)}</div>` : ''}
      <div class="data-block">
        <div class="data-row">
          <span class="data-label">Найдено</span>
          <span class="data-value">${filteredRows} из ${originalRows}</span>
        </div>
      </div>
      <div class="action-buttons">
        <button class="action-btn" data-action="insertFilteredData">Новый лист</button>
        <button class="action-btn secondary" data-action="highlightFilteredRows">Выделить</button>
      </div>
    `;
  }

  // Data validation
  else if (response.type === 'data_validation') {
    const valuesCount = response.rule?.allowed_values?.length || 0;
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/></svg>
        Валидация
      </div>
      <div class="response-content">
        <p>${escapeHtml(cleanResponseText(response.text) || 'Выпадающий список создан')}</p>
      </div>
      <div class="summary-box">${valuesCount} вариантов</div>
    `;
  }

  // Chat/clarification response (agent asking a question)
  else if (response.type === 'chat') {
    // v11.6: Preserve newlines in chat responses for multi-step explanations
    const chatText = cleanResponseText(response.text, true);
    const formattedChat = escapeHtml(chatText).replace(/\n/g, '<br>');
    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        Уточнение
      </div>
      <div class="response-content">
        <p>${formattedChat}</p>
      </div>
    `;
  }

  // Success/Action message
  else if (response.type === 'success' || response.type === 'action') {
    content = `
      <div class="status-box success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <span>${escapeHtml(cleanResponseText(response.text))}</span>
      </div>
    `;
  }

  // Default fallback
  else {
    const cleaned = cleanResponseText(response.text || 'Готово');
    content = `<div class="response-content"><p>${escapeHtml(cleaned)}</p></div>`;
  }

  messageDiv.innerHTML = `<div class="message-bubble">${content}</div>`;
  elements.chatContainer.appendChild(messageDiv);
  scrollToBottom();
}

function addLoadingIndicator() {
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'message ai';
  loadingDiv.innerHTML = `
    <div class="loading-indicator">
      <div class="loading-dots">
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
      </div>
    </div>
  `;
  elements.chatContainer.appendChild(loadingDiv);
  scrollToBottom();
  return loadingDiv;
}

function scrollToBottom() {
  elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

// ============================================
// API COMMUNICATION
// ============================================

// Send message to content script and wait for response
async function sendToContentScript(action, data = {}) {
  return new Promise((resolve, reject) => {
    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const handler = (event) => {
      // Check if this is our response
      if (event.data && event.data.messageId === messageId) {
        window.removeEventListener('message', handler);
        clearTimeout(timeout);

        if (event.data.success) {
          resolve(event.data.result);
        } else {
          reject(new Error(event.data.error || 'Неизвестная ошибка'));
        }
      }
    };

    window.addEventListener('message', handler);

    // Timeout after 90 seconds (CleanAnalyst needs more time for large datasets)
    const timeout = setTimeout(() => {
      window.removeEventListener('message', handler);
      reject(new Error('Таймаут ожидания ответа. Перезагрузите страницу.'));
    }, 90000);

    // Send message to parent (content script)
    console.log('[Sidebar] Sending to content script:', { action, data, messageId });
    window.parent.postMessage({ action, data, messageId }, '*');
  });
}

async function getSheetData() {
  return new Promise((resolve) => {
    // Try to get data from parent window (Google Sheets)
    if (window.parent !== window) {
      window.parent.postMessage({ type: 'GET_SHEET_DATA' }, '*');
      
      const handler = (event) => {
        if (event.data && event.data.type === 'SHEET_DATA') {
          window.removeEventListener('message', handler);
          resolve(event.data.data);
        }
      };
      
      window.addEventListener('message', handler);
      
      // Timeout fallback
      setTimeout(() => {
        window.removeEventListener('message', handler);
        resolve(null);
      }, 2000);
    } else {
      resolve(null);
    }
  });
}

async function overwriteSheetData(dataToWrite) {
  return new Promise((resolve, reject) => {
    console.log('[Sidebar] overwriteSheetData called with:', dataToWrite);
    // Send message to content script to write data
    window.parent.postMessage({
      type: 'OVERWRITE_SHEET_DATA',
      data: dataToWrite
    }, '*');

    const handler = (event) => {
      if (event.data && event.data.type === 'OVERWRITE_SHEET_DATA_RESPONSE') {
        window.removeEventListener('message', handler);
        if (event.data.success) {
          console.log('[Sidebar] ✅ Sheet data written successfully');
          resolve(event.data);
        } else {
          console.error('[Sidebar] ❌ Failed to write sheet data:', event.data.error);
          reject(new Error(event.data.error || 'Failed to write data'));
        }
      }
    };

    window.addEventListener('message', handler);

    // Timeout after 10 seconds
    setTimeout(() => {
      window.removeEventListener('message', handler);
      reject(new Error('Timeout waiting for sheet data write response'));
    }, 10000);
  });
}

// v10.1.1: Append column by key (VLOOKUP mode)
// Adds new column(s) to the right of existing data, matching rows by key column
async function appendColumnByKey(keyColumn, writeHeaders, writeData) {
  return new Promise((resolve, reject) => {
    console.log('[Sidebar] appendColumnByKey called:', { keyColumn, writeHeaders, writeData });

    // Send message to content script to append column
    window.parent.postMessage({
      type: 'APPEND_COLUMN_BY_KEY',
      data: {
        keyColumn: keyColumn,        // Column name to match by (e.g., "Артикул")
        writeHeaders: writeHeaders,  // All headers from VLOOKUP result [key, col1, col2...]
        writeData: writeData         // Data rows [[keyVal, val1, val2], ...]
      }
    }, '*');

    const handler = (event) => {
      if (event.data && event.data.type === 'APPEND_COLUMN_BY_KEY_RESPONSE') {
        window.removeEventListener('message', handler);
        if (event.data.success) {
          console.log('[Sidebar] ✅ Column appended successfully');
          resolve(event.data);
        } else {
          console.error('[Sidebar] ❌ Failed to append column:', event.data.error);
          reject(new Error(event.data.error || 'Failed to append column'));
        }
      }
    };

    window.addEventListener('message', handler);

    // Timeout after 15 seconds (longer for complex operations)
    setTimeout(() => {
      window.removeEventListener('message', handler);
      reject(new Error('Timeout waiting for append column response'));
    }, 15000);
  });
}

// v11.1: Fill column directly (without key matching)
// Writes values directly to a specific column by letter (e.g., "E")
async function fillColumn(targetColumn, columnName, startRow, values) {
  return new Promise((resolve, reject) => {
    console.log('[Sidebar] fillColumn called:', { targetColumn, columnName, startRow, valuesCount: values?.length });

    // Send message to content script to fill column
    window.parent.postMessage({
      type: 'FILL_COLUMN',
      data: {
        targetColumn: targetColumn,  // Column letter (e.g., "E")
        columnName: columnName,      // Column header name (e.g., "Прогноз")
        startRow: startRow || 2,     // Row to start writing (default: 2)
        values: values               // Array of values to write
      }
    }, '*');

    const handler = (event) => {
      if (event.data && event.data.type === 'FILL_COLUMN_RESPONSE') {
        window.removeEventListener('message', handler);
        if (event.data.success) {
          console.log('[Sidebar] ✅ Column filled successfully');
          resolve(event.data);
        } else {
          console.error('[Sidebar] ❌ Failed to fill column:', event.data.error);
          reject(new Error(event.data.error || 'Failed to fill column'));
        }
      }
    };

    window.addEventListener('message', handler);

    // Timeout after 15 seconds
    setTimeout(() => {
      window.removeEventListener('message', handler);
      reject(new Error('Timeout waiting for fill column response'));
    }, 15000);
  });
}

// v11.3: Fill multiple columns at once
async function fillColumns(startRow, columns) {
  return new Promise((resolve, reject) => {
    console.log('[Sidebar] fillColumns called:', { startRow, columnsCount: columns?.length });

    // Send message to content script to fill multiple columns
    window.parent.postMessage({
      type: 'FILL_COLUMNS',
      data: {
        startRow: startRow || 2,
        columns: columns  // Array of {target, name, values}
      }
    }, '*');

    const handler = (event) => {
      if (event.data && event.data.type === 'FILL_COLUMNS_RESPONSE') {
        window.removeEventListener('message', handler);
        if (event.data.success) {
          console.log('[Sidebar] ✅ All columns filled successfully');
          resolve(event.data);
        } else {
          console.error('[Sidebar] ❌ Failed to fill columns:', event.data.error);
          reject(new Error(event.data.error || 'Failed to fill columns'));
        }
      }
    };

    window.addEventListener('message', handler);

    // Timeout after 30 seconds (longer for multiple columns)
    setTimeout(() => {
      window.removeEventListener('message', handler);
      reject(new Error('Timeout waiting for fill columns response'));
    }, 30000);
  });
}

async function callAPI(query, sheetData, history = []) {
  // Format payload for /api/v1/analyze endpoint (CleanAnalyst v1.0)
  const payload = {
    query: query,
    column_names: sheetData?.headers || [],
    sheet_data: sheetData?.rows || [],
    custom_context: state.customContext || '',
    history: history
  };

  console.log('[API] Sending request to CleanAnalyst:', payload);

  let lastError;

  for (let attempt = 0; attempt < CONFIG.MAX_RETRIES; attempt++) {
    try {
      const response = await fetch(`${CONFIG.API_URL}/api/v1/analyze`, {
        method: 'POST',
        headers: (() => {
        const h = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
        if (state.licenseKey) {
          h['X-License-Key'] = state.licenseKey;
          console.log('[API] Sending X-License-Key:', state.licenseKey);
        } else {
          console.warn('[API] No license key available!');
        }
        return h;
      })(),
        body: JSON.stringify(payload)
      });

      console.log('[API] Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[API] Error response:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      console.log('[API] Response data:', result);

      // Transform API response to UI format
      // v9.3.1: Preserve _usage for tracking
      const transformed = transformAPIResponse(result);
      console.log('[API] Raw result._usage:', result._usage);
      if (result._usage) {
        transformed._usage = result._usage;
        console.log('[API] _usage attached to response');
      } else {
        console.warn('[API] No _usage in response - server may not be tracking!');
      }
      return transformed;

    } catch (error) {
      console.error('[API] Attempt', attempt + 1, 'failed:', error);
      lastError = error;

      if (attempt < CONFIG.MAX_RETRIES - 1) {
        await new Promise(r => setTimeout(r, CONFIG.RETRY_DELAYS[attempt]));
      }
    }
  }

  console.error('[API] All attempts failed, using demo response');
  // Return demo response if API fails
  return getDemoResponse(query);
}

// Translate common English responses to Russian
function translateToRussian(text) {
  if (!text) return text;

  const str = String(text).trim();

  // Boolean translations
  const translations = {
    'True': 'Да',
    'true': 'Да',
    'False': 'Нет',
    'false': 'Нет',
    'Yes': 'Да',
    'yes': 'Да',
    'No': 'Нет',
    'no': 'Нет',
    'None': 'Нет данных',
    'null': 'Нет данных',
    'undefined': 'Нет данных',
    'N/A': 'Н/Д',
    'Not found': 'Не найдено',
    'No data': 'Нет данных',
    'No results': 'Нет результатов',
    'Success': 'Успешно',
    'Error': 'Ошибка',
    'Failed': 'Не удалось'
  };

  // Direct match
  if (translations[str]) {
    return translations[str];
  }

  return text;
}

// Transform API response to UI format
// v10.1.2: Added options parameter for VLOOKUP auto-detection
function transformAPIResponse(apiResponse, options = {}) {
  console.log('[Sidebar] transformAPIResponse received:', apiResponse);
  console.log('[Sidebar] action_type:', apiResponse.action_type);
  console.log('[Sidebar] formula_template:', apiResponse.formula_template);
  console.log('[Sidebar] column_name:', apiResponse.column_name);
  console.log('[Sidebar] chart_spec:', apiResponse.chart_spec);
  console.log('[Sidebar] options:', options);

  // Store structured_data globally for table insertion
  if (apiResponse.structured_data) {
    window.lastStructuredData = apiResponse.structured_data;
  }

  // If response has formula
  if (apiResponse.formula) {
    return {
      type: 'formula',
      formula: apiResponse.formula,
      explanation: translateToRussian(apiResponse.explanation || apiResponse.summary || '')
    };
  }

  // If response is a sort action
  if (apiResponse.action_type === 'sort' && apiResponse.sort_column_index !== undefined) {
    // Trigger sort action
    sortRangeInSheet(apiResponse.sort_column_index, apiResponse.sort_order || 'ASCENDING');
    return {
      type: 'action',
      text: apiResponse.summary || `Данные отсортированы по колонке "${apiResponse.sort_column}"`,
      actionType: 'sort'
    };
  }

  // If response is a freeze action
  if (apiResponse.action_type === 'freeze') {
    // Trigger freeze action
    freezeRowsInSheet(apiResponse.freeze_rows || 0, apiResponse.freeze_columns || 0);
    return {
      type: 'action',
      text: apiResponse.summary || 'Строки/столбцы закреплены',
      actionType: 'freeze'
    };
  }

  // If response is a format action
  if (apiResponse.action_type === 'format') {
    // Trigger format action
    formatRowInSheet(apiResponse.target_row - 1 || 0, apiResponse.bold, apiResponse.background_color);
    return {
      type: 'action',
      text: apiResponse.summary || 'Форматирование применено',
      actionType: 'format'
    };
  }

  // If response is a chart action
  console.log('[Sidebar] Checking chart condition:', {
    action_type: apiResponse.action_type,
    has_chart_spec: !!apiResponse.chart_spec,
    condition_met: apiResponse.action_type === 'chart' && apiResponse.chart_spec
  });

  if (apiResponse.action_type === 'chart' && apiResponse.chart_spec) {
    console.log('[Sidebar] ✅ Chart condition met! Creating chart with spec:', JSON.stringify(apiResponse.chart_spec));
    // Trigger chart creation and handle result
    createChartInSheet(apiResponse.chart_spec).then(() => {
      console.log('[Sidebar] ✅ Chart creation promise resolved');
      addAIMessage({ type: 'success', text: '✅ Диаграмма успешно создана!' });
    }).catch(err => {
      console.error('[Sidebar] ❌ Chart creation promise rejected:', err);
    });
    return {
      type: 'chart',
      text: apiResponse.summary || `Создаю диаграмму "${apiResponse.chart_spec.title || 'Диаграмма'}"...`,
      chartSpec: apiResponse.chart_spec
    };
  }

  // If response is a color scale (gradient) action
  if (apiResponse.action_type === 'color_scale' && (apiResponse.color_scale_rule || apiResponse.rule)) {
    const rule = apiResponse.color_scale_rule || apiResponse.rule;
    console.log('[Sidebar] ✅ Color scale condition met! Applying gradient...', rule);
    // Apply color scale immediately
    applyColorScaleInSheet(rule).then(() => {
      console.log('[Sidebar] ✅ Color scale applied successfully');
      addAIMessage({ type: 'success', text: '✅ Цветовая шкала применена!' });
    }).catch(err => {
      console.error('[Sidebar] ❌ Color scale failed:', err);
      addAIMessage({ type: 'error', text: `Ошибка применения цветовой шкалы: ${err.message}` });
    });
    return {
      type: 'color_scale',
      text: apiResponse.summary || `Применяю цветовую шкалу для "${rule.column_name}"...`,
      rule: rule
    };
  }

  // If response is a conditional format action
  if (apiResponse.action_type === 'conditional_format' && (apiResponse.conditional_rule || apiResponse.rule)) {
    const rule = apiResponse.conditional_rule || apiResponse.rule;
    console.log('[Sidebar] ✅ Conditional format condition met! Applying...', rule);
    // Trigger conditional format action
    applyConditionalFormatInSheet(rule);
    return {
      type: 'conditional_format',
      text: apiResponse.summary || 'Условное форматирование применено',
      rule: rule
    };
  }

  // If response is a convert to numbers action
  if (apiResponse.action_type === 'convert_to_numbers' && apiResponse.convert_rule) {
    const rule = apiResponse.convert_rule;
    console.log('[Sidebar] ✅ Convert to numbers condition met! Converting...', rule);
    convertColumnToNumbersInSheet(rule).then(() => {
      console.log('[Sidebar] ✅ Column converted to numbers');
      addAIMessage({ type: 'success', text: `✅ Колонка "${rule.column_name}" преобразована в числа!` });
    }).catch(err => {
      console.error('[Sidebar] ❌ Convert to numbers failed:', err);
      addAIMessage({ type: 'error', text: `Ошибка преобразования: ${err.message}` });
    });
    return {
      type: 'convert_to_numbers',
      text: apiResponse.summary || `Преобразую колонку "${rule.column_name}" в числа...`,
      rule: rule
    };
  }

  // If response is a pivot table action
  if (apiResponse.action_type === 'pivot_table' && apiResponse.pivot_data) {
    console.log('[Sidebar] ✅ Pivot table condition met! Creating...');
    // Store pivot data for insertion
    window.lastPivotData = apiResponse.pivot_data;
    return {
      type: 'pivot_table',
      text: apiResponse.summary || 'Сводная таблица готова',
      pivotData: apiResponse.pivot_data,
      groupColumn: apiResponse.group_column,
      valueColumn: apiResponse.value_column,
      aggFunc: apiResponse.agg_func
    };
  }

  // If response is a write_value action (write single value to specific cell)
  if (apiResponse.action_type === 'write_value' && apiResponse.target_cell && apiResponse.value !== undefined) {
    console.log('[Sidebar] ✅ Write value condition met! Cell:', apiResponse.target_cell, 'Value:', apiResponse.value);
    // Execute immediately
    writeValueToCell(apiResponse.target_cell, apiResponse.value);
    return {
      type: 'action_done',
      text: apiResponse.summary || `Значение ${apiResponse.value} записано в ячейку ${apiResponse.target_cell}`
    };
  }

  // If response is an add_formula action (add new column with formula)
  if (apiResponse.action_type === 'add_formula' && apiResponse.formula_template) {
    console.log('[Sidebar] ➕ Add formula condition met!', apiResponse);
    // Execute immediately - add column with formula
    addFormulaColumn(apiResponse.column_name, apiResponse.formula_template, apiResponse.row_count, apiResponse.target_column);
    return {
      type: 'action_done',
      text: apiResponse.summary || `Добавлен столбец "${apiResponse.column_name}" с формулой`
    };
  }

  // v11.1: If response is a fill_column action (direct column write without key matching)
  if (apiResponse.action_type === 'fill_column' && apiResponse.fill_values) {
    console.log('[Sidebar] 📝 Fill column condition met!');
    console.log('[Sidebar] Target column:', apiResponse.target_column);
    console.log('[Sidebar] Column name:', apiResponse.column_name);
    console.log('[Sidebar] Start row:', apiResponse.start_row);
    console.log('[Sidebar] Values count:', apiResponse.fill_values?.length);

    // Call fillColumn to write values directly to the specified column
    fillColumn(
      apiResponse.target_column,   // Target column letter (e.g., "E")
      apiResponse.column_name,     // Column header name (e.g., "Прогноз")
      apiResponse.start_row,       // Row to start writing (e.g., 8)
      apiResponse.fill_values      // Array of values to write
    ).then(() => {
      console.log('[Sidebar] ✅ Column filled successfully');
      addAIMessage({ type: 'success', text: apiResponse.summary || `✅ Колонка ${apiResponse.target_column} заполнена!` });
    }).catch(err => {
      console.error('[Sidebar] ❌ Fill column failed:', err);
      addAIMessage({ type: 'error', text: `Ошибка заполнения колонки: ${err.message}` });
    });

    return {
      type: 'fill_column',
      text: apiResponse.summary || `Заполняю колонку ${apiResponse.target_column}...`,
      dataWritten: true,
      // v11.0: Pass full CleanAnalyst methodology for display
      thinking: apiResponse.thinking,
      methodology: apiResponse.methodology,
      examples: apiResponse.examples,
      warnings: apiResponse.warnings,
      rowCount: apiResponse.fill_values?.length || 0
    };
  }

  // v11.3: If response is a fill_columns action (multiple columns at once)
  if (apiResponse.action_type === 'fill_columns' && apiResponse.columns) {
    console.log('[Sidebar] 📝 Fill COLUMNS (multiple) condition met!');
    console.log('[Sidebar] Start row:', apiResponse.start_row);
    console.log('[Sidebar] Columns:', apiResponse.columns.length);

    // Call fillColumns to write values to multiple columns
    fillColumns(
      apiResponse.start_row,
      apiResponse.columns
    ).then(() => {
      console.log('[Sidebar] ✅ All columns filled successfully');
      const colNames = apiResponse.columns.map(c => c.name || c.target).join(', ');
      addAIMessage({ type: 'success', text: apiResponse.summary || `✅ Колонки заполнены: ${colNames}` });
    }).catch(err => {
      console.error('[Sidebar] ❌ Fill columns failed:', err);
      addAIMessage({ type: 'error', text: `Ошибка заполнения колонок: ${err.message}` });
    });

    return {
      type: 'fill_columns',
      text: apiResponse.summary || `Заполняю колонки...`,
      dataWritten: true,
      thinking: apiResponse.thinking,
      methodology: apiResponse.methodology,
      examples: apiResponse.examples,
      warnings: apiResponse.warnings,
      rowCount: apiResponse.columns[0]?.values?.length || 0,
      columnCount: apiResponse.columns.length
    };
  }

  // v11.1: If response is a replace_data action (full data replacement, CSV split)
  if (apiResponse.action_type === 'replace_data' && apiResponse.structured_data) {
    console.log('[Sidebar] 📋 Replace data condition met!');
    console.log('[Sidebar] Headers:', apiResponse.structured_data.headers);
    console.log('[Sidebar] Rows:', apiResponse.structured_data.rows?.length);

    // Store structured data for insertion
    window.lastStructuredData = apiResponse.structured_data;

    // Execute replacement immediately
    overwriteSheetData({
      headers: apiResponse.structured_data.headers,
      rows: apiResponse.structured_data.rows
    }).then(() => {
      console.log('[Sidebar] ✅ Data replaced successfully');
      addAIMessage({ type: 'success', text: apiResponse.summary || '✅ Данные успешно заменены!' });
    }).catch(err => {
      console.error('[Sidebar] ❌ Replace data failed:', err);
      addAIMessage({ type: 'error', text: `Ошибка замены данных: ${err.message}` });
    });

    return {
      type: 'replace_data',
      text: apiResponse.summary || 'Заменяю данные в таблице...',
      structuredData: apiResponse.structured_data,
      thinking: apiResponse.thinking,
      methodology: apiResponse.methodology,
      examples: apiResponse.examples,
      warnings: apiResponse.warnings,
      rowCount: apiResponse.structured_data.rows?.length || 0
    };
  }

  // If response is a chat/clarification action (agent wants to ask a question)
  if (apiResponse.action_type === 'chat' && apiResponse.message) {
    console.log('[Sidebar] 💬 Chat action - agent asking:', apiResponse.message);
    return {
      type: 'chat',
      text: apiResponse.message
    };
  }

  // If response is a clean data action
  if (apiResponse.action_type === 'clean_data' && apiResponse.cleaned_data) {
    console.log('[Sidebar] ✅ Clean data condition met!');
    // Store cleaned data for insertion
    window.lastCleanedData = apiResponse.cleaned_data;
    return {
      type: 'clean_data',
      text: apiResponse.summary || 'Данные очищены',
      cleanedData: apiResponse.cleaned_data,
      originalRows: apiResponse.original_rows,
      finalRows: apiResponse.final_rows,
      operations: apiResponse.operations,
      changes: apiResponse.changes
    };
  }

  // If response is a data validation action
  if (apiResponse.action_type === 'data_validation' && apiResponse.rule) {
    console.log('[Sidebar] ✅ Data validation condition met!');
    // Apply validation immediately
    setDataValidationInSheet(apiResponse.rule);
    return {
      type: 'data_validation',
      text: apiResponse.summary || 'Валидация данных создана',
      rule: apiResponse.rule
    };
  }

  // If response is a filter action
  if (apiResponse.action_type === 'filter_data' && apiResponse.filtered_data) {
    console.log('[Sidebar] ✅ Filter condition met!');
    // Store filtered data for later use
    window.lastFilteredData = apiResponse.filtered_data;
    return {
      type: 'filter_data',
      text: apiResponse.summary || 'Данные отфильтрованы',
      filteredData: apiResponse.filtered_data,
      originalRows: apiResponse.original_rows,
      filteredRows: apiResponse.filtered_rows,
      conditionStr: apiResponse.condition_str
    };
  }

  // If response has highlight_rows
  if (apiResponse.highlight_rows && apiResponse.highlight_rows.length > 0) {
    // Trigger highlight action with color from response
    highlightRowsInSheet(apiResponse.highlight_rows, apiResponse.highlight_color);
    return {
      type: 'highlight',
      text: `Выделено ${apiResponse.highlighted_count || apiResponse.highlight_rows.length} строк`,
      rows: apiResponse.highlight_rows
    };
  }


  // v10.1.3: If response is a vlookup action (frontend does the lookup)
  if (apiResponse.action_type === 'vlookup' && options.referenceSheetData) {
    console.log('[Sidebar] 🔗 VLOOKUP action - doing lookup on frontend');
    const keyColumn = apiResponse.key_column || 'Артикул';
    let valueColumn = apiResponse.value_column;

    // v10.1.5: Fallback - extract column from query if AI didn't specify
    if (!valueColumn && options.lastQuery) {
      console.log('[Sidebar] 🔍 Trying to extract value_column from query:', options.lastQuery);
      const refHeaders = options.referenceSheetHeaders || [];
      const queryLower = options.lastQuery.toLowerCase();

      // Try to find matching column from reference sheet headers
      for (const header of refHeaders) {
        if (header && header.toLowerCase() !== keyColumn.toLowerCase()) {
          // Check if header name appears in query
          if (queryLower.includes(header.toLowerCase())) {
            valueColumn = header;
            console.log('[Sidebar] ✅ Found value_column in query:', valueColumn);
            break;
          }
        }
      }

      // Try common month names in Russian
      if (!valueColumn) {
        const months = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                        'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'];
        for (const month of months) {
          if (queryLower.includes(month)) {
            // Find matching header (case-insensitive)
            const matchingHeader = refHeaders.find(h =>
              h && h.toLowerCase().includes(month)
            );
            if (matchingHeader) {
              valueColumn = matchingHeader;
              console.log('[Sidebar] ✅ Found month in query:', valueColumn);
              break;
            }
          }
        }
      }
    }

    if (!valueColumn) {
      console.error('[Sidebar] ❌ VLOOKUP missing value_column');
      return { type: 'error', text: 'Ошибка: не указана колонка для подтягивания. Укажите название колонки (например "октябрь")' };
    }

    // Find column indices in reference sheet
    const refHeaders = options.referenceSheetHeaders || [];
    const keyColIdx = refHeaders.findIndex(h => h && h.toString().toLowerCase().trim() === keyColumn.toLowerCase().trim());
    const valueColIdx = refHeaders.findIndex(h => h && h.toString().toLowerCase().trim() === valueColumn.toLowerCase().trim());

    if (keyColIdx < 0) {
      console.error('[Sidebar] ❌ Key column not found in reference sheet:', keyColumn);
      return { type: 'error', text: `Колонка "${keyColumn}" не найдена в справочном листе` };
    }
    if (valueColIdx < 0) {
      console.error('[Sidebar] ❌ Value column not found in reference sheet:', valueColumn);
      return { type: 'error', text: `Колонка "${valueColumn}" не найдена в справочном листе` };
    }

    console.log('[Sidebar] 🔗 Key column:', keyColumn, 'index:', keyColIdx);
    console.log('[Sidebar] 🔗 Value column:', valueColumn, 'index:', valueColIdx);

    // Build lookup data from reference sheet
    const refData = options.referenceSheetData || [];
    const writeData = refData.map(row => [row[keyColIdx], row[valueColIdx]]);
    const writeHeaders = [keyColumn, valueColumn];

    console.log('[Sidebar] 🔗 Built lookup data:', writeData.length, 'rows');

    // Call appendColumnByKey with the full data
    appendColumnByKey(keyColumn, writeHeaders, writeData).then(() => {
      console.log('[Sidebar] ✅ VLOOKUP column appended successfully');
      addAIMessage({ type: 'success', text: apiResponse.summary || `✅ Колонка "${valueColumn}" добавлена!` });
    }).catch(err => {
      console.error('[Sidebar] ❌ VLOOKUP append failed:', err);
      addAIMessage({ type: 'error', text: `Ошибка: ${err.message}` });
    });

    return {
      type: 'vlookup',
      text: apiResponse.summary || `Подтягиваю "${valueColumn}"...`,
      keyColumn,
      valueColumn
    };
  }

  // If response is a write_data action (VLOOKUP result)
  if (apiResponse.action_type === 'write_data' && apiResponse.write_data) {
    console.log('[Sidebar] ✅ Write data condition met!');

    // v10.2.6: Smart detection of append mode
    // Check if first header looks like a key column (Артикул, ID, SKU, etc.)
    const firstHeader = apiResponse.write_headers?.[0]?.toLowerCase() || '';
    const keyPatterns = ['артикул', 'id', 'sku', 'код', 'key', 'название', 'наименование', 'name'];
    const looksLikeKey = keyPatterns.some(p => firstHeader.includes(p));

    // v10.1.2: Auto-detect VLOOKUP/append mode
    // Use append mode if: merge_by_key specified, or isVlookup, or first header looks like a key
    const isVlookupMode = apiResponse.merge_by_key || options.isVlookup || looksLikeKey;
    // Use first header as key column if not specified (typically "Артикул")
    const keyColumn = apiResponse.merge_by_key || apiResponse.write_headers?.[0] || null;

    console.log('[Sidebar] 🔍 Append mode detection:', { merge_by_key: apiResponse.merge_by_key, isVlookup: options.isVlookup, looksLikeKey, firstHeader, keyColumn });

    if (isVlookupMode && keyColumn) {
      console.log('[Sidebar] 🔗 VLOOKUP mode - appending column by key:', keyColumn);
      console.log('[Sidebar] 🔗 Auto-detected from:', apiResponse.merge_by_key ? 'API response' : 'reference sheet');
      // Call appendColumnByKey instead of overwriting
      appendColumnByKey(
        keyColumn,                  // Key column name (e.g., "Артикул")
        apiResponse.write_headers,  // Headers including key + new columns
        apiResponse.write_data      // Data rows [[key, val1, val2], ...]
      ).then(() => {
        console.log('[Sidebar] ✅ Column appended successfully');
        addAIMessage({ type: 'success', text: apiResponse.summary || '✅ Колонка добавлена справа!' });
      }).catch(err => {
        console.error('[Sidebar] ❌ Append column failed:', err);
        addAIMessage({ type: 'error', text: `Ошибка добавления колонки: ${err.message}` });
      });
      return {
        type: 'write_data',
        text: apiResponse.summary || 'Добавляю колонку...',
        dataWritten: true,
        mergeMode: true,
        // v11.0: Pass full CleanAnalyst methodology for display
        thinking: apiResponse.thinking,
        methodology: apiResponse.methodology,
        examples: apiResponse.examples,
        warnings: apiResponse.warnings,
        rowCount: apiResponse.write_data?.length || 0
      };
    }

    // Default: overwrite mode (legacy behavior - no reference sheet)
    console.log('[Sidebar] 📝 Overwrite mode - replacing sheet data');
    const dataToWrite = {
      headers: apiResponse.write_headers,
      rows: apiResponse.write_data  // Note: "rows" not "data" - content.js expects this format
    };
    overwriteSheetData(dataToWrite).then(() => {
      console.log('[Sidebar] ✅ Data written to sheet successfully');
      addAIMessage({ type: 'success', text: apiResponse.summary || '✅ Данные успешно записаны в таблицу!' });
    }).catch(err => {
      console.error('[Sidebar] ❌ Write data failed:', err);
      addAIMessage({ type: 'error', text: `Ошибка записи данных: ${err.message}` });
    });
    return {
      type: 'write_data',
      text: apiResponse.summary || 'Записываю данные в таблицу...',
      dataWritten: true
    };
  }

  // If response is a fill_column action (direct column write without key matching)
  if (apiResponse.action_type === 'fill_column' && apiResponse.fill_values) {
    console.log('[Sidebar] ✅ Fill column condition met!');
    console.log('[Sidebar] Target column:', apiResponse.target_column);
    console.log('[Sidebar] Column name:', apiResponse.column_name);
    console.log('[Sidebar] Values count:', apiResponse.fill_values?.length);

    // Call fillColumn to write values directly to the specified column
    fillColumn(
      apiResponse.target_column,   // Target column letter (e.g., "B")
      apiResponse.column_name,     // Column header name (e.g., "Ответы")
      apiResponse.fill_values      // Array of values to write
    ).then(() => {
      console.log('[Sidebar] ✅ Column filled successfully');
      addAIMessage({ type: 'success', text: apiResponse.summary || `✅ Колонка ${apiResponse.target_column} заполнена!` });
    }).catch(err => {
      console.error('[Sidebar] ❌ Fill column failed:', err);
      addAIMessage({ type: 'error', text: `Ошибка заполнения колонки: ${err.message}` });
    });

    return {
      type: 'fill_column',
      text: apiResponse.summary || `Заполняю колонку ${apiResponse.target_column}...`,
      dataWritten: true,
      // v11.0: Pass full CleanAnalyst methodology for display
      thinking: apiResponse.thinking,
      methodology: apiResponse.methodology,
      examples: apiResponse.examples,
      warnings: apiResponse.warnings,
      rowCount: apiResponse.fill_values?.length || 0
    };
  }

  // If response is a csv_split action
  if (apiResponse.action_type === 'csv_split' && apiResponse.structured_data) {
    console.log('[Sidebar] CSV split condition met!');
    // Store split data for later use with "Заменить данные" button
    window.lastSplitData = apiResponse.structured_data;
    return {
      type: 'csv_split',
      text: apiResponse.summary || 'Данные разбиты по ячейкам',
      newRows: apiResponse.new_rows || apiResponse.structured_data.rows?.length || 0,
      newCols: apiResponse.new_cols || apiResponse.structured_data.headers?.length || 0
    };
  }

  // If response has structured_data (table) - but respect display_mode
  if (apiResponse.structured_data) {
    // v11.10: If display_mode is 'sidebar_only', don't offer table insertion
    if (apiResponse.structured_data.display_mode === 'sidebar_only') {
      // Just show the summary as analysis, don't offer to insert table
      let responseText = apiResponse.summary || apiResponse.explanation || 'Анализ завершён';
      return {
        type: 'analysis',
        text: responseText
      };
    }
    return {
      type: 'table',
      text: `Найдено ${apiResponse.structured_data.rows?.length || 0} записей`,
      data: apiResponse.structured_data
    };
  }

  // Default analysis response - translate to Russian
  let responseText = apiResponse.summary || apiResponse.explanation || apiResponse.value || apiResponse.message || 'Запрос обработан';
  responseText = translateToRussian(responseText);

  return {
    type: 'analysis',
    text: responseText
  };
}

function getDemoResponse(query) {
  const lowerQuery = query.toLowerCase();
  
  if (lowerQuery.includes('сумм') || lowerQuery.includes('sumif')) {
    return {
      type: 'formula',
      formula: '=СУММЕСЛИ(C:C;">50000";C:C)',
      explanation: 'Эта формула суммирует все значения в столбце C, которые больше 50000.'
    };
  }
  
  if (lowerQuery.includes('топ') || lowerQuery.includes('лучш') || lowerQuery.includes('первы')) {
    return {
      type: 'analysis',
      title: 'Топ результатов',
      items: ['Первая позиция', 'Вторая позиция', 'Третья позиция'],
      summary: 'Анализ основан на данных в вашей таблице.'
    };
  }
  
  if (lowerQuery.includes('выдел') || lowerQuery.includes('подсвет') || lowerQuery.includes('цвет')) {
    return {
      type: 'highlight',
      text: 'Найдено 5 строк, соответствующих критериям. Строки выделены.'
    };
  }
  
  if (lowerQuery.includes('таблиц') || lowerQuery.includes('создай') || lowerQuery.includes('генер')) {
    return {
      type: 'table',
      text: 'Таблица с данными готова к вставке в ваш документ.'
    };
  }
  
  return {
    type: 'analysis',
    text: 'Запрос обработан. Для более точных результатов убедитесь, что данные в таблице доступны.'
  };
}

function getErrorMessage(error) {
  if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
    return 'Ошибка сети. Проверьте подключение к интернету.';
  }
  if (error.message.includes('401') || error.message.includes('403')) {
    return 'Ошибка авторизации. Попробуйте перезайти.';
  }
  if (error.message.includes('429')) {
    return 'Слишком много запросов. Подождите немного.';
  }
  if (error.message.includes('500') || error.message.includes('502') || error.message.includes('503')) {
    return 'Сервер временно недоступен. Попробуйте позже.';
  }
  return 'Произошла ошибка. Попробуйте ещё раз.';
}

// ============================================
// ACTIONS
// ============================================

// Highlight rows in the sheet
async function highlightRowsInSheet(rows, color) {
  if (!rows || rows.length === 0) return;

  try {
    // Pass highlighted rows to snapshot for proper undo (clear colors, not restore data)
    await saveSheetSnapshot('Выделение строк', { highlightedRows: rows });
    await sendToContentScript('HIGHLIGHT_ROWS', { rows: rows, color: color });
    console.log('[Sidebar] Rows highlighted:', rows, 'with color:', color);
  } catch (error) {
    console.error('[Sidebar] Error highlighting rows:', error);
  }
}

async function sortRangeInSheet(columnIndex, sortOrder) {
  if (columnIndex === undefined || columnIndex === null) {
    console.error('[Sidebar] Sort error: columnIndex is required');
    return;
  }
  await saveSheetSnapshot('Сортировка');

  try {
    await sendToContentScript('SORT_RANGE', {
      columnIndex: columnIndex,
      sortOrder: sortOrder || 'ASCENDING'
    });
    console.log(`[Sidebar] Range sorted by column ${columnIndex}, order ${sortOrder}`);
  } catch (error) {
    console.error('[Sidebar] Error sorting range:', error);
  }
}

async function freezeRowsInSheet(freezeRows, freezeColumns) {
  try {
    await saveSheetSnapshot('Закрепление');
    await sendToContentScript('FREEZE_ROWS', {
      freezeRows: freezeRows || 0,
      freezeColumns: freezeColumns || 0
    });
    console.log(`[Sidebar] Frozen: ${freezeRows} rows, ${freezeColumns} columns`);
  } catch (error) {
    console.error('[Sidebar] Error freezing rows:', error);
  }
}

async function formatRowInSheet(rowIndex, bold, backgroundColor) {
  try {
    await saveSheetSnapshot('Форматирование строки');
    await sendToContentScript('FORMAT_ROW', {
      rowIndex: rowIndex || 0,
      bold: bold,
      backgroundColor: backgroundColor
    });
    console.log(`[Sidebar] Row ${rowIndex} formatted`);
  } catch (error) {
    console.error('[Sidebar] Error formatting row:', error);
  }
}

async function createChartInSheet(chartSpec) {
  if (!chartSpec) {
    console.error('[Sidebar] Chart error: chartSpec is required');
    addAIMessage({ type: 'error', text: 'Ошибка: спецификация диаграммы не найдена' });
    return;
  }

  try {
    await saveSheetSnapshot('Создание диаграммы');
    console.log('[Sidebar] Creating chart with spec:', chartSpec);
    await sendToContentScript('CREATE_CHART', {
      chartSpec: chartSpec
    });
    console.log(`[Sidebar] Chart "${chartSpec.title}" created successfully`);
  } catch (error) {
    console.error('[Sidebar] Error creating chart:', error);
    addAIMessage({
      type: 'error',
      text: `Ошибка создания диаграммы: ${error.message || error}. Попробуйте обновить страницу.`
    });
  }
}

async function applyConditionalFormatInSheet(rule) {
  if (!rule) {
    console.error('[Sidebar] Conditional format error: rule is required');
    return;
  }

  try {
    await saveSheetSnapshot('Условное форматирование');
    await sendToContentScript('APPLY_CONDITIONAL_FORMAT', {
      rule: rule
    });
    console.log(`[Sidebar] Conditional format applied to column "${rule.column_name}"`);
  } catch (error) {
    console.error('[Sidebar] Error applying conditional format:', error);
  }
}

async function applyColorScaleInSheet(rule) {
  if (!rule) {
    console.error('[Sidebar] Color scale error: rule is required');
    throw new Error('Rule is required for color scale');
  }

  try {
    await saveSheetSnapshot('Цветовая шкала');
    console.log('[Sidebar] Sending APPLY_COLOR_SCALE to content script:', rule);
    const response = await sendToContentScript('APPLY_COLOR_SCALE', {
      rule: rule
    });
    console.log(`[Sidebar] Color scale applied to column "${rule.column_name}":`, response);
    return response;
  } catch (error) {
    console.error('[Sidebar] Error applying color scale:', error);
    throw error;
  }
}

/**
 * Write a single value to a specific cell
 * @param {string} targetCell - Cell address like "B12", "C5"
 * @param {any} value - Value to write (number or string)
 */
async function writeValueToCell(targetCell, value) {
  if (!targetCell || value === undefined) {
    console.error('[Sidebar] Write value error: targetCell and value are required');
    return;
  }

  try {
    await saveSheetSnapshot('Запись в ячейку');
    console.log(`[Sidebar] Writing value ${value} to cell ${targetCell}`);
    const response = await sendToContentScript('WRITE_CELL_VALUE', {
      targetCell: targetCell,
      value: value
    });
    console.log(`[Sidebar] Value written to ${targetCell}:`, response);
    return response;
  } catch (error) {
    console.error('[Sidebar] Error writing value to cell:', error);
    addAIMessage({
      type: 'error',
      text: `Ошибка записи в ячейку ${targetCell}: ${error.message}`
    });
  }
}

/**
 * Add a new column with a formula
 * @param {string} columnName - Name for the new column header
 * @param {string} formulaTemplate - Formula template like "=H{row}+E{row}"
 * @param {number} rowCount - Number of data rows
 */
async function addFormulaColumn(columnName, formulaTemplate, rowCount, targetColumn = null) {
  if (!formulaTemplate) {
    console.error('[Sidebar] Add formula error: formulaTemplate is required');
    return;
  }

  try {
    console.log(`[Sidebar] Adding formula column "${columnName}" with template: ${formulaTemplate}`);
    const response = await sendToContentScript('ADD_FORMULA_COLUMN', {
      columnName: columnName || 'Итого',
      formulaTemplate: formulaTemplate,
      rowCount: rowCount || 100,
      targetColumn: targetColumn || null
    });
    console.log(`[Sidebar] Formula column added:`, response);

    // Save snapshot AFTER adding column, so we know which column was added
    if (response?.column) {
      await saveSheetSnapshot('Добавление столбца с формулой', { addedColumn: response.column });
    }

    return response;
  } catch (error) {
    console.error('[Sidebar] Error adding formula column:', error);
    addAIMessage({
      type: 'error',
      text: `Ошибка добавления столбца с формулой: ${error.message}`
    });
  }
}

async function convertColumnToNumbersInSheet(rule) {
  if (!rule) {
    console.error('[Sidebar] Convert to numbers error: rule is required');
    throw new Error('Rule is required for convert to numbers');
  }

  try {
    console.log('[Sidebar] Sending CONVERT_TO_NUMBERS to content script:', rule);
    const response = await sendToContentScript('CONVERT_TO_NUMBERS', {
      columnIndex: rule.column_index,
      columnName: rule.column_name,
      rowCount: rule.row_count
    });
    console.log(`[Sidebar] Column "${rule.column_name}" converted to numbers:`, response);
    return response;
  } catch (error) {
    console.error('[Sidebar] Error converting to numbers:', error);
    throw error;
  }
}

async function setDataValidationInSheet(rule) {
  if (!rule) {
    console.error('[Sidebar] Data validation error: rule is required');
    return;
  }

  try {
    await sendToContentScript('SET_DATA_VALIDATION', {
      rule: rule
    });
    console.log(`[Sidebar] Data validation set for column "${rule.column_name}"`);
  } catch (error) {
    console.error('[Sidebar] Error setting data validation:', error);
  }
}

window.insertFormula = async function(formula) {
  try {
    await sendToContentScript('INSERT_FORMULA', { formula: formula });
    console.log('[Sidebar] Formula inserted:', formula);
  } catch (error) {
    console.error('[Sidebar] Error inserting formula:', error);
    // Fallback to old method
    window.parent.postMessage({
      type: 'INSERT_FORMULA',
      formula: formula
    }, '*');
  }
};

window.insertTable = async function() {
  const structuredData = window.lastStructuredData;
  if (!structuredData) {
    addAIMessage({
      type: 'error',
      text: 'Нет данных для вставки. Сначала запросите создание таблицы.'
    });
    return;
  }

  try {
    await saveSheetSnapshot('Вставка таблицы');
    // Note: content script expects camelCase 'structuredData'
    const result = await sendToContentScript('CREATE_TABLE_AND_CHART', {
      structuredData: structuredData
    });
    console.log('[Sidebar] Table inserted:', result);

    if (result.success) {
      addAIMessage({
        type: 'analysis',
        text: result.message || `Таблица создана`
      });
    } else {
      addAIMessage({
        type: 'error',
        text: result.message || 'Не удалось создать таблицу'
      });
    }
  } catch (error) {
    console.error('[Sidebar] Error inserting table:', error);
    addAIMessage({
      type: 'error',
      text: 'Ошибка при создании таблицы: ' + error.message
    });
  }
};

window.insertPivotTable = async function() {
  const pivotData = window.lastPivotData;
  if (!pivotData) {
    addAIMessage({
      type: 'error',
      text: 'Нет данных для вставки. Сначала запросите создание сводной таблицы.'
    });
    return;
  }

  // Prompt for sheet name - pivot tables should go to NEW sheet, not overwrite current!
  const sheetName = prompt('Введите имя нового листа для сводной таблицы:', 'Сводная таблица');
  if (!sheetName) {
    return; // User cancelled
  }

  try {
    // Create a NEW sheet with pivot data (not overwrite current!)
    const result = await sendToContentScript('CREATE_NEW_SHEET_WITH_DATA', {
      sheetName: sheetName,
      structuredData: pivotData
    });
    console.log('[Sidebar] Pivot table inserted to new sheet:', result);

    if (result.success) {
      addAIMessage({
        type: 'analysis',
        text: result.message || `Сводная таблица создана на листе "${sheetName}"`
      });
    } else {
      addAIMessage({
        type: 'error',
        text: result.message || 'Не удалось создать сводную таблицу'
      });
    }
  } catch (error) {
    console.error('[Sidebar] Error inserting pivot table:', error);
    addAIMessage({
      type: 'error',
      text: 'Ошибка при создании сводной таблицы: ' + error.message
    });
  }
};

window.insertCleanedData = async function() {
  const cleanedData = window.lastCleanedData;
  if (!cleanedData) {
    addAIMessage({
      type: 'error',
      text: 'Нет данных для вставки. Сначала запросите очистку данных.'
    });
    return;
  }

  // Prompt for sheet name
  const sheetName = prompt('Введите имя нового листа:', 'Очищенные данные');
  if (!sheetName) {
    return; // User cancelled
  }

  try {
    await saveSheetSnapshot('Вставка очищенных данных');
    // Create a new sheet with cleaned data
    const result = await sendToContentScript('CREATE_TABLE_AND_CHART', {
      structuredData: cleanedData,
      sheetTitle: sheetName
    });
    console.log('[Sidebar] Cleaned data inserted:', result);

    if (result.success) {
      addAIMessage({
        type: 'analysis',
        text: result.message || 'Новый лист с очищенными данными создан'
      });
    } else {
      addAIMessage({
        type: 'error',
        text: result.message || 'Не удалось создать лист с данными'
      });
    }
  } catch (error) {
    console.error('[Sidebar] Error inserting cleaned data:', error);
    addAIMessage({
      type: 'error',
      text: 'Ошибка при создании листа: ' + error.message
    });
  }
};

window.overwriteWithCleanedData = async function() {
  const cleanedData = window.lastCleanedData;
  if (!cleanedData) {
    addAIMessage({
      type: 'error',
      text: 'Нет данных для замены. Сначала запросите очистку данных.'
    });
    return;
  }

  try {
    await saveSheetSnapshot('Замена данных');
    // Overwrite current sheet with cleaned data
    const result = await sendToContentScript('OVERWRITE_SHEET_DATA', {
      cleanedData: cleanedData
    });
    console.log('[Sidebar] Data overwritten:', result);

    if (result.success) {
      addAIMessage({
        type: 'analysis',
        text: result.message || 'Данные успешно заменены'
      });
    } else {
      addAIMessage({
        type: 'error',
        text: result.message || 'Не удалось заменить данные'
      });
    }
  } catch (error) {
    console.error('[Sidebar] Error overwriting data:', error);
    addAIMessage({
      type: 'error',
      text: 'Ошибка при замене данных: ' + error.message
    });
  }
};

window.applySplitData = async function() {
  const splitData = window.lastSplitData;
  if (!splitData) {
    addAIMessage({
      type: 'error',
      text: 'Нет данных для вставки. Сначала запросите разбиение данных.'
    });
    return;
  }

  try {
    await saveSheetSnapshot('Разбиение данных');
    // Overwrite current sheet with split data
    const result = await sendToContentScript('OVERWRITE_SHEET_DATA', {
      cleanedData: splitData
    });
    console.log('[Sidebar] Split data applied:', result);

    if (result.success) {
      addAIMessage({
        type: 'analysis',
        text: result.message || 'Данные успешно разбиты по ячейкам'
      });
    } else {
      addAIMessage({
        type: 'error',
        text: result.message || 'Не удалось применить разбитые данные'
      });
    }
  } catch (error) {
    console.error('[Sidebar] Error applying split data:', error);
    addAIMessage({
      type: 'error',
      text: 'Ошибка при применении данных: ' + error.message
    });
  }
};

window.insertFilteredData = async function() {
  const filteredData = window.lastFilteredData;
  if (!filteredData) {
    addAIMessage({
      type: 'error',
      text: 'Нет данных для вставки. Сначала выполните фильтрацию.'
    });
    return;
  }

  try {
    await saveSheetSnapshot('Вставка отфильтрованных данных');
    // Create a new sheet with filtered data
    const result = await sendToContentScript('CREATE_TABLE_AND_CHART', {
      structuredData: filteredData,
      sheetTitle: 'Отфильтрованные данные'
    });
    console.log('[Sidebar] Filtered data inserted:', result);

    if (result.success) {
      addAIMessage({
        type: 'analysis',
        text: result.message || 'Новый лист с отфильтрованными данными создан'
      });
    } else {
      addAIMessage({
        type: 'error',
        text: result.message || 'Не удалось создать лист с данными'
      });
    }
  } catch (error) {
    console.error('[Sidebar] Error inserting filtered data:', error);
    addAIMessage({
      type: 'error',
      text: 'Ошибка при создании листа: ' + error.message
    });
  }
};

window.highlightFilteredRows = async function() {
  const filteredData = window.lastFilteredData;
  if (!filteredData || !filteredData.rows) {
    addAIMessage({
      type: 'error',
      text: 'Нет данных для выделения. Сначала выполните фильтрацию.'
    });
    return;
  }

  try {
    // Get row indices from filtered data
    // Note: rows are 1-indexed in sheets, and we skip header
    const rowIndices = filteredData.rows.map((_, idx) => idx + 2); // +2 because 1-indexed and skip header

    const result = await sendToContentScript('HIGHLIGHT_ROWS', {
      rows: rowIndices.slice(0, 100), // Limit to 100 rows for performance
      color: 'yellow'
    });
    console.log('[Sidebar] Rows highlighted:', result);

    if (result.success) {
      addAIMessage({
        type: 'analysis',
        text: result.message || `Выделено ${Math.min(rowIndices.length, 100)} строк`
      });
    } else {
      addAIMessage({
        type: 'error',
        text: result.message || 'Не удалось выделить строки'
      });
    }
  } catch (error) {
    console.error('[Sidebar] Error highlighting rows:', error);
    addAIMessage({
      type: 'error',
      text: 'Ошибка при выделении строк: ' + error.message
    });
  }
};

window.copyToClipboard = async function(text) {
  try {
    // Try modern Clipboard API first
    await navigator.clipboard.writeText(text);
    showCopySuccess();
  } catch (e) {
    // Fallback for iframe/extension context where Clipboard API is blocked
    console.log('[Sidebar] Clipboard API blocked, using fallback');
    try {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-9999px';
      textArea.style.top = '0';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const success = document.execCommand('copy');
      document.body.removeChild(textArea);
      if (success) {
        showCopySuccess();
      } else {
        console.error('Copy fallback failed');
      }
    } catch (fallbackError) {
      console.error('Copy failed completely:', fallbackError);
    }
  }
};

function showCopySuccess() {
  // Brief visual feedback
  const btn = document.querySelector('.copy-formula-btn');
  if (btn) {
    const originalText = btn.textContent;
    btn.textContent = '✓ Скопировано!';
    btn.style.background = 'var(--success)';
    setTimeout(() => {
      btn.textContent = originalText;
      btn.style.background = '';
    }, 1500);
  }
}

// ============================================
// UTILITIES
// ============================================
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ============================================
// POSTMESSAGE BRIDGE
// ============================================
window.addEventListener('message', (event) => {
  const { type, data } = event.data || {};
  
  switch (type) {
    case 'SHEET_DATA':
      // Handled in getSheetData
      break;
    case 'AUTH_STATUS':
      if (data && data.authenticated) {
        state.isAuthenticated = true;
        saveState();
        checkAuthentication();
      }
      break;
  }
});

// Emulate google.script.run for Apps Script compatibility
window.google = {
  script: {
    run: {
      withSuccessHandler: function(callback) {
        return {
          withFailureHandler: function(errorCallback) {
            return {
              processRequest: function(query) {
                callAPI(query, null)
                  .then(callback)
                  .catch(errorCallback);
              }
            };
          }
        };
      }
    }
  }
};
