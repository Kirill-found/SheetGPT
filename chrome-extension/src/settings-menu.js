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

// ===== СОСТОЯНИЕ =====
let userState = {
  email: 'user@example.com',
  plan: 'free', // 'free' | 'unlimited'
  requestsUsed: 7,
  requestsLimit: 10,
  resetDate: null, // Date когда сбросится лимит
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

  cancelPersonalizeBtn?.addEventListener('click', () => {
    closeModal('personalizeModal');
  });

  savePersonalizeBtn?.addEventListener('click', () => {
    savePersonalization(contextInput.value);
    closeModal('personalizeModal');
  });

  contextInput?.addEventListener('input', () => {
    charCount.textContent = contextInput.value.length;
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
  // Загрузить из localStorage или от API
  const saved = localStorage.getItem('sheetgpt_user');
  if (saved) {
    try {
      userState = { ...userState, ...JSON.parse(saved) };
    } catch (e) {
      console.error('Error loading user state:', e);
    }
  }

  // Проверить сброс лимита
  checkLimitReset();
}

function saveUserState() {
  localStorage.setItem('sheetgpt_user', JSON.stringify(userState));
}

function checkLimitReset() {
  if (userState.plan === 'unlimited') return;

  const now = new Date();
  const resetDate = userState.resetDate ? new Date(userState.resetDate) : null;

  if (!resetDate || now >= resetDate) {
    // Сбросить лимит
    userState.requestsUsed = 0;

    // Установить следующий сброс (завтра в полночь)
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    userState.resetDate = tomorrow.toISOString();

    saveUserState();
  }
}

// ===== USAGE DISPLAY =====
function updateUsageDisplay() {
  const emailEl = document.getElementById('userEmail');
  const badgeEl = document.getElementById('planBadge');
  const countEl = document.getElementById('usageCount');
  const barFillEl = document.getElementById('usageBarFill');
  const resetEl = document.getElementById('usageReset');
  const upgradeLinkEl = document.getElementById('upgradeBtn');

  // Email
  if (emailEl) {
    emailEl.textContent = userState.email;
  }

  // Plan badge
  if (badgeEl) {
    badgeEl.textContent = userState.plan === 'unlimited' ? 'UNLIMITED' : 'FREE';
    badgeEl.classList.toggle('unlimited', userState.plan === 'unlimited');
  }

  // Usage count & bar
  if (userState.plan === 'unlimited') {
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
      resetEl.textContent = getResetText();
    }

    if (upgradeLinkEl) upgradeLinkEl.style.display = 'inline-flex';
  }
}

function getResetText() {
  if (!userState.resetDate) return 'Обновление: завтра';

  const now = new Date();
  const reset = new Date(userState.resetDate);
  const diffMs = reset - now;
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffHours < 1) {
    const diffMins = Math.floor(diffMs / (1000 * 60));
    return `Обновление: ${diffMins} мин`;
  } else if (diffHours < 24) {
    return `Обновление: ${diffHours} ч`;
  } else {
    return 'Обновление: завтра';
  }
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
  // Очистить состояние
  localStorage.removeItem('sheetgpt_user');
  localStorage.removeItem('sheetgpt_context');
  localStorage.removeItem('sheetgpt_history');

  // Редирект или обновление
  // google.script.run.logout(); // Для Google Apps Script

  showToast('Выход выполнен', 'info');

  // Закрыть dropdown
  document.getElementById('settingsDropdown')?.classList.remove('show');

  // Перезагрузить или показать login
  setTimeout(() => {
    location.reload();
  }, 1000);
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
  setUserEmail: (email) => {
    userState.email = email;
    saveUserState();
    updateUsageDisplay();
  },
  setPlan: (plan) => {
    userState.plan = plan;
    if (plan === 'unlimited') {
      userState.requestsUsed = 0;
    }
    saveUserState();
    updateUsageDisplay();
  }
};
