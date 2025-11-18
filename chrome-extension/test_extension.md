# Инструкция по отладке Chrome Extension

## Шаг 1: Проверка загрузки расширения

1. Откройте Chrome: `chrome://extensions/`
2. Найдите **SheetGPT AI Assistant**
3. Кликните на **"Подробности"** (Details)
4. Нажмите **"Проверить представления: service worker"** (Inspect views: service worker)

### Что проверить в DevTools service worker:

```javascript
// В консоли должно быть:
[Background] Service worker started

// Проверьте, есть ли ошибки загрузки sheets-api.js:
// Не должно быть: "Failed to load sheets-api.js" или подобных ошибок
```

## Шаг 2: Проверка на странице Google Sheets

1. Откройте вашу таблицу Google Sheets
2. Откройте DevTools (F12)
3. Перейдите на вкладку Console

### Что проверить:

```javascript
// Должны быть логи:
[SheetGPT] Content script loaded
[SheetGPT] Sidebar opened

// Если есть ошибки типа:
// "Failed to execute 'importScripts' on 'WorkerGlobalScope'"
// Значит путь импорта неправильный
```

## Шаг 3: Проверка OAuth авторизации

В консоли service worker выполните:

```javascript
// Проверка токена
chrome.identity.getAuthToken({ interactive: false }, (token) => {
  console.log('Token:', token ? 'OK' : 'Missing');
  console.log('Error:', chrome.runtime.lastError);
});
```

## Шаг 4: Полная переустановка расширения

Если ничего не помогает:

1. Откройте `chrome://extensions/`
2. Нажмите **"Удалить"** на SheetGPT
3. Нажмите **"Загрузить распакованное расширение"**
4. Выберите папку: `C:\SheetGPT\chrome-extension`
5. Разрешите доступ к Google Sheets при первом запуске

## Шаг 5: Проверка правильности путей

Убедитесь, что файлы на месте:

```
chrome-extension/
├── manifest.json
├── src/
│   ├── background.js      ← importScripts('src/sheets-api.js')
│   ├── sheets-api.js      ← Должен быть здесь!
│   ├── content.js
│   └── sidebar.js
```

## Ожидаемые логи при успешной работе:

```
[Background] Service worker started
[SheetGPT] Content script loaded
[SheetGPT] Sidebar opened
[Sidebar] Calling google.script.run.processQuery
[SheetGPT] Processing query: выдели города...
[SheetGPT] Getting active sheet data...
[SheetsAPI] ✅ Got auth token
[SheetsAPI] Read data: {headers: [...], data: [...]}
[Background] ✅ Got sheet data
[SheetGPT] Sending request to backend...
[SheetGPT] ✅ Rows highlighted
```
