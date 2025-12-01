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
// TEXT FORMATTING UTILITIES (v9.1.0)
// ============================================

function cleanResponseText(text) {
  if (!text) return '';
  // Remove emoji
  let cleaned = text.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]/gu, '');
  // Remove markdown bold/italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '$1');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '$1');
  cleaned = cleaned.replace(/__([^_]+)__/g, '$1');
  cleaned = cleaned.replace(/_([^_]+)_/g, '$1');
  // Clean whitespace
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  return cleaned;
}

function parseResponseContent(text) {
  if (!text) return { paragraphs: [], metrics: [], items: [] };
  const cleaned = cleanResponseText(text);
  const result = { paragraphs: [], metrics: [], items: [] };

  // Split by bullet points
  const lines = cleaned.split(/[•·\-]\s+/).filter(l => l.trim());

  for (const line of lines) {
    const trimmed = line.trim();
    // Check if metric (contains : and number)
    const metricMatch = trimmed.match(/^([^:]+):\s*([0-9.,\s]+(?:руб|₽|%|шт)?\.?)\s*(?:\(([^)]+)\))?/i);
    if (metricMatch) {
      result.metrics.push({
        label: metricMatch[1].trim(),
        value: metricMatch[2].trim(),
        subtext: metricMatch[3] ? metricMatch[3].trim() : null
      });
    } else if (trimmed.length > 0) {
      result.items.push(trimmed);
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
          // Update usage limit based on subscription
          const isPremium = ['premium', 'pro', 'unlimited'].includes(data.subscription_tier) ||
                            ['premium', 'pro', 'unlimited'].includes(data.plan);
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
        // Check for premium/pro/unlimited subscription
        const isPremium = ['premium', 'pro', 'unlimited'].includes(data.subscription_tier) ||
                          ['premium', 'pro', 'unlimited'].includes(data.plan) ||
                          ['premium', 'pro', 'unlimited'].includes(data.subscription_type);
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

    const result = await sendToContentScript('PROCESS_QUERY', { query, history: conversationHistory });

    // Remove loading
    loadingEl.remove();

    // Transform and display AI response
    const response = transformAPIResponse(result);
    addAIMessage(response);

    // Update usage
    updateUsage();

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
    const parsed = parseResponseContent(response.text);

    content = `
      <div class="response-type">
        <svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        Анализ
      </div>
    `;

    // Render metrics as data block
    if (parsed.metrics.length > 0) {
      content += `<div class="data-block">`;
      for (const metric of parsed.metrics) {
        content += `
          <div class="data-row">
            <span class="data-label">${escapeHtml(metric.label)}</span>
            <span class="data-value">${escapeHtml(metric.value)}${metric.subtext ? ` <small style="color: var(--text-muted); font-weight: 400;">(${escapeHtml(metric.subtext)})</small>` : ''}</span>
          </div>
        `;
      }
      content += `</div>`;
    }

    // Render items as paragraphs
    if (parsed.items.length > 0) {
      content += `<div class="response-content">`;
      for (const item of parsed.items) {
        content += `<p>${escapeHtml(item)}</p>`;
      }
      content += `</div>`;
    }

    // Render paragraphs
    if (parsed.paragraphs.length > 0) {
      content += `<div class="response-content">`;
      for (const para of parsed.paragraphs) {
        content += `<p>${escapeHtml(para)}</p>`;
      }
      content += `</div>`;
    }

    // Fallback
    if (parsed.metrics.length === 0 && parsed.items.length === 0 && parsed.paragraphs.length === 0) {
      content += `<div class="response-content"><p>${escapeHtml(cleanResponseText(response.text))}</p></div>`;
    }
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

  // CSV split
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

async function callAPI(query, sheetData, history = []) {
  // Format payload for /api/v1/formula endpoint
  const payload = {
    query: query,
    column_names: sheetData?.headers || [],
    sheet_data: sheetData?.rows || [],
    custom_context: state.customContext || '',
    history: history
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
function transformAPIResponse(apiResponse) {
  console.log('[Sidebar] transformAPIResponse received:', apiResponse);
  console.log('[Sidebar] action_type:', apiResponse.action_type);
  console.log('[Sidebar] chart_spec:', apiResponse.chart_spec);

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
    // Trigger highlight action
    highlightRowsInSheet(apiResponse.highlight_rows);
    return {
      type: 'highlight',
      text: `Выделено ${apiResponse.highlighted_count || apiResponse.highlight_rows.length} строк`,
      rows: apiResponse.highlight_rows
    };
  }

  // If response has structured_data (table)
  if (apiResponse.structured_data) {
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
async function highlightRowsInSheet(rows) {
  if (!rows || rows.length === 0) return;

  try {
    await sendToContentScript('HIGHLIGHT_ROWS', { rows: rows });
    console.log('[Sidebar] Rows highlighted:', rows);
  } catch (error) {
    console.error('[Sidebar] Error highlighting rows:', error);
  }
}

async function sortRangeInSheet(columnIndex, sortOrder) {
  if (columnIndex === undefined || columnIndex === null) {
    console.error('[Sidebar] Sort error: columnIndex is required');
    return;
  }

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

  try {
    // Create a new sheet with pivot data
    const result = await sendToContentScript('CREATE_TABLE_AND_CHART', {
      structuredData: pivotData
    });
    console.log('[Sidebar] Pivot table inserted:', result);

    if (result.success) {
      addAIMessage({
        type: 'analysis',
        text: result.message || 'Сводная таблица создана'
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
