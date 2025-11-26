/**
 * SheetGPT - Settings Menu Logic
 * Управление меню настроек, тарифами, usage bar
 */

// ===== КОНФИГУРАЦИЯ ТАРИФОВ =====
const PLANS = {
  free: {
    name: 'FREE',
    limit: 10,
    resetPeriod: 'daily', // daily, weekly, monthly
  },
  unlimited: {
    name: 'UNLIMITED',
    limit: Infinity,
    price: 299,
  }
};

// ===== КОНСТАНТЫ =====
const USER_DATA_STORAGE_KEY = 'sheetgpt_user_data';
const LICENSE_STORAGE_KEY = 'sheetgpt_license_key';

// ===== СОСТОЯНИЕ =====
let userState = {
  username: null,
  first_name: null,
  telegram_user_id: null,
  plan: 'free', // 'free' | 'premium'
  requestsUsed: 0,
  requestsLimit: 10,
};

// ===== ИНИЦИАЛИЗАЦИЯ =====
function init() {
  console.log('[SettingsMenu] Initializing...');
  initSettingsMenu();
  initModals();
  loadUserState();
  updateUsageDisplay();
  console.log('[SettingsMenu] ✅ Initialized');
}

// Инициализация: либо сразу, либо на DOMContentLoaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

function initSettingsMenu() {
  const settingsBtn = document.getElementById('settingsBtn');
  const settingsDropdown = document.getElementById('settingsDropdown');

  console.log('[SettingsMenu] settingsBtn:', settingsBtn);
  console.log('[SettingsMenu] settingsDropdown:', settingsDropdown);

  if (!settingsBtn || !settingsDropdown) {
    console.error('[SettingsMenu] ❌ Elements not found!');
    return;
  }

  // Toggle dropdown
  settingsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    console.log('[SettingsMenu] Button clicked!');
    settingsDropdown.classList.toggle('show');
    console.log('[SettingsMenu] Dropdown classes:', settingsDropdown.className);

    // Закрыть другие dropdown
    document.getElementById('historyDropdown')?.classList.remove('show');
  });

  // Закрыть при клике вне
  document.addEventListener('click', (e) => {
    if (!settingsDropdown?.contains(e.target) && e.target !== settingsBtn) {
      settingsDropdown?.classList.remove('show');
    }
  });

  // Menu item handlers
  document.getElementById('personalizeBtn')?.addEventListener('click', () => {
    settingsDropdown.classList.remove('show');
    openModal('personalizeModal');
  });

  document.getElementById('historyMenuBtn')?.addEventListener('click', () => {
    settingsDropdown.classList.remove('show');
    document.getElementById('historyDropdown')?.classList.toggle('show');
  });

  document.getElementById('upgradeBtn')?.addEventListener('click', () => {
    settingsDropdown.classList.remove('show');
    openModal('upgradeModal');
  });

  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    handleLogout();
  });
}

function initModals() {
  // Personalize modal
  const personalizeModal = document.getElementById('personalizeModal');
  const cancelPersonalizeBtn = document.getElementById('cancelPersonalizeBtn');
  const savePersonalizeBtn = document.getElementById('savePersonalizeBtn');
  const contextInput = document.getElementById('customContextInput');
  const charCount = document.getElementById('charCount');

  // Загрузить сохранённый контекст при открытии модала
  if (contextInput) {
    const savedContext = localStorage.getItem('sheetgpt_context') || '';
    contextInput.value = savedContext;
    if (charCount) charCount.textContent = savedContext.length;
  }

  cancelPersonalizeBtn?.addEventListener('click', () => {
    closeModal('personalizeModal');
  });

  savePersonalizeBtn?.addEventListener('click', () => {
    if (contextInput) {
      savePersonalization(contextInput.value);
    }
    closeModal('personalizeModal');
  });

  contextInput?.addEventListener('input', () => {
    if (charCount) charCount.textContent = contextInput.value.length;
  });

  // Upgrade modal
  const upgradeModal = document.getElementById('upgradeModal');
  const closeUpgradeBtn = document.getElementById('closeUpgradeModal');
  const purchaseBtn = document.getElementById('purchaseBtn');

  closeUpgradeBtn?.addEventListener('click', () => {
    closeModal('upgradeModal');
  });

  purchaseBtn?.addEventListener('click', () => {
    handlePurchase();
  });

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('show');
      }
    });
  });
}

// ===== MODAL HELPERS =====
function openModal(modalId) {
  document.getElementById(modalId)?.classList.add('show');
}

function closeModal(modalId) {
  document.getElementById(modalId)?.classList.remove('show');
}

// ===== USER STATE =====
function loadUserState() {
  // Загрузить из localStorage (данные от API через sidebar.js)
  const saved = localStorage.getItem(USER_DATA_STORAGE_KEY);
  console.log('[SettingsMenu] Loading user data:', saved);

  if (saved) {
    try {
      const data = JSON.parse(saved);
      userState = {
        username: data.username || null,
        first_name: data.first_name || null,
        telegram_user_id: data.telegram_user_id || null,
        plan: data.subscription_tier || 'free',
        requestsUsed: data.queries_used_today || 0,
        requestsLimit: data.queries_limit || 10,
      };
      console.log('[SettingsMenu] User state loaded:', userState);
    } catch (e) {
      console.error('[SettingsMenu] Error loading user state:', e);
    }
  }
}

function saveUserState() {
  // Сохраняем в том же формате что и sidebar.js
  const data = {
    username: userState.username,
    first_name: userState.first_name,
    telegram_user_id: userState.telegram_user_id,
    subscription_tier: userState.plan,
    queries_used_today: userState.requestsUsed,
    queries_limit: userState.requestsLimit,
  };
  localStorage.setItem(USER_DATA_STORAGE_KEY, JSON.stringify(data));
}

// Функция для обновления данных из sidebar.js
function setUserData(data) {
  console.log('[SettingsMenu] setUserData called:', data);
  userState = {
    username: data.username || null,
    first_name: data.first_name || null,
    telegram_user_id: data.telegram_user_id || null,
    plan: data.subscription_tier || 'free',
    requestsUsed: data.queries_used_today || 0,
    requestsLimit: data.queries_limit || 10,
  };
  updateUsageDisplay();
}

// ===== USAGE DISPLAY =====
function updateUsageDisplay() {
  const usernameEl = document.getElementById('userEmail'); // элемент для имени пользователя
  const badgeEl = document.getElementById('planBadge');
  const countEl = document.getElementById('usageCount');
  const barFillEl = document.getElementById('usageBarFill');
  const resetEl = document.getElementById('usageReset');
  const upgradeLinkEl = document.getElementById('upgradeBtn');

  // Username (показываем @username или first_name)
  if (usernameEl) {
    const displayName = userState.username
      ? `@${userState.username}`
      : userState.first_name || 'Пользователь';
    usernameEl.textContent = displayName;
  }

  // Plan badge
  if (badgeEl) {
    const isPremium = userState.plan === 'premium' || userState.plan === 'unlimited';
    badgeEl.textContent = isPremium ? 'UNLIMITED' : 'FREE';
    badgeEl.classList.toggle('unlimited', isPremium);
  }

  // Usage count & bar
  const isPremium = userState.plan === 'premium' || userState.plan === 'unlimited';
  if (isPremium) {
    if (countEl) countEl.textContent = '∞';
    if (barFillEl) {
      barFillEl.style.width = '100%';
      barFillEl.classList.add('unlimited');
      barFillEl.classList.remove('warning', 'critical');
    }
    if (resetEl) resetEl.textContent = 'Безлимит';
    if (upgradeLinkEl) upgradeLinkEl.style.display = 'none';
  } else {
    const used = userState.requestsUsed;
    const limit = userState.requestsLimit;
    const percent = Math.min((used / limit) * 100, 100);

    if (countEl) countEl.textContent = `${used} / ${limit}`;

    if (barFillEl) {
      barFillEl.style.width = `${percent}%`;
      barFillEl.classList.remove('unlimited', 'warning', 'critical');

      if (percent >= 100) {
        barFillEl.classList.add('critical');
      } else if (percent >= 70) {
        barFillEl.classList.add('warning');
      }
    }

    if (resetEl) {
      resetEl.textContent = 'Обновление: в полночь';
    }

    if (upgradeLinkEl) upgradeLinkEl.style.display = 'flex';
  }

  console.log('[SettingsMenu] Usage display updated:', {
    used: userState.requestsUsed,
    limit: userState.requestsLimit,
    plan: userState.plan
  });
}

// ===== REQUEST TRACKING =====
function canMakeRequest() {
  if (userState.plan === 'unlimited') return true;
  return userState.requestsUsed < userState.requestsLimit;
}

function incrementRequestCount() {
  if (userState.plan === 'unlimited') return;

  userState.requestsUsed++;
  saveUserState();
  updateUsageDisplay();

  // Показать предупреждение если осталось мало
  const remaining = userState.requestsLimit - userState.requestsUsed;
  if (remaining === 3) {
    showToast('Осталось 3 запроса', 'warning');
  } else if (remaining === 0) {
    showToast('Лимит запросов исчерпан', 'error');
  }
}

function getRemainingRequests() {
  if (userState.plan === 'unlimited') return Infinity;
  return Math.max(0, userState.requestsLimit - userState.requestsUsed);
}

// ===== ACTIONS =====
function savePersonalization(context) {
  localStorage.setItem('sheetgpt_context', context);
  showToast('Контекст сохранён', 'success');
}

function handlePurchase() {
  // TODO: Интеграция с платёжной системой
  // Пока имитируем успешную покупку

  console.log('Starting purchase flow...');

  // Открыть ссылку на оплату или показать форму
  // window.open('https://sheetgpt.ru/checkout', '_blank');

  // Для демо - активируем сразу
  // activateUnlimited();

  showToast('Переход к оплате...', 'info');

  // Закрыть модал
  closeModal('upgradeModal');
}

function activateUnlimited() {
  userState.plan = 'unlimited';
  userState.requestsUsed = 0;
  saveUserState();
  updateUsageDisplay();
  showToast('Unlimited активирован! 🎉', 'success');
}

function handleLogout() {
  console.log('[SettingsMenu] Logout initiated');

  // Очистить ВСЕ данные
  localStorage.removeItem(LICENSE_STORAGE_KEY);      // Лицензионный ключ
  localStorage.removeItem(USER_DATA_STORAGE_KEY);    // Данные пользователя
  localStorage.removeItem('sheetgpt_context');       // Персонализация
  localStorage.removeItem('sheetgpt_history');       // История

  // Сбросить состояние
  userState = {
    username: null,
    first_name: null,
    telegram_user_id: null,
    plan: 'free',
    requestsUsed: 0,
    requestsLimit: 10,
  };

  showToast('Выход выполнен', 'info');

  // Закрыть dropdown
  document.getElementById('settingsDropdown')?.classList.remove('show');

  // Показать экран активации (не перезагружать страницу)
  setTimeout(() => {
    const overlay = document.getElementById('licenseOverlay');
    if (overlay) {
      overlay.classList.remove('hidden');
      console.log('[SettingsMenu] License overlay shown');
    } else {
      // Fallback: перезагрузить страницу
      location.reload();
    }
  }, 500);
}

// ===== TOAST NOTIFICATIONS =====
function showToast(message, type = 'info') {
  // Удалить существующий toast
  document.querySelector('.toast')?.remove();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-message">${message}</span>
  `;

  document.body.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  // Auto remove
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ===== ДОБАВИТЬ СТИЛИ TOAST =====
const toastStyles = document.createElement('style');
toastStyles.textContent = `
  .toast {
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: var(--ink-primary);
    color: var(--ink-inverse);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-md);
    font-size: 13px;
    font-weight: 500;
    box-shadow: var(--shadow-lg);
    opacity: 0;
    transition: all var(--duration-normal) var(--ease-out-expo);
    z-index: 9999;
  }

  .toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }

  .toast-success {
    background: var(--data-success);
  }

  .toast-warning {
    background: var(--data-warning);
  }

  .toast-error {
    background: var(--data-error);
  }

  .toast-info {
    background: var(--data-info);
  }
`;
document.head.appendChild(toastStyles);

// ===== ЭКСПОРТ ДЛЯ ИСПОЛЬЗОВАНИЯ В ДРУГИХ ФАЙЛАХ =====
window.SheetGPTSettings = {
  canMakeRequest,
  incrementRequestCount,
  getRemainingRequests,
  updateUsageDisplay,
  openUpgradeModal: () => openModal('upgradeModal'),
  showToast,
  getUserState: () => ({ ...userState }),
  // Установка данных пользователя из sidebar.js
  setUserData,
  setPlan: (plan) => {
    userState.plan = plan;
    if (plan === 'premium' || plan === 'unlimited') {
      userState.requestsUsed = 0;
    }
    saveUserState();
    updateUsageDisplay();
  }
};
