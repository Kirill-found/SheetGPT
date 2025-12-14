# Fix personalization sync with state.customContext
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/sidebar.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''    document.getElementById('savePersonalizationBtn').addEventListener('click', () => {
      const selectedPreset = document.querySelector('.preset-card.selected');
      const presetId = selectedPreset ? selectedPreset.dataset.preset : 'analyst';
      const customContext = document.getElementById('personalizationContextInput').value;
      const personalization = { preset: presetId, customContext };
      localStorage.setItem('sheetgpt-personalization', JSON.stringify(personalization));
      const settingsContext = document.getElementById('customContextInput');
      if (settingsContext && customContext) {
        settingsContext.value = customContext;
        document.getElementById('charCount').textContent = customContext.length;
      }
      document.getElementById('personalizationModal').classList.remove('show');
    });'''

new_code = '''    document.getElementById('savePersonalizationBtn').addEventListener('click', () => {
      const selectedPreset = document.querySelector('.preset-card.selected');
      const presetId = selectedPreset ? selectedPreset.dataset.preset : 'analyst';
      const customContext = document.getElementById('personalizationContextInput').value;
      const personalization = { preset: presetId, customContext };
      localStorage.setItem('sheetgpt-personalization', JSON.stringify(personalization));
      const settingsContext = document.getElementById('customContextInput');
      if (settingsContext && customContext) {
        settingsContext.value = customContext;
        document.getElementById('charCount').textContent = customContext.length;
      }

      // ВАЖНО: Синхронизируем с state.customContext для API вызовов
      if (typeof savePersonalization === 'function') {
        // Вызываем функцию из sidebar.js которая обновляет state
        savePersonalization();
      } else {
        // Fallback: закрываем модалку
        document.getElementById('personalizationModal').classList.remove('show');
      }
    });'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed personalization sync')
else:
    print('ERROR: Pattern not found')
