// ===== POSTMESSAGE BRIDGE FOR CHROME EXTENSION =====
console.log('[Sidebar] Initializing event listeners...');

let messageIdCounter = 0;
const pendingMessages = new Map();

// Send message to content script via postMessage
function sendMessageToContentScript(action, data) {
  console.log('[Sidebar] sendMessageToContentScript called with:', { action, data });
  return new Promise((resolve, reject) => {
    const messageId = ++messageIdCounter;
    pendingMessages.set(messageId, { resolve, reject });

    const message = { action, data, messageId };
    console.log('[Sidebar] Sending message to parent:', message);
    window.parent.postMessage(message, '*');

    // Timeout after 30 seconds
    setTimeout(() => {
      if (pendingMessages.has(messageId)) {
        pendingMessages.delete(messageId);
        reject(new Error('Request timeout'));
      }
    }, 30000);
  });
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
      return { structuredData: args[0] };
    case 'replaceDataInCurrentSheet':
      return { structuredData: args[0] };
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
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        // Response type badge
        const responseType = result.response_type || 'formula';
        const badge = document.createElement('div');
        badge.className = 'response-badge';
        if (responseType === 'analysis') {
          badge.textContent = 'Анализ';
        } else if (responseType === 'action') {
          badge.textContent = 'Действия';
        } else {
          badge.textContent = 'Формула';
        }
        bubble.appendChild(badge);

        // Main content
        const content = document.createElement('div');

        if (responseType === 'formula' && result.formula) {
          // Formula
          const formulaDiv = document.createElement('div');
          formulaDiv.className = 'formula-code';
          formulaDiv.textContent = result.formula;
          content.appendChild(formulaDiv);

          // Explanation
          if (result.explanation) {
            const explanation = document.createElement('p');
            explanation.style.marginTop = '12px';
            explanation.textContent = result.explanation;
            content.appendChild(explanation);
          }

          // Action buttons
          const actions = document.createElement('div');
          actions.className = 'action-buttons';

          const insertBtn = document.createElement('button');
          insertBtn.className = 'btn-primary btn-sm';
          insertBtn.textContent = 'Вставить формулу';
          insertBtn.onclick = () => insertFormula(result.formula, result.target_cell);
          actions.appendChild(insertBtn);

          const copyBtn = document.createElement('button');
          copyBtn.className = 'btn-secondary btn-sm';
          copyBtn.textContent = 'Скопировать';
          copyBtn.onclick = () => copyToClipboard(result.formula);
          actions.appendChild(copyBtn);

          content.appendChild(actions);
        } else {
          // Analysis response

          // Summary
          if (result.summary) {
            const summaryBox = document.createElement('div');

            // Проверяем на сообщения об отсутствии данных
            if (result.summary.includes('Данные отсутствуют') || result.summary.includes('невозможно создать')) {
              summaryBox.className = 'content-box error';
              summaryBox.innerHTML = `
                <div style="margin-bottom: 8px;">❌ ${result.summary}</div>
                <div style="font-size: 13px; color: #666; margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee;">
                  <strong>💡 Что попробовать:</strong><br/>
                  <ul style="margin: 8px 0; padding-left: 20px;">
                    <li>Переформулируйте запрос более конкретно</li>
                    <li>Укажите конкретные примеры данных</li>
                    <li>Попробуйте более простую тему с базовыми данными</li>
                  </ul>
                  <strong>✅ Примеры успешных запросов:</strong><br/>
                  <ul style="margin: 8px 0; padding-left: 20px;">
                    <li>"Создай таблицу с топ-10 стран Европы"</li>
                    <li>"Создай таблицу планет солнечной системы"</li>
                    <li>"Создай таблицу химических элементов"</li>
                  </ul>
                </div>
              `;
            } else {
              summaryBox.className = 'content-box info';
              const sentences = result.summary.split('. ');
              summaryBox.innerHTML = sentences.map(s => s.trim() ? `<p style="margin: 8px 0;">${s.trim()}${s.endsWith('.') ? '' : '.'}</p>` : '').join('');
            }

            content.appendChild(summaryBox);
          } else if (result.explanation) {
            const explanation = document.createElement('p');
            explanation.textContent = result.explanation;
            content.appendChild(explanation);
          }

          // Methodology
          if (result.methodology) {
            const sectionTitle = document.createElement('div');
            sectionTitle.className = 'section-title';
            sectionTitle.textContent = 'Методология';
            content.appendChild(sectionTitle);

            const methodBox = document.createElement('div');
            methodBox.className = 'content-box';
            methodBox.innerHTML = result.methodology;
            content.appendChild(methodBox);
          }

          // Key findings
          if (result.key_findings && result.key_findings.length > 0) {
            const sectionTitle = document.createElement('div');
            sectionTitle.className = 'section-title';
            sectionTitle.textContent = 'Ключевые находки';
            content.appendChild(sectionTitle);

            const findingsList = document.createElement('ul');
            findingsList.className = 'list-items';
            result.key_findings.forEach(finding => {
              const li = document.createElement('li');
              li.textContent = finding;
              findingsList.appendChild(li);
            });
            content.appendChild(findingsList);
          }

          // Professional Insights
          if (result.professional_insights) {
            const sectionTitle = document.createElement('div');
            sectionTitle.className = 'section-title';
            sectionTitle.textContent = 'Профессиональный анализ';
            content.appendChild(sectionTitle);

            const insightsBox = document.createElement('div');
            insightsBox.className = 'content-box warning';
            insightsBox.textContent = result.professional_insights;
            content.appendChild(insightsBox);
          }

          // Recommendations
          if (result.recommendations && result.recommendations.length > 0) {
            const sectionTitle = document.createElement('div');
            sectionTitle.className = 'section-title';
            sectionTitle.textContent = 'Рекомендации';
            content.appendChild(sectionTitle);

            const recsList = document.createElement('ul');
            recsList.className = 'list-items';
            result.recommendations.forEach(rec => {
              const li = document.createElement('li');
              li.textContent = rec;
              recsList.appendChild(li);
            });
            content.appendChild(recsList);
          }

          // Warnings
          if (result.warnings && result.warnings.length > 0) {
            const sectionTitle = document.createElement('div');
            sectionTitle.className = 'section-title';
            sectionTitle.textContent = 'Предупреждения';
            content.appendChild(sectionTitle);

            const warnsList = document.createElement('ul');
            warnsList.className = 'list-items';
            result.warnings.forEach(warn => {
              const li = document.createElement('li');
              li.textContent = warn;
              warnsList.appendChild(li);
            });
            content.appendChild(warnsList);
          }
        }

        bubble.appendChild(content);
        messageDiv.appendChild(bubble);
        container.appendChild(messageDiv);

        // Handle structured data (tables, charts, and split operations)
        if (result.structured_data) {
          console.log('[UI] Processing structured_data');
          console.log('[UI] operation_type:', result.structured_data.operation_type);
          console.log('[UI] Data:', result.structured_data);

          // КРИТИЧНО: Проверяем operation_type чтобы определить куда отправлять данные
          const isSplitOperation = result.structured_data.operation_type === 'split';

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
          } else {
            // TABLE/CHART OPERATION: создаём НОВЫЙ лист
            console.log('[UI] TABLE/CHART OPERATION: Creating new sheet');

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
      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'message ai';
      loadingDiv.id = 'loading';

      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';

      const loading = document.createElement('div');
      loading.className = 'loading-indicator';
      loading.innerHTML = '<div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div>';

      bubble.appendChild(loading);
      loadingDiv.appendChild(bubble);
      container.appendChild(loadingDiv);

      scrollToBottom();
    }

    function removeLoadingIndicator() {
      const loading = document.getElementById('loading');
      if (loading) loading.remove();
    }

    function handleResponse(result) {
      removeLoadingIndicator();
      isProcessing = false;

      if (result) {
        addAIResponse(result);
      } else {
        handleError({message: 'Пустой ответ от сервера'});
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

      // Проверяем на специфичные ошибки и даём подсказки
      if (errorMessage.includes('Данные отсутствуют') || errorMessage.includes('невозможно создать')) {
        errorBox.innerHTML = `
          <div style="margin-bottom: 8px;">❌ ${errorMessage}</div>
          <div style="font-size: 13px; color: #666; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;">
            💡 <strong>Попробуйте:</strong><br/>
            • Переформулируйте запрос более конкретно<br/>
            • Укажите конкретные примеры (например: "GPT-4, Claude, Gemini")<br/>
            • Используйте более простые запросы с базовыми данными<br/>
            <br/>
            <strong>Примеры успешных запросов:</strong><br/>
            • "Создай таблицу с топ-10 стран Европы по населению"<br/>
            • "Создай таблицу планет солнечной системы"<br/>
            • "Создай таблицу химических элементов (первые 10)"
          </div>
        `;
      } else {
        errorBox.textContent = 'Ошибка: ' + errorMessage;
      }

      bubble.appendChild(errorBox);
      errorDiv.appendChild(bubble);
      container.appendChild(errorDiv);

      scrollToBottom();
    }

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

    // Settings Modal
    function openSettings() {
      google.script.run
        .withSuccessHandler(function(context) {
          document.getElementById('customContextInput').value = context || '';
          document.getElementById('charCount').textContent = (context || '').length;
          document.getElementById('settingsModal').style.display = 'flex';
        })
        .getCustomContext();
    }

    function closeSettings() {
      document.getElementById('settingsModal').style.display = 'none';
    }

    function saveSettings() {
      const context = document.getElementById('customContextInput').value.trim();

      google.script.run
        .withSuccessHandler(function(result) {
          if (result.success) {
            alert('Настройки сохранены!');
            closeSettings();
          } else {
            alert('Ошибка сохранения: ' + result.error);
          }
        })
        .withFailureHandler(function(error) {
          alert('Ошибка: ' + error.message);
        })
        .saveCustomContext(context);
    }

    // Chat History Functions
    let chatHistoryData = [];

    function toggleHistory() {
      const dropdown = document.getElementById('historyDropdown');
      const isVisible = dropdown.classList.contains('show');

      if (isVisible) {
        dropdown.classList.remove('show');
      } else {
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
        historyList.innerHTML = '<div class="history-empty">История пуста</div>';
        return;
      }

      historyList.innerHTML = '';
      chatHistoryData.forEach((item, index) => {
        const li = document.createElement('li');
        li.className = 'history-item';
        li.onclick = () => loadChat(index);

        const title = document.createElement('div');
        title.className = 'history-item-title';
        title.textContent = item.title || item.firstMessage || 'Новый чат';

        const time = document.createElement('div');
        time.className = 'history-item-time';
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

// ===== EVENT LISTENERS INITIALIZATION =====
console.log('[Sidebar] Setting up event listeners...');

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

// Settings button
const settingsBtn = document.getElementById('settingsBtn');
if (settingsBtn) {
  settingsBtn.addEventListener('click', openSettings);
  console.log('[Sidebar] ✅ Settings button listener attached');
}

// Save settings button
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
if (saveSettingsBtn) {
  saveSettingsBtn.addEventListener('click', saveSettings);
  console.log('[Sidebar] ✅ Save settings button listener attached');
}

// Cancel settings button
const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
if (cancelSettingsBtn) {
  cancelSettingsBtn.addEventListener('click', closeSettings);
  console.log('[Sidebar] ✅ Cancel settings button listener attached');
}

console.log('[Sidebar] Event listeners initialized');
