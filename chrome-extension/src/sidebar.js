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
  isLoading: false
};

// ============================================
// DOM ELEMENTS
// ============================================
const elements = {
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
  logoutBtn: document.getElementById('logoutBtn')
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', init);

function init() {
  loadState();
  setupEventListeners();
  applyTheme();
  checkAuthentication();
}

function loadState() {
  try {
    const savedState = localStorage.getItem('sheetgpt_state');
    if (savedState) {
      const parsed = JSON.parse(savedState);
      Object.assign(state, parsed);
    }
    
    // Load chat history separately
    const savedHistory = localStorage.getItem('sheetgpt_history');
    if (savedHistory) {
      state.chatHistory = JSON.parse(savedHistory);
    }
    
    // Check if it's a new day - reset usage
    const lastUsageDate = localStorage.getItem('sheetgpt_usage_date');
    const today = new Date().toDateString();
    if (lastUsageDate !== today) {
      state.usageCount = 0;
      localStorage.setItem('sheetgpt_usage_date', today);
    }
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
      customContext: state.customContext,
      usageCount: state.usageCount,
      usageLimit: state.usageLimit
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
          // Update usage limit based on subscription
          const isPremium = ['premium', 'pro'].includes(data.subscription_tier) ||
                            ['premium', 'pro'].includes(data.plan);
          state.usageLimit = isPremium ? CONFIG.PRO_DAILY_LIMIT : CONFIG.FREE_DAILY_LIMIT;
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
        // Check for premium/pro subscription
        const isPremium = ['premium', 'pro'].includes(data.subscription_tier) ||
                          ['premium', 'pro'].includes(data.plan) ||
                          ['premium', 'pro'].includes(data.subscription_type);
        state.usageLimit = isPremium ? CONFIG.PRO_DAILY_LIMIT : CONFIG.FREE_DAILY_LIMIT;

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
  const plan = state.user.plan || 'free';
  const isPro = plan === 'pro';
  
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
  if (state.chatHistory.length === 0) {
    elements.historyList.innerHTML = '<li class="dropdown-empty">История пуста</li>';
    return;
  }
  
  elements.historyList.innerHTML = state.chatHistory.slice(0, 10).map((item, index) => `
    <li class="dropdown-item" data-index="${index}">
      <div class="dropdown-item-title">${escapeHtml(item.query.substring(0, 40))}${item.query.length > 40 ? '...' : ''}</div>
      <div class="dropdown-item-meta">${formatTime(item.timestamp)}</div>
    </li>
  `).join('');
  
  // Add click handlers
  elements.historyList.querySelectorAll('.dropdown-item').forEach(item => {
    item.addEventListener('click', () => {
      const index = parseInt(item.dataset.index);
      const historyItem = state.chatHistory[index];
      if (historyItem) {
        elements.messageInput.value = historyItem.query;
        handleInputChange();
        elements.historyDropdown.classList.remove('show');
      }
    });
  });
}

function addToHistory(query) {
  state.chatHistory.unshift({
    query,
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
  updateUserUI();
  closeSettings();
}

function updateCharCounter() {
  const count = elements.customContextInput.value.length;
  elements.charCount.textContent = count;
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
  if (state.user.plan !== 'pro' && state.usageCount >= state.usageLimit) {
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
  
  // Add to history
  addToHistory(query);
  
  // Show loading
  state.isLoading = true;
  elements.sendBtn.disabled = true;
  const loadingEl = addLoadingIndicator();
  
  try {
    // Use PROCESS_QUERY action via content.js (it handles sheet data and API call)
    const result = await sendToContentScript('PROCESS_QUERY', { query });

    // Remove loading
    loadingEl.remove();

    // Transform and display AI response
    const response = transformAPIResponse(result);
    addAIMessage(response);

    // Update usage
    updateUsage();

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
  
  if (response.type === 'error') {
    content = `
      <div class="content-box error">${escapeHtml(response.text)}</div>
    `;
  } else if (response.type === 'formula') {
    content = `
      <div class="response-badge formula">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 4h16v16H4z"/><path d="M4 10h16"/><path d="M10 4v16"/>
        </svg>
        Формула
      </div>
      <div class="formula-code">${escapeHtml(response.formula)}</div>
      ${response.explanation ? `<p>${escapeHtml(response.explanation)}</p>` : ''}
      <div class="action-buttons">
        <button class="action-btn" onclick="insertFormula('${escapeHtml(response.formula)}')">Вставить</button>
        <button class="action-btn secondary" onclick="copyToClipboard('${escapeHtml(response.formula)}')">Копировать</button>
      </div>
    `;
  } else if (response.type === 'analysis') {
    content = `
      <div class="response-badge analysis">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4"/>
        </svg>
        Анализ
      </div>
      ${response.title ? `<div class="section-title">${escapeHtml(response.title)}</div>` : ''}
      ${response.items ? `
        <ul class="list-items">
          ${response.items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
        </ul>
      ` : ''}
      ${response.text ? `<p>${escapeHtml(response.text)}</p>` : ''}
      ${response.summary ? `<div class="content-box info">${escapeHtml(response.summary)}</div>` : ''}
    `;
  } else if (response.type === 'table') {
    content = `
      <div class="response-badge formula">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 3v18"/>
        </svg>
        Таблица
      </div>
      <p>${escapeHtml(response.text || 'Таблица готова к вставке')}</p>
      <div class="action-buttons">
        <button class="action-btn" onclick="insertTable()">Вставить таблицу</button>
      </div>
    `;
  } else if (response.type === 'highlight') {
    content = `
      <div class="response-badge analysis">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2z"/>
        </svg>
        Выделение
      </div>
      <div class="content-box success">${escapeHtml(response.text || 'Строки успешно выделены')}</div>
    `;
  } else {
    content = `<p>${escapeHtml(response.text || 'Готово')}</p>`;
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
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span class="loading-text">Анализирую данные...</span>
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

    // Timeout after 30 seconds
    const timeout = setTimeout(() => {
      window.removeEventListener('message', handler);
      reject(new Error('Таймаут ожидания ответа. Перезагрузите страницу.'));
    }, 30000);

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

async function callAPI(query, sheetData) {
  // Format payload for /api/v1/formula endpoint
  const payload = {
    query: query,
    column_names: sheetData?.headers || [],
    sheet_data: sheetData?.rows || [],
    custom_context: state.customContext || ''
  };

  console.log('[API] Sending request:', payload);

  let lastError;

  for (let attempt = 0; attempt < CONFIG.MAX_RETRIES; attempt++) {
    try {
      const response = await fetch(`${CONFIG.API_URL}/api/v1/formula`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
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
      return transformAPIResponse(result);

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

// Transform API response to UI format
function transformAPIResponse(apiResponse) {
  // If response has formula
  if (apiResponse.formula) {
    return {
      type: 'formula',
      formula: apiResponse.formula,
      explanation: apiResponse.explanation || apiResponse.summary || ''
    };
  }

  // If response has highlight_rows
  if (apiResponse.highlight_rows && apiResponse.highlight_rows.length > 0) {
    return {
      type: 'highlight',
      text: `Найдено ${apiResponse.highlighted_count || apiResponse.highlight_rows.length} строк`,
      rows: apiResponse.highlight_rows
    };
  }

  // If response has structured_data (table)
  if (apiResponse.structured_data) {
    return {
      type: 'table',
      text: apiResponse.summary || 'Данные обработаны',
      data: apiResponse.structured_data
    };
  }

  // Default analysis response
  return {
    type: 'analysis',
    title: apiResponse.response_type || 'Результат',
    text: apiResponse.summary || apiResponse.explanation || apiResponse.message || 'Запрос обработан'
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
window.insertFormula = function(formula) {
  window.parent.postMessage({
    type: 'INSERT_FORMULA',
    formula: formula
  }, '*');
};

window.insertTable = function() {
  window.parent.postMessage({
    type: 'INSERT_TABLE'
  }, '*');
};

window.copyToClipboard = async function(text) {
  try {
    await navigator.clipboard.writeText(text);
    // Could show a toast notification here
  } catch (e) {
    console.error('Copy failed:', e);
  }
};

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
