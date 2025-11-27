// ===== DEBUG: SCRIPT LOADED =====
console.log('🚀🚀🚀 SIDEBAR.JS IS LOADING! 🚀🚀🚀');

// ===== LICENSE VALIDATION =====
const LICENSE_API_URL = 'https://sheetgpt-production.up.railway.app/api/v1/telegram/license/validate';
const LICENSE_STATUS_URL = 'https://sheetgpt-production.up.railway.app/api/v1/telegram/license';
// Note: LICENSE_STORAGE_KEY and USER_DATA_STORAGE_KEY are defined in settings-menu.js
// Use them directly since settings-menu.js loads first

// Check if license is valid on startup
async function checkLicense() {
  const savedLicense = localStorage.getItem(LICENSE_STORAGE_KEY);
  console.log('[Sidebar] Checking license:', savedLicense ? 'found' : 'not found');

  if (savedLicense) {
    // Validate saved license
    const isValid = await validateLicense(savedLicense, true);
    if (isValid) {
      console.log('[Sidebar] License valid, hiding activation screen');
      hideLicenseOverlay();
      return true;
    } else {
      console.log('[Sidebar] Saved license invalid, clearing');
      localStorage.removeItem(LICENSE_STORAGE_KEY);
    }
  }

  console.log('[Sidebar] No valid license, showing activation screen');
  showLicenseOverlay();
  return false;
}

// Validate license key via API
async function validateLicense(licenseKey, silent = false) {
  try {
    const cleanKey = licenseKey.trim().toUpperCase();
    console.log('[Sidebar] Validating license:', cleanKey);

    const response = await fetch(`${LICENSE_API_URL}/${encodeURIComponent(cleanKey)}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });

    console.log('[Sidebar] License API response status:', response.status);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    console.log('[Sidebar] License API response:', data);

    // API returns {success: true/false, license_key, message, username, etc.} with status 200
    if (data.success === true && data.license_key) {
      // Save valid license
      localStorage.setItem(LICENSE_STORAGE_KEY, data.license_key);

      // Save user data for settings menu
      const userData = {
        telegram_user_id: data.telegram_user_id,
        username: data.username,
        first_name: data.first_name,
        subscription_tier: data.subscription_tier || 'free',
        queries_used_today: data.queries_used_today || 0,
        queries_limit: data.queries_limit || 10,
        total_queries: data.total_queries || 0
      };
      localStorage.setItem(USER_DATA_STORAGE_KEY, JSON.stringify(userData));
      console.log('[Sidebar] User data saved:', userData);

      // Update settings menu if available
      if (window.SheetGPTSettings) {
        window.SheetGPTSettings.setUserData(userData);
      }

      return true;
    }

    // License not found or invalid - API returns success: false
    console.log('[Sidebar] License validation failed:', data.message);
    return false;
  } catch (error) {
    console.error('[Sidebar] License validation error:', error);
    if (!silent) {
      throw error;
    }
    return false;
  }
}

// Show license activation overlay
function showLicenseOverlay() {
  const overlay = document.getElementById('licenseOverlay');
  if (overlay) {
    overlay.classList.remove('hidden');
  }
}

// Hide license activation overlay
function hideLicenseOverlay() {
  const overlay = document.getElementById('licenseOverlay');
  if (overlay) {
    overlay.classList.add('hidden');
  }
}

// Format license key input (add dashes)
function formatLicenseInput(input) {
  // Remove non-alphanumeric characters
  let value = input.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase();

  // Add dashes every 4 characters
  let formatted = '';
  for (let i = 0; i < value.length && i < 16; i++) {
    if (i > 0 && i % 4 === 0) {
      formatted += '-';
    }
    formatted += value[i];
  }

  input.value = formatted;
}

// Handle license activation
async function handleActivation() {
  console.log('[Sidebar] 🔥 handleActivation() called!');

  const input = document.getElementById('licenseInput');
  const btn = document.getElementById('activateBtn');
  const errorDiv = document.getElementById('licenseError');

  console.log('[Sidebar] Elements found:', { input: !!input, btn: !!btn, errorDiv: !!errorDiv });

  if (!input || !btn) {
    console.error('[Sidebar] ❌ Required elements not found!');
    return;
  }

  const licenseKey = input.value.trim();

  // Validate format
  if (!/^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/i.test(licenseKey)) {
    input.classList.add('error');
    errorDiv.textContent = 'Неверный формат ключа';
    errorDiv.classList.add('show');
    setTimeout(() => {
      input.classList.remove('error');
    }, 300);
    return;
  }

  // Disable button during validation
  btn.disabled = true;
  btn.textContent = 'Проверка...';
  errorDiv.classList.remove('show');
  input.classList.remove('error', 'success');

  try {
    const isValid = await validateLicense(licenseKey, false);

    if (isValid) {
      input.classList.add('success');
      btn.textContent = 'Успешно!';
      console.log('[Sidebar] License valid, hiding overlay in 500ms...');

      // Hide overlay after short delay
      setTimeout(() => {
        console.log('[Sidebar] Hiding license overlay now');
        const overlay = document.getElementById('licenseOverlay');
        if (overlay) {
          overlay.style.display = 'none';
          overlay.classList.add('hidden');
          console.log('[Sidebar] ✅ Overlay hidden');
        } else {
          console.error('[Sidebar] ❌ licenseOverlay element not found!');
        }
      }, 500);
    } else {
      input.classList.add('error');
      errorDiv.textContent = 'Лицензионный ключ не найден';
      errorDiv.classList.add('show');
      btn.textContent = 'Активировать';
      btn.disabled = false;

      setTimeout(() => {
        input.classList.remove('error');
      }, 300);
    }
  } catch (error) {
    console.error('[Sidebar] Activation error:', error);
    input.classList.add('error');
    errorDiv.textContent = 'Ошибка проверки: ' + error.message;
    errorDiv.classList.add('show');
    btn.textContent = 'Активировать';
    btn.disabled = false;

    setTimeout(() => {
      input.classList.remove('error');
    }, 300);
  }
}

// Initialize license system when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Sidebar] ✅ DOM loaded, initializing license system');

  // Check license on load
  checkLicense();

  // Setup license input formatting
  const licenseInput = document.getElementById('licenseInput');
  console.log('[Sidebar] licenseInput element:', licenseInput);

  if (licenseInput) {
    licenseInput.addEventListener('input', (e) => formatLicenseInput(e.target));
    licenseInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        console.log('[Sidebar] Enter pressed in license input');
        handleActivation();
      }
    });
  }

  // Setup activate button
  const activateBtn = document.getElementById('activateBtn');
  console.log('[Sidebar] activateBtn element:', activateBtn);

  if (activateBtn) {
    activateBtn.addEventListener('click', () => {
      console.log('[Sidebar] 🖱️ Activate button clicked!');
      handleActivation();
    });
    console.log('[Sidebar] ✅ Click handler attached to activateBtn');
  } else {
    console.error('[Sidebar] ❌ activateBtn not found!');
  }
});

console.log('[Sidebar] 📜 sidebar.js loaded');

// ===== DEBUG MESSAGE HANDLER =====
window.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'DEBUG_ACTIVATE') {
    console.log('[Sidebar] 🔧 DEBUG_ACTIVATE received, key:', event.data.key);
    const input = document.getElementById('licenseInput');
    if (input) {
      input.value = event.data.key || 'TEST-TEST-TEST-TEST';
      console.log('[Sidebar] 🔧 Input value set, calling handleActivation...');
      handleActivation();
    } else {
      console.error('[Sidebar] 🔧 licenseInput not found!');
    }
  }
});

// ===== POSTMESSAGE BRIDGE FOR CHROME EXTENSION =====
console.log('[Sidebar] Initializing event listeners...');

let messageIdCounter = 0;
const pendingMessages = new Map();

// ===== RETRY CONFIGURATION =====
const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000,      // 1 second
  maxDelay: 10000,      // 10 seconds max
  backoffMultiplier: 2,
  timeout: 45000,       // 45 seconds per attempt (increased from 30)
  retryableErrors: [
    'Request timeout',
    'Network error',
    'Failed to fetch',
    'ERR_NETWORK',
    'ERR_CONNECTION',
    'ETIMEDOUT',
    '502',
    '503',
    '504',
    'temporarily unavailable'
  ]
};

// Check if error is retryable
function isRetryableError(error) {
  const errorMessage = error?.message?.toLowerCase() || String(error).toLowerCase();
  return RETRY_CONFIG.retryableErrors.some(retryable =>
    errorMessage.includes(retryable.toLowerCase())
  );
}

// Calculate delay with exponential backoff + jitter
function getRetryDelay(attempt) {
  const exponentialDelay = RETRY_CONFIG.baseDelay * Math.pow(RETRY_CONFIG.backoffMultiplier, attempt);
  const jitter = Math.random() * 0.3 * exponentialDelay; // 0-30% jitter
  return Math.min(exponentialDelay + jitter, RETRY_CONFIG.maxDelay);
}

// Update loading indicator with retry info
function updateLoadingStatus(message) {
  const loadingText = document.querySelector('#loading .loading-text');
  if (loadingText) {
    loadingText.textContent = message;
  }
}

// Single attempt to send message
function sendMessageAttempt(action, data, messageId) {
  return new Promise((resolve, reject) => {
    pendingMessages.set(messageId, { resolve, reject });

    const message = { action, data, messageId };
    console.log('[Sidebar] Sending message to parent:', message);
    window.parent.postMessage(message, '*');

    // Timeout for this attempt
    setTimeout(() => {
      if (pendingMessages.has(messageId)) {
        pendingMessages.delete(messageId);
        reject(new Error('Request timeout'));
      }
    }, RETRY_CONFIG.timeout);
  });
}

// Send message to content script via postMessage with retry logic
async function sendMessageToContentScript(action, data) {
  console.log('[Sidebar] sendMessageToContentScript called with:', { action, data });

  let lastError;

  for (let attempt = 0; attempt <= RETRY_CONFIG.maxRetries; attempt++) {
    const messageId = ++messageIdCounter;

    try {
      if (attempt > 0) {
        const delay = getRetryDelay(attempt - 1);
        console.log(`[Sidebar] Retry attempt ${attempt}/${RETRY_CONFIG.maxRetries} after ${Math.round(delay)}ms delay`);
        updateLoadingStatus(`Повторная попытка ${attempt}/${RETRY_CONFIG.maxRetries}...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }

      const result = await sendMessageAttempt(action, data, messageId);

      if (attempt > 0) {
        console.log(`[Sidebar] ✅ Retry successful on attempt ${attempt + 1}`);
        updateLoadingStatus('Думаю...');
      }

      return result;

    } catch (error) {
      lastError = error;
      console.warn(`[Sidebar] Attempt ${attempt + 1} failed:`, error.message);

      // Check if we should retry
      if (attempt < RETRY_CONFIG.maxRetries && isRetryableError(error)) {
        console.log(`[Sidebar] Error is retryable, will retry...`);
        continue;
      }

      // Non-retryable error or max retries reached
      break;
    }
  }

  // All retries exhausted
  console.error(`[Sidebar] ❌ All ${RETRY_CONFIG.maxRetries + 1} attempts failed`);
  throw lastError;
}

// Listen for responses from content script
window.addEventListener('message', (event) => {
  console.log('[Sidebar] Received message from parent:', event.data);

  const { messageId, success, result, error } = event.data;

  if (!messageId || !pendingMessages.has(messageId)) {
    console.log('[Sidebar] Ignoring message - no matching messageId');
    return;
  }

  const { resolve, reject } = pendingMessages.get(messageId);
  pendingMessages.delete(messageId);

  if (success) {
    console.log('[Sidebar] ✅ Request successful:', result);
    resolve(result);
  } else {
    console.error('[Sidebar] ❌ Request failed:', error);
    reject(new Error(error));
  }
});

// Helper: Convert camelCase to SCREAMING_SNAKE_CASE
function camelToScreamingSnake(str) {
  return str.replace(/[A-Z]/g, letter => `_${letter}`).toUpperCase();
}

// Helper: Convert function arguments to data object
function convertArgsToData(method, args) {
  switch (method) {
    case 'processQuery':
      return { query: args[0] };
    case 'getCustomContext':
      return {};
    case 'saveCustomContext':
      return { context: args[0] };
    case 'insertFormula':
      return { formula: args[0], targetCell: args[1] };
    case 'createTableAndChart':
      // v9.0.2: Deep clone to ensure data is properly serialized
      const data = args[0];
      console.log('[Sidebar] convertArgsToData createTableAndChart input:', data);
      console.log('[Sidebar] headers:', data?.headers);
      console.log('[Sidebar] rows count:', data?.rows?.length);
      // Force deep clone via JSON to ensure proper serialization
      const cloned = JSON.parse(JSON.stringify(data));
      console.log('[Sidebar] cloned data rows count:', cloned?.rows?.length);
      return { structuredData: cloned };
    case 'replaceDataInCurrentSheet':
      return { structuredData: JSON.parse(JSON.stringify(args[0])) };
    case 'highlightRows':
      return { rows: args[0], color: args[1] };
    default:
      return args[0] || {};
  }
}

// ===== GOOGLE.SCRIPT.RUN EMULATION =====
const google = {
  script: {
    run: {
      withSuccessHandler: function(successCallback) {
        return {
          withFailureHandler: function(failureCallback) {
            return new Proxy({}, {
              get: function(target, method) {
                return async function(...args) {
                  try {
                    console.log('[Sidebar] Calling google.script.run.' + method, args);
                    const action = camelToScreamingSnake(method);
                    const result = await sendMessageToContentScript(
                      action,
                      convertArgsToData(method, args)
                    );
                    if (successCallback) {
                      successCallback(result);
                    }
                  } catch (error) {
                    console.error('[Sidebar] Error in google.script.run.' + method, error);
                    if (failureCallback) {
                      failureCallback(error);
                    }
                  }
                };
              }
            });
          }
        };
      }
    }
  }
};

// Send READY message to content script
window.parent.postMessage({ type: 'SHEETGPT_READY' }, '*');
console.log('[Sidebar] ✅ READY message sent to parent');

// ===== ORIGINAL APPS SCRIPT CODE =====
let chatHistory = [];
let isProcessing = false;

    // Initialize
    document.getElementById('messageInput').addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = (this.scrollHeight) + 'px';

      const sendBtn = document.getElementById('sendBtn');
      sendBtn.disabled = !this.value.trim() || isProcessing;
    });

    // Character counter
    const customContextInput = document.getElementById('customContextInput');
    if (customContextInput) {
      customContextInput.addEventListener('input', function() {
        document.getElementById('charCount').textContent = this.value.length;
      });
    }

    function handleKeyPress(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    }

    function useExample(query) {
      document.getElementById('messageInput').value = query;
      document.getElementById('sendBtn').disabled = false;
      sendMessage();
    }

    function sendMessage() {
      const input = document.getElementById('messageInput');
      const message = input.value.trim();

      if (!message || isProcessing) return;

      // Check usage limit before sending query
      if (window.SheetGPTSettings && !window.SheetGPTSettings.canMakeRequest()) {
        window.SheetGPTSettings.showToast('Лимит запросов исчерпан', 'error');
        window.SheetGPTSettings.openUpgradeModal();
        return;
      }

      // v9.0.1: Save query for display_mode detection
      window.lastUserQuery = message;

      // Hide empty state
      document.getElementById('emptyState').style.display = 'none';

      // Add user message
      addMessage(message, 'user');

      // Save user message to history
      chatHistory.push({
        role: 'user',
        content: message
      });

      // Clear input
      input.value = '';
      input.style.height = 'auto';
      document.getElementById('sendBtn').disabled = true;

      // Show loading
      isProcessing = true;
      addLoadingIndicator();

      // Call backend
      google.script.run
        .withSuccessHandler(handleResponse)
        .withFailureHandler(handleError)
        .processQuery(message);
    }

    function addMessage(content, type) {
      const container = document.getElementById('chatContainer');
      const messageDiv = document.createElement('div');
      messageDiv.className = `message ${type}`;

      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';
      bubble.textContent = content;

      messageDiv.appendChild(bubble);
      container.appendChild(messageDiv);

      scrollToBottom();
    }

    function addAIResponse(result) {
      try {
        const container = document.getElementById('chatContainer');

        // Use new templates from response-templates.js if available
        if (typeof renderAIResponse === 'function') {
          renderAIResponse(result);
        } else {
          // Fallback to simple display
          const messageDiv = document.createElement('div');
          messageDiv.className = 'message ai';
          const bubble = document.createElement('div');
          bubble.className = 'message-bubble';
          bubble.innerHTML = `
            <div class="ai-response">
              <div class="response-header">
                <div class="response-type-icon analysis">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 3v18h18"/><path d="M7 12l4-4 4 4 5-5"/>
                  </svg>
                </div>
                <span class="response-type-label">Анализ</span>
              </div>
              <div class="response-body">
                <div class="response-result">${result.summary || result.explanation || 'Результат'}</div>
                ${result.methodology ? `<div class="response-explanation">${result.methodology}</div>` : ''}
              </div>
            </div>
          `;
          messageDiv.appendChild(bubble);
          container.appendChild(messageDiv);
        }

        // Handle structured data (tables, charts, and split operations)
        if (result.structured_data) {
          console.log('[UI] Processing structured_data');
          console.log('[UI] operation_type:', result.structured_data.operation_type);
          console.log('[UI] Data:', result.structured_data);
          console.log('[UI] Rows count:', result.structured_data.rows ? result.structured_data.rows.length : 0);

          // КРИТИЧНО: Проверяем operation_type и display_mode чтобы определить куда отправлять данные
          const isSplitOperation = result.structured_data.operation_type === 'split';
          const rowCount = result.structured_data.rows ? result.structured_data.rows.length : 0;

          // v9.0.1: Проверяем, просил ли пользователь явно создать отдельный лист
          const userQuery = (window.lastUserQuery || '').toLowerCase();
          const wantsNewSheet = userQuery.includes('отдельн') || userQuery.includes('новом листе') ||
                               userQuery.includes('новый лист') || userQuery.includes('создай лист') ||
                               userQuery.includes('создай таблицу') || userQuery.includes('в листе') ||
                               userQuery.includes('на листе') || userQuery.includes('в таблиц');

          // Логика выбора display_mode:
          // 1. Если пользователь ЯВНО просит создать лист - ВСЕГДА create_sheet (приоритет!)
          // 2. Если > 50 строк - create_sheet
          // 3. Если указано в ответе backend - используем его
          // 4. Иначе - sidebar_only
          let displayMode;
          if (wantsNewSheet) {
            displayMode = 'create_sheet';
            console.log('[UI] User requested new sheet explicitly, overriding backend');
          } else if (rowCount > 50) {
            displayMode = 'create_sheet';
            console.log('[UI] Large dataset (>50 rows), creating sheet');
          } else {
            displayMode = result.structured_data.display_mode || 'sidebar_only';
          }
          console.log('[UI] Display mode:', displayMode);

          if (isSplitOperation) {
            // SPLIT OPERATION: заменяем данные в ТЕКУЩЕМ листе
            console.log('[UI] SPLIT OPERATION: Replacing data in current sheet');

            google.script.run
              .withSuccessHandler(function(splitResult) {
                console.log('[UI] Split success handler:', splitResult);

                const resultDiv = document.createElement('div');
                resultDiv.className = 'message ai';
                const resultBubble = document.createElement('div');
                resultBubble.className = 'message-bubble';
                const resultBox = document.createElement('div');

                if (splitResult && splitResult.success) {
                  resultBox.className = 'content-box success';
                  resultBox.textContent = '✅ ' + (splitResult.message || 'Данные успешно разбиты');
                } else {
                  resultBox.className = 'content-box error';
                  resultBox.textContent = '❌ ' + (splitResult ? (splitResult.message || splitResult.error || 'Неизвестная ошибка') : 'Функция не вернула результат');
                }

                resultBubble.appendChild(resultBox);
                resultDiv.appendChild(resultBubble);
                container.appendChild(resultDiv);
                scrollToBottom();
              })
              .withFailureHandler(function(error) {
                console.error('[UI] Split operation failed:', error);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message ai';
                const errorBubble = document.createElement('div');
                errorBubble.className = 'message-bubble';
                const errorBox = document.createElement('div');
                errorBox.className = 'content-box error';
                errorBox.textContent = 'Ошибка разбиения данных: ' + error.message;
                errorBubble.appendChild(errorBox);
                errorDiv.appendChild(errorBubble);
                container.appendChild(errorDiv);
                scrollToBottom();
              })
              .replaceDataInCurrentSheet(result.structured_data);
          } else if (displayMode === 'sidebar_only') {
            // v7.8.14: SIDEBAR DISPLAY: показываем таблицу прямо в sidebar (для простых списков)
            console.log('[UI] SIDEBAR DISPLAY: Showing table in sidebar (simple list)');
            displayTableInSidebar(result.structured_data, container);
          } else {
            // TABLE/CHART OPERATION: создаём НОВЫЙ лист
            console.log('[UI] TABLE/CHART OPERATION: Creating new sheet');

            // v9.0.2: Enhanced debug logging and validation before calling createTableAndChart
            console.log('[UI] Calling createTableAndChart with:', result.structured_data);
            console.log('[UI] structured_data keys:', result.structured_data ? Object.keys(result.structured_data) : 'null');
            console.log('[UI] headers:', result.structured_data?.headers);
            console.log('[UI] rows:', result.structured_data?.rows);
            console.log('[UI] rows count:', result.structured_data?.rows?.length);

            // v9.0.2: Pre-call validation
            if (!result.structured_data?.headers || !result.structured_data?.rows) {
              console.error('[UI] ❌ ERROR: structured_data missing headers or rows!');
              console.error('[UI] Full result object:', JSON.stringify(result, null, 2));
              const errorDiv = document.createElement('div');
              errorDiv.className = 'message ai';
              const errorBubble = document.createElement('div');
              errorBubble.className = 'message-bubble';
              const errorBox = document.createElement('div');
              errorBox.className = 'content-box error';
              errorBox.textContent = '❌ Ошибка: данные таблицы отсутствуют или повреждены';
              errorBubble.appendChild(errorBox);
              errorDiv.appendChild(errorBubble);
              container.appendChild(errorDiv);
              scrollToBottom();
              return;
            }

            google.script.run
              .withSuccessHandler(function(tableResult) {
                console.log('[UI] Table success handler:', tableResult);

                const resultDiv = document.createElement('div');
                resultDiv.className = 'message ai';
                const resultBubble = document.createElement('div');
                resultBubble.className = 'message-bubble';
                const resultBox = document.createElement('div');

                if (tableResult && tableResult.success) {
                  resultBox.className = 'content-box success';
                  resultBox.textContent = '✅ ' + (tableResult.message || 'Таблица создана успешно');
                } else {
                  resultBox.className = 'content-box error';
                  resultBox.textContent = '❌ ' + (tableResult ? (tableResult.message || tableResult.error || 'Неизвестная ошибка') : 'Функция не вернула результат');
                }

                resultBubble.appendChild(resultBox);
                resultDiv.appendChild(resultBubble);
                container.appendChild(resultDiv);
                scrollToBottom();
              })
              .withFailureHandler(function(error) {
                console.error('[UI] Table creation failed:', error);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message ai';
                const errorBubble = document.createElement('div');
                errorBubble.className = 'message-bubble';
                const errorBox = document.createElement('div');
                errorBox.className = 'content-box error';
                errorBox.textContent = 'Ошибка создания таблицы: ' + error.message;
                errorBubble.appendChild(errorBox);
                errorDiv.appendChild(errorBubble);
                container.appendChild(errorDiv);
                scrollToBottom();
              })
              .createTableAndChart(result.structured_data);
          }
        }

        // Handle row highlighting
        if (result.highlight_rows && result.highlight_rows.length > 0) {
          console.log('[UI] Highlighting rows:', result.highlight_rows);
          google.script.run
            .withSuccessHandler(function(highlightResult) {
              if (highlightResult.success) {
                const successDiv = document.createElement('div');
                successDiv.className = 'message ai';
                const successBubble = document.createElement('div');
                successBubble.className = 'message-bubble';
                const successBox = document.createElement('div');
                successBox.className = 'content-box success';
                successBox.textContent = result.highlight_message || highlightResult.message;
                successBubble.appendChild(successBox);
                successDiv.appendChild(successBubble);
                container.appendChild(successDiv);
                scrollToBottom();
              }
            })
            .withFailureHandler(function(error) {
              console.error('[UI] Row highlighting failed:', error);
            })
            .highlightRows(result.highlight_rows, result.highlight_color || '#FFFF00');
        }

        scrollToBottom();
      } catch (error) {
        console.error('Error in addAIResponse:', error);
        handleError({message: 'Ошибка отображения ответа: ' + error.message});
      }
    }

    function addLoadingIndicator() {
      const container = document.getElementById('chatContainer');
      // Use new template from response-templates.js
      if (typeof createLoadingMessage === 'function') {
        container.insertAdjacentHTML('beforeend', createLoadingMessage());
      } else {
        // Fallback to old loading
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message ai';
        loadingDiv.id = 'loadingMessage';
        const loading = document.createElement('div');
        loading.className = 'loading-indicator';
        loading.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div><span class="loading-text">Думаю...</span>';
        loadingDiv.appendChild(loading);
        container.appendChild(loadingDiv);
      }
      scrollToBottom();
    }

    function removeLoadingIndicator() {
      const loading = document.getElementById('loadingMessage') || document.getElementById('loading');
      if (loading) loading.remove();
    }

    function handleResponse(result) {
      removeLoadingIndicator();
      isProcessing = false;

      if (result) {
        addAIResponse(result);
        // Increment usage after successful query
        incrementUsage();
      } else {
        handleError({message: 'Пустой ответ от сервера'});
      }
    }

    // Increment usage via API
    async function incrementUsage() {
      const licenseKey = localStorage.getItem(LICENSE_STORAGE_KEY);
      if (!licenseKey) {
        console.warn('[Sidebar] No license key for usage tracking');
        return;
      }

      try {
        const response = await fetch(`${LICENSE_STATUS_URL}/${encodeURIComponent(licenseKey)}/increment-usage`, {
          method: 'POST',
          headers: { 'Accept': 'application/json' }
        });

        if (response.ok) {
          const data = await response.json();
          console.log('[Sidebar] Usage incremented:', data);

          // Update local storage
          const userData = JSON.parse(localStorage.getItem(USER_DATA_STORAGE_KEY) || '{}');
          userData.queries_used_today = data.queries_used_today;
          userData.queries_limit = data.queries_limit;
          localStorage.setItem(USER_DATA_STORAGE_KEY, JSON.stringify(userData));

          // Update settings menu
          if (window.SheetGPTSettings) {
            window.SheetGPTSettings.setUserData(userData);
          }

          // Проверяем, является ли пользователь premium/unlimited
          const isUnlimited = data.queries_remaining === -1 || data.queries_limit === -1;

          // Show warning if limit almost reached (только для free пользователей)
          if (!data.can_make_query && !isUnlimited) {
            if (window.SheetGPTSettings) {
              window.SheetGPTSettings.showToast('Лимит запросов исчерпан', 'error');
              window.SheetGPTSettings.openUpgradeModal();
            }
          } else if (!isUnlimited && data.queries_remaining <= 3 && data.queries_remaining > 0) {
            if (window.SheetGPTSettings) {
              window.SheetGPTSettings.showToast(`Осталось ${data.queries_remaining} запросов`, 'warning');
            }
          }
        }
      } catch (error) {
        console.error('[Sidebar] Usage increment error:', error);
      }
    }

    function handleError(error) {
      removeLoadingIndicator();
      isProcessing = false;

      const container = document.getElementById('chatContainer');
      const errorDiv = document.createElement('div');
      errorDiv.className = 'message ai';

      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';
      bubble.style.borderColor = 'var(--error)';

      const errorMessage = error.message || 'Неизвестная ошибка';

      // Умная обработка типичных ошибок
      const errorBox = document.createElement('div');
      errorBox.className = 'content-box error';

      // Классифицируем ошибку для пользователя
      const errorInfo = classifyError(errorMessage);

      errorBox.innerHTML = `
        <div style="margin-bottom: 8px;">${errorInfo.icon} ${errorInfo.title}</div>
        <div style="font-size: 13px; color: #666; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;">
          ${errorInfo.description}
          ${errorInfo.suggestions ? `
            <div style="margin-top: 10px;">
              💡 <strong>Что попробовать:</strong><br/>
              ${errorInfo.suggestions.map(s => `• ${s}`).join('<br/>')}
            </div>
          ` : ''}
        </div>
      `;

      bubble.appendChild(errorBox);
      errorDiv.appendChild(bubble);
      container.appendChild(errorDiv);

      scrollToBottom();
    }

    // Классификация ошибок для понятных сообщений пользователю
    function classifyError(errorMessage) {
      const lowerMsg = errorMessage.toLowerCase();

      // v7.9.3: Extension context invalidated - расширение обновилось
      if (lowerMsg.includes('extension context invalidated') ||
          lowerMsg.includes('context invalidated') ||
          lowerMsg.includes('extension context')) {
        return {
          icon: '🔄',
          title: 'Расширение обновилось',
          description: 'Расширение было обновлено. Требуется перезагрузка страницы.',
          suggestions: [
            'Закройте эту вкладку и откройте Google Sheets заново',
            'Или нажмите Ctrl+Shift+R для полной перезагрузки'
          ]
        };
      }

      // Таймаут / сетевые ошибки
      if (lowerMsg.includes('timeout') || lowerMsg.includes('timed out')) {
        return {
          icon: '⏱️',
          title: 'Превышено время ожидания',
          description: 'Сервер не ответил вовремя. Было выполнено несколько попыток подключения.',
          suggestions: [
            'Попробуйте ещё раз через несколько секунд',
            'Проверьте интернет-соединение',
            'Упростите запрос, если он сложный'
          ]
        };
      }

      // Сетевые ошибки
      if (lowerMsg.includes('network') || lowerMsg.includes('fetch') || lowerMsg.includes('connection')) {
        return {
          icon: '🌐',
          title: 'Ошибка сети',
          description: 'Не удалось подключиться к серверу.',
          suggestions: [
            'Проверьте подключение к интернету',
            'Попробуйте обновить страницу',
            'Повторите запрос через несколько минут'
          ]
        };
      }

      // Серверные ошибки (502, 503, 504)
      if (lowerMsg.includes('502') || lowerMsg.includes('503') || lowerMsg.includes('504') ||
          lowerMsg.includes('unavailable') || lowerMsg.includes('server error')) {
        return {
          icon: '🔧',
          title: 'Сервер временно недоступен',
          description: 'Сервис перегружен или проводится техническое обслуживание.',
          suggestions: [
            'Подождите 30-60 секунд и повторите',
            'Если проблема сохраняется, попробуйте позже'
          ]
        };
      }

      // Ошибки данных
      if (lowerMsg.includes('данные отсутствуют') || lowerMsg.includes('невозможно создать') ||
          lowerMsg.includes('no data') || lowerMsg.includes('empty')) {
        return {
          icon: '📊',
          title: 'Не удалось получить данные',
          description: 'AI не смог найти или сгенерировать запрошенную информацию.',
          suggestions: [
            'Переформулируйте запрос более конкретно',
            'Укажите конкретные примеры данных',
            'Попробуйте запрос с более известными данными'
          ]
        };
      }

      // Ошибки авторизации
      if (lowerMsg.includes('auth') || lowerMsg.includes('token') || lowerMsg.includes('unauthorized') ||
          lowerMsg.includes('401') || lowerMsg.includes('403')) {
        return {
          icon: '🔐',
          title: 'Ошибка авторизации',
          description: 'Требуется повторная авторизация в Google.',
          suggestions: [
            'Обновите страницу Google Sheets',
            'Переустановите расширение если проблема повторяется'
          ]
        };
      }

      // Ошибки формулы
      if (lowerMsg.includes('formula') || lowerMsg.includes('syntax') || lowerMsg.includes('parse')) {
        return {
          icon: '📝',
          title: 'Ошибка в формуле',
          description: 'Не удалось создать корректную формулу для вашего запроса.',
          suggestions: [
            'Попробуйте описать задачу другими словами',
            'Укажите конкретные ячейки или диапазоны',
            'Разбейте сложный запрос на несколько простых'
          ]
        };
      }

      // Неизвестная ошибка
      return {
        icon: '❌',
        title: 'Произошла ошибка',
        description: errorMessage,
        suggestions: [
          'Попробуйте повторить запрос',
          'Если ошибка повторяется, обновите страницу'
        ]
      };
    }

    // v7.8.14: Отображение простых таблиц прямо в sidebar (без создания нового листа)
    function displayTableInSidebar(structuredData, container) {
      console.log('[UI] displayTableInSidebar called with:', structuredData);

      const messageDiv = document.createElement('div');
      messageDiv.className = 'message ai';

      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';

      // Title
      if (structuredData.table_title) {
        const titleDiv = document.createElement('div');
        titleDiv.style.fontWeight = 'bold';
        titleDiv.style.marginBottom = '8px';
        titleDiv.textContent = structuredData.table_title;
        bubble.appendChild(titleDiv);
      }

      // Create table
      const table = document.createElement('table');
      table.style.width = '100%';
      table.style.borderCollapse = 'collapse';
      table.style.fontSize = '13px';
      table.style.marginTop = '8px';

      // Headers - extract from first row if not provided
      let headers = structuredData.headers;
      if ((!headers || headers.length === 0) && structuredData.rows && structuredData.rows.length > 0) {
        const firstRow = structuredData.rows[0];
        if (!Array.isArray(firstRow) && typeof firstRow === 'object') {
          headers = Object.keys(firstRow);
        }
      }

      if (headers && headers.length > 0) {
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        headers.forEach(header => {
          const th = document.createElement('th');
          th.textContent = header;
          th.style.padding = '6px 8px';
          th.style.borderBottom = '2px solid #ddd';
          th.style.textAlign = 'left';
          th.style.backgroundColor = '#f5f5f5';
          headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
      }

      // Rows
      if (structuredData.rows && structuredData.rows.length > 0) {
        const tbody = document.createElement('tbody');
        structuredData.rows.forEach((row, index) => {
          const tr = document.createElement('tr');
          tr.style.backgroundColor = index % 2 === 0 ? '#ffffff' : '#f9f9f9';

          // Handle both array rows and object rows
          const cells = Array.isArray(row) ? row : Object.values(row);
          cells.forEach(cell => {
            const td = document.createElement('td');
            td.textContent = cell !== null && cell !== undefined ? cell : '';
            td.style.padding = '6px 8px';
            td.style.borderBottom = '1px solid #eee';
            tr.appendChild(td);
          });

          tbody.appendChild(tr);
        });
        table.appendChild(tbody);
      }

      bubble.appendChild(table);
      messageDiv.appendChild(bubble);
      container.appendChild(messageDiv);

      // Success message
      const resultDiv = document.createElement('div');
      resultDiv.className = 'message ai';
      const resultBubble = document.createElement('div');
      resultBubble.className = 'message-bubble';
      const resultBox = document.createElement('div');
      resultBox.className = 'content-box success';
      resultBox.textContent = '✅ Результаты отображены в sidebar';
      resultBubble.appendChild(resultBox);
      resultDiv.appendChild(resultBubble);
      container.appendChild(resultDiv);

      scrollToBottom();
    }

    // Глобальная функция для создания листа из предложения
    window.createSheetFromOffer = function(structuredDataJson) {
      try {
        const structuredData = JSON.parse(structuredDataJson);
        console.log('[UI] Creating sheet from offer:', structuredData);

        // Добавляем headers если их нет
        if (!structuredData.headers && structuredData.rows && structuredData.rows.length > 0) {
          const firstRow = structuredData.rows[0];
          if (!Array.isArray(firstRow) && typeof firstRow === 'object') {
            structuredData.headers = Object.keys(firstRow);
          }
        }

        google.script.run
          .withSuccessHandler(function(result) {
            console.log('[UI] Sheet created:', result);
            const container = document.getElementById('chatContainer');
            const successDiv = document.createElement('div');
            successDiv.className = 'message ai';
            successDiv.innerHTML = `
              <div class="message-bubble">
                <div class="content-box success">
                  ✅ Лист "${result.sheet_name || 'SheetGPT'}" создан (${result.rows_count || structuredData.rows?.length || 0} строк)
                </div>
              </div>
            `;
            container.appendChild(successDiv);
            scrollToBottom();
          })
          .withFailureHandler(function(error) {
            console.error('[UI] Sheet creation failed:', error);
            alert('Ошибка при создании листа: ' + error.message);
          })
          .createTableAndChart(structuredData);

        // Скрываем блок с предложением
        document.querySelectorAll('.sheet-offer').forEach(el => el.style.display = 'none');

      } catch (e) {
        console.error('[UI] Error parsing structured data:', e);
        alert('Ошибка: ' + e.message);
      }
    };

    function scrollToBottom() {
      const container = document.getElementById('chatContainer');
      setTimeout(() => {
        container.scrollTop = container.scrollHeight;
      }, 100);
    }

    function insertFormula(formula, targetCell) {
      google.script.run
        .withSuccessHandler(() => {
          alert('Формула вставлена!');
        })
        .withFailureHandler((error) => {
          alert('Ошибка: ' + error.message);
        })
        .insertFormula(formula, targetCell);
    }

    function copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        alert('Скопировано!');
      }).catch(() => {
        alert('Не удалось скопировать');
      });
    }

    // Settings Modal - handled by settings-menu.js

    // Chat History Functions
    let chatHistoryData = [];

    function toggleHistory() {
      const dropdown = document.getElementById('historyDropdown');
      const isVisible = dropdown.classList.contains('show');

      // Close any open dropdowns first
      document.querySelectorAll('.dropdown.show').forEach(d => d.classList.remove('show'));

      if (!isVisible) {
        loadHistory();
        dropdown.classList.add('show');
      }
    }

    function loadHistory() {
      const historyList = document.getElementById('historyList');

      // Load from localStorage (temporary - in production use Google Apps Script)
      const savedHistory = localStorage.getItem('sheetgpt_history');
      chatHistoryData = savedHistory ? JSON.parse(savedHistory) : [];

      if (chatHistoryData.length === 0) {
        historyList.innerHTML = '<div class="dropdown-empty">История пуста</div>';
        return;
      }

      historyList.innerHTML = '';
      chatHistoryData.forEach((item, index) => {
        const li = document.createElement('li');
        li.className = 'dropdown-item';
        li.onclick = () => loadChat(index);

        const title = document.createElement('div');
        title.className = 'dropdown-item-title';
        title.textContent = item.title || item.firstMessage || 'Новый чат';

        const time = document.createElement('div');
        time.className = 'dropdown-item-meta';
        time.textContent = formatTime(item.timestamp);

        li.appendChild(title);
        li.appendChild(time);
        historyList.appendChild(li);
      });
    }

    function saveChatToHistory() {
      const messages = Array.from(document.getElementById('chatContainer').querySelectorAll('.message'));
      if (messages.length === 0) return;

      const firstUserMessage = messages.find(m => m.classList.contains('user'));
      const firstMessage = firstUserMessage ? firstUserMessage.textContent.trim() : 'Новый чат';

      const chatData = {
        id: Date.now(),
        title: firstMessage.substring(0, 50) + (firstMessage.length > 50 ? '...' : ''),
        firstMessage: firstMessage,
        timestamp: Date.now(),
        messages: chatHistory
      };

      chatHistoryData.unshift(chatData);
      if (chatHistoryData.length > 20) chatHistoryData.pop(); // Keep only last 20

      localStorage.setItem('sheetgpt_history', JSON.stringify(chatHistoryData));
    }

    function loadChat(index) {
      const chat = chatHistoryData[index];
      if (!chat) return;

      // Clear current chat
      const container = document.getElementById('chatContainer');
      container.innerHTML = '';
      const emptyState = document.getElementById('emptyState');
      if (emptyState) {
        emptyState.style.display = 'none';
      }

      // Restore chat history array
      chatHistory = chat.messages || [];

      // Restore messages from saved history
      if (chat.messages && chat.messages.length > 0) {
        chat.messages.forEach(msg => {
          if (msg.role === 'user') {
            addMessage(msg.content, 'user');
          } else if (msg.role === 'assistant' && msg.result) {
            addAIResponse(msg.result);
          }
        });
      } else {
        // Fallback: just show the title as first message
        addMessage(chat.firstMessage || chat.title, 'user');
      }

      toggleHistory();
      scrollToBottom();
    }

    function formatTime(timestamp) {
      const date = new Date(timestamp);
      const now = new Date();
      const diff = now - date;

      if (diff < 60000) return 'только что';
      if (diff < 3600000) return Math.floor(diff / 60000) + ' мин назад';
      if (diff < 86400000) return Math.floor(diff / 3600000) + ' ч назад';

      return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    }

    // Save chat on successful response
    const originalHandleResponse = handleResponse;
    handleResponse = function(result) {
      // Save AI response to history
      if (result) {
        chatHistory.push({
          role: 'assistant',
          result: result  // Save full result for later restoration
        });
      }

      originalHandleResponse(result);
      setTimeout(saveChatToHistory, 500); // Save after rendering
    };

    // Close history dropdown when clicking outside
    document.addEventListener('click', function(e) {
      const dropdown = document.getElementById('historyDropdown');
      const historyBtn = document.querySelector('button[aria-label="История"]');

      if (!dropdown.contains(e.target) && e.target !== historyBtn && !historyBtn.contains(e.target)) {
        dropdown.classList.remove('show');
      }
    });

// ===== THEME MANAGEMENT =====
function initTheme() {
  const savedTheme = localStorage.getItem('sheetgpt_theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = savedTheme || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  console.log('[Sidebar] Theme initialized:', theme);
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('sheetgpt_theme', newTheme);
  console.log('[Sidebar] Theme toggled to:', newTheme);
}

// Initialize theme on load
initTheme();

// ===== EVENT LISTENERS INITIALIZATION =====
console.log('[Sidebar] Setting up event listeners...');

// Theme toggle
const themeToggle = document.getElementById('themeToggle');
if (themeToggle) {
  themeToggle.addEventListener('click', toggleTheme);
  console.log('[Sidebar] ✅ Theme toggle listener attached');
}

// Send button
const sendBtn = document.getElementById('sendBtn');
if (sendBtn) {
  sendBtn.addEventListener('click', sendMessage);
  console.log('[Sidebar] ✅ Send button listener attached');
}

// Message input - Enter to send
const messageInput = document.getElementById('messageInput');
if (messageInput) {
  messageInput.addEventListener('keydown', handleKeyPress);
  console.log('[Sidebar] ✅ Message input keydown listener attached');
}

// Template cards
document.querySelectorAll('.template-card').forEach(card => {
  const query = card.getAttribute('data-query');
  if (query) {
    card.addEventListener('click', () => useExample(query));
  }
});
console.log('[Sidebar] ✅ Template cards listeners attached');

// History button
const historyBtn = document.getElementById('historyBtn');
if (historyBtn) {
  historyBtn.addEventListener('click', toggleHistory);
  console.log('[Sidebar] ✅ History button listener attached');
}

// Settings button - handled by settings-menu.js

console.log('[Sidebar] Event listeners initialized');
