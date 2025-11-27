/**
 * SheetGPT - Settings Menu Logic
 * Управление меню настроек, тарифами, usage bar
 */

console.log('[SettingsMenu] 📜 settings-menu.js loading...');

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

// ===== ШАБЛОНЫ РОЛЕЙ ДЛЯ ПЕРСОНАЛИЗАЦИИ =====
const ROLE_TEMPLATES = {
  'small-business': {
    name: "Малый бизнес",
    color: "#84CC16",
    prompt: `Ты опытный бизнес-консультант для владельцев малого и среднего бизнеса.
Анализируй данные с позиции собственника, который принимает стратегические решения.

КЛЮЧЕВЫЕ МЕТРИКИ И ФОРМУЛЫ:
• Валовая прибыль = Выручка - Себестоимость
• Чистая прибыль = Валовая прибыль - Операционные расходы - Налоги
• Маржинальность = (Выручка - Переменные затраты) / Выручка × 100%
  - Низкая: < 20% (требует оптимизации)
  - Нормальная: 20-40%
  - Высокая: > 40%
• Точка безубыточности = Постоянные расходы / Маржинальность
• Оборачиваемость запасов = Себестоимость / Средний остаток запасов

ФОКУС АНАЛИЗА:
- Выявляй самые прибыльные и убыточные направления
- Отслеживай динамику: рост/падение относительно прошлых периодов
- Ищи скрытые резервы для оптимизации затрат
- Оценивай риски: зависимость от крупных клиентов, сезонность
- Прогнозируй cash flow и потребность в оборотном капитале

ФОРМАТ ОТВЕТА:
Давай конкретные цифры, проценты и сравнения. Выводы должны быть actionable — что конкретно делать.`
  },

  'sales': {
    name: "Продажи",
    color: "#F59E0B",
    prompt: `Ты эксперт по продажам и руководитель отдела продаж с 10+ летним опытом.
Анализируй данные через призму воронки продаж и эффективности команды.

КЛЮЧЕВЫЕ МЕТРИКИ И ФОРМУЛЫ:
• Конверсия этапа = (Перешли на след. этап / Всего на этапе) × 100%
  - Лид → Квалификация: норма 30-50%
  - Квалификация → Презентация: норма 40-60%
  - Презентация → КП: норма 50-70%
  - КП → Сделка: норма 20-40%
• Средний чек = Общая выручка / Количество сделок
• LTV = Средний чек × Среднее кол-во покупок × Срок жизни клиента
• CAC = Затраты на привлечение / Количество новых клиентов
• LTV/CAC ratio: здоровый показатель > 3
• Цикл сделки = Среднее время от первого контакта до оплаты
• Win Rate = Выигранные сделки / Все завершённые сделки × 100%

ФОКУС АНАЛИЗА:
- Выявляй узкие места воронки (где теряем больше всего)
- Сравнивай эффективность менеджеров: конверсии, средний чек, скорость
- Анализируй причины отказов и проигранных сделок
- Отслеживай выполнение плана: факт vs план, динамика по неделям
- Сегментируй по источникам лидов, продуктам, регионам

ФОРМАТ ОТВЕТА:
Структурируй по этапам воронки. Подсвечивай проблемные зоны и точки роста. Давай рекомендации по улучшению конверсии.`
  },

  'finance': {
    name: "Финансы",
    color: "#3B82F6",
    prompt: `Ты финансовый директор (CFO) с экспертизой в управленческом учёте и финансовом анализе.
Анализируй данные с точки зрения финансовой устойчивости и эффективности.

КЛЮЧЕВЫЕ МЕТРИКИ И ФОРМУЛЫ:
• EBITDA = Операционная прибыль + Амортизация
• Рентабельность продаж (ROS) = Чистая прибыль / Выручка × 100%
• ROE = Чистая прибыль / Собственный капитал × 100%
• ROA = Чистая прибыль / Активы × 100%
• ROI = (Доход - Инвестиции) / Инвестиции × 100%
• Коэффициент текущей ликвидности = Оборотные активы / Краткосрочные обязательства
  - Критично: < 1
  - Норма: 1.5-2.5
  - Избыток ликвидности: > 3
• DSO (Days Sales Outstanding) = (Дебиторка / Выручка) × 365
• DPO (Days Payable Outstanding) = (Кредиторка / Себестоимость) × 365
• Cash Conversion Cycle = DSO + DIO - DPO

ФОКУС АНАЛИЗА:
- Структура доходов и расходов, динамика по периодам
- Cash flow: операционный, инвестиционный, финансовый
- Дебиторская задолженность: просрочки, aging analysis
- Кредиторская задолженность: график платежей
- Бюджет vs факт: отклонения и их причины
- Финансовые риски и stress-тесты

ФОРМАТ ОТВЕТА:
Используй профессиональную финансовую терминологию. Давай выводы с точными цифрами и процентами. Указывай на риски и возможности.`
  },

  'analyst': {
    name: "Аналитик",
    color: "#8B5CF6",
    prompt: `Ты senior data analyst с экспертизой в статистике и бизнес-аналитике.
Ищи паттерны, аномалии и скрытые инсайты в данных.

МЕТОДЫ АНАЛИЗА:
• Описательная статистика: среднее, медиана, мода, стандартное отклонение
• Анализ распределения: нормальность, выбросы, квартили
• Корреляционный анализ: поиск связей между переменными
• Временные ряды: тренд, сезонность, цикличность
• Когортный анализ: поведение групп во времени
• ABC/XYZ анализ: классификация по важности и стабильности
• Парето-анализ: правило 80/20

ДЕТЕКЦИЯ АНОМАЛИЙ:
- Выбросы: значения за пределами 1.5×IQR или 3σ
- Резкие изменения: отклонение > 20% от скользящего среднего
- Пропуски данных: паттерны отсутствующих значений
- Дубликаты и несоответствия

ФОКУС АНАЛИЗА:
- Сегментация данных по ключевым признакам
- Поиск скрытых закономерностей и корреляций
- Выявление трендов и прогнозирование
- Формирование и проверка гипотез
- Визуализация для презентации выводов

ФОРМАТ ОТВЕТА:
Структурируй анализ: данные → методология → находки → выводы → рекомендации. Указывай степень уверенности в выводах и ограничения анализа.`
  },

  'marketing': {
    name: "Маркетинг",
    color: "#EC4899",
    prompt: `Ты Head of Marketing с экспертизой в digital-маркетинге и аналитике.
Оценивай эффективность каналов, кампаний и маркетинговых инвестиций.

КЛЮЧЕВЫЕ МЕТРИКИ И ФОРМУЛЫ:
• CAC = Маркетинговые расходы / Новые клиенты
  - По каналам: paid, organic, referral, direct
• ROMI = (Доход от маркетинга - Расходы) / Расходы × 100%
  - Минимум для окупаемости: 100%
  - Хороший показатель: 300-500%
• CPL = Расходы на рекламу / Количество лидов
• CPA = Расходы на рекламу / Количество целевых действий
• CTR = Клики / Показы × 100%
• CR (Conversion Rate) = Конверсии / Визиты × 100%
• Bounce Rate = Отказы / Все сессии × 100%
• LTV:CAC — здоровый ratio > 3:1
• Payback Period = CAC / (ARPU × Gross Margin)

АТРИБУЦИЯ:
- Last Click, First Click, Linear, Time Decay, Position Based
- Мультиканальные последовательности

ФОКУС АНАЛИЗА:
- Эффективность каналов: какой канал приносит качественных клиентов
- Unit-экономика кампаний: CAC, LTV, Payback по сегментам
- A/B тесты: статистическая значимость результатов
- Воронка: где теряем пользователей
- Сезонность и тренды спроса

ФОРМАТ ОТВЕТА:
Группируй по каналам/кампаниям. Сравнивай с бенчмарками. Давай конкретные рекомендации по оптимизации бюджета.`
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
try {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  console.log('[SettingsMenu] 📜 settings-menu.js loaded successfully');
} catch (e) {
  console.error('[SettingsMenu] ❌ Error during init:', e);
}

function initSettingsMenu() {
  // Support both old (settingsBtn/settingsDropdown) and new (menuBtn/menuDropdown) element IDs
  const settingsBtn = document.getElementById('menuBtn') || document.getElementById('settingsBtn');
  const settingsDropdown = document.getElementById('menuDropdown') || document.getElementById('settingsDropdown');

  console.log('[SettingsMenu] settingsBtn:', settingsBtn);
  console.log('[SettingsMenu] settingsDropdown:', settingsDropdown);

  // Note: If using new design, dropdown toggle is handled in inline scripts
  // So we skip setting up the toggle handler to avoid conflicts

  // Menu item handlers - personalize button handled by inline scripts in new design
  // This adds additional functionality (loading saved context)
  document.getElementById('personalizeBtn')?.addEventListener('click', () => {
    if (settingsDropdown) settingsDropdown.classList.remove('show');

    // Reset and reload state when opening modal - support both old and new IDs
    const contextInput = document.getElementById('promptField') || document.getElementById('customContextInput');
    const promptIndicator = document.getElementById('promptIndicator');
    const charCount = document.getElementById('promptCounter') || document.getElementById('charCount');

    if (contextInput) {
      const savedContext = localStorage.getItem('sheetgpt_context') || '';
      contextInput.value = savedContext;
      const maxLen = contextInput.getAttribute('maxlength') || 2000;
      if (charCount) charCount.textContent = `${savedContext.length}/${maxLen}`;

      // Reset all role cards and preset buttons
      document.querySelectorAll('.role-card').forEach(c => c.classList.remove('selected'));
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      if (promptIndicator) promptIndicator.style.background = 'var(--accent-primary)';

      // Detect if saved context matches a role template
      for (const [roleId, roleData] of Object.entries(ROLE_TEMPLATES)) {
        if (savedContext.trim() === roleData.prompt.trim()) {
          const card = document.querySelector(`.role-card[data-role="${roleId}"]`);
          if (card) {
            card.classList.add('selected');
            if (promptIndicator) promptIndicator.style.background = roleData.color;
          }
          break;
        }
      }
    }

    openModal('personalizeModal');
  });

  document.getElementById('historyMenuBtn')?.addEventListener('click', () => {
    if (settingsDropdown) settingsDropdown.classList.remove('show');
    document.getElementById('historyDropdown')?.classList.toggle('show');
  });

  document.getElementById('upgradeBtn')?.addEventListener('click', () => {
    if (settingsDropdown) settingsDropdown.classList.remove('show');
    openModal('upgradeModal');
  });

  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    handleLogout();
  });
}

function initModals() {
  // Personalize modal - support both old and new element IDs
  const personalizeModal = document.getElementById('personalizeModal');
  const cancelPersonalizeBtn = document.getElementById('closePersonalize') || document.getElementById('cancelPersonalizeBtn');
  const savePersonalizeBtn = document.getElementById('savePrompt') || document.getElementById('savePersonalizeBtn');
  const contextInput = document.getElementById('promptField') || document.getElementById('customContextInput');
  const charCount = document.getElementById('promptCounter') || document.getElementById('charCount');

  // Note: Context loading and role selection happens in personalizeBtn click handler

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
    if (charCount) {
      const maxLen = contextInput.getAttribute('maxlength') || 2000;
      charCount.textContent = `${contextInput.value.length}/${maxLen}`;
    }
  });

  // Role card buttons (new design)
  const promptIndicator = document.getElementById('promptIndicator');

  document.querySelectorAll('.role-card').forEach(card => {
    card.addEventListener('click', () => {
      const role = card.getAttribute('data-role');
      const roleData = ROLE_TEMPLATES[role];

      if (roleData && contextInput) {
        // Set prompt text
        contextInput.value = roleData.prompt;
        if (charCount) charCount.textContent = contextInput.value.length;

        // Visual feedback - add selected class to clicked card only
        document.querySelectorAll('.role-card').forEach(c => {
          c.classList.remove('selected');
        });
        card.classList.add('selected');

        // Update prompt indicator color
        if (promptIndicator) {
          promptIndicator.style.background = roleData.color;
        }

        showToast(`Загружен шаблон: ${roleData.name}`, 'success');
      }
    });
  });

  // Clear context button - support both old and new element IDs
  const clearBtn = document.getElementById('clearPrompt') || document.getElementById('clearContextBtn');
  clearBtn?.addEventListener('click', () => {
    if (contextInput) {
      contextInput.value = '';
      const maxLen = contextInput.getAttribute('maxlength') || 2000;
      if (charCount) charCount.textContent = `0/${maxLen}`;

      // Reset all role cards selection
      document.querySelectorAll('.role-card').forEach(c => {
        c.classList.remove('selected');
      });
      // Also reset preset buttons if present
      document.querySelectorAll('.preset-btn').forEach(b => {
        b.classList.remove('active');
      });

      // Reset prompt indicator to default
      if (promptIndicator) {
        promptIndicator.style.background = 'var(--accent-primary)';
      }
    }
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
  // premium или unlimited = безлимит
  if (userState.plan === 'unlimited' || userState.plan === 'premium') return true;
  // queries_limit = -1 также означает безлимит
  if (userState.requestsLimit === -1) return true;
  return userState.requestsUsed < userState.requestsLimit;
}

function incrementRequestCount() {
  if (userState.plan === 'unlimited' || userState.plan === 'premium') return;
  if (userState.requestsLimit === -1) return;

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
  if (userState.plan === 'unlimited' || userState.plan === 'premium') return Infinity;
  if (userState.requestsLimit === -1) return Infinity;
  return Math.max(0, userState.requestsLimit - userState.requestsUsed);
}

// ===== ACTIONS =====
function savePersonalization(context) {
  localStorage.setItem('sheetgpt_context', context);

  // Также сохраняем в chrome.storage через postMessage к content script
  window.parent.postMessage({
    type: 'SHEETGPT_SAVE_CONTEXT',
    context: context
  }, '*');

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
  const dropdown = document.getElementById('menuDropdown') || document.getElementById('settingsDropdown');
  if (dropdown) dropdown.classList.remove('show');

  // Показать экран активации (не перезагружать страницу)
  setTimeout(() => {
    const overlay = document.getElementById('licenseScreen') || document.getElementById('licenseOverlay');
    if (overlay) {
      overlay.classList.remove('hidden');
      overlay.style.display = '';
      console.log('[SettingsMenu] License screen shown');
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
