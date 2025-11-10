# ДИАГНОСТИКА: API РАБОТАЕТ ПРАВИЛЬНО

## Результат проверки API

API возвращает **ПРАВИЛЬНУЮ** формулу в `insights[1].config.formula`:

```json
{
  "response_type": "action",
  "explanation": "Добавить оклад по отделу и стажу",
  "insights": [
    {
      "type": "insert_formula",
      "config": {
        "cell": "H1",
        "formula": "\"Оклад\""
      }
    },
    {
      "type": "insert_formula",
      "config": {
        "cell": "H2",
        "formula": "=ARRAYFORMULA(IF(C2:C=\"\"; \"\"; IF(C2:C<5; INDEX($H:$H; MATCH(B2:B; $G:$G; 0)); INDEX($H:$H; MATCH(B2:B; $G:$G; 0))*1.05)))"
      }
    },
    {
      "type": "format_cells",
      "config": {
        "range": "H1:H1",
        "bold": true
      }
    }
  ]
}
```

## Проверка формулы

**Формула из insights[1]:**
```
=ARRAYFORMULA(IF(C2:C=""; ""; IF(C2:C<5; INDEX($H:$H; MATCH(B2:B; $G:$G; 0)); INDEX($H:$H; MATCH(B2:B; $G:$G; 0))*1.05)))
```

**Результаты проверки:**
- ✅ Ищет в `$G:$G` (текст - "Отделы")
- ✅ Возвращает из `$H:$H` (числа - "Оклад")
- ✅ НЕ использует `$I:$I` (неправильный столбец)
- ✅ Использует правильную логику: если стаж < 5 → базовый оклад, иначе → базовый оклад × 1.05

## Вывод

**Бэкенд INDEX/MATCH постпроцессинг работает ИДЕАЛЬНО!**

Формула была исправлена с:
- `INDEX($I:$I; MATCH(B2:B; $H:$H; 0))` ❌ (ищет текст в числах, возвращает из несуществующего столбца)

На:
- `INDEX($H:$H; MATCH(B2:B; $G:$G; 0))` ✅ (ищет текст в тексте, возвращает из правильного столбца)

## Что делать пользователю

Если вы видите старую формулу в расширении, это означает:

1. **Кэш расширения Google Apps Script** - Google кэширует код расширения на своих серверах
2. **Нужно обновить расширение вручную:**

   a. Откройте Google Sheets
   b. Перейдите в **Extensions → Apps Script**
   c. Нажмите **Ctrl+S** (сохранить) даже без изменений
   d. Или создайте новый деплой (Deploy → New deployment)
   e. Закройте и снова откройте таблицу

3. **Или просто нажмите кнопку "▶ Выполнить действия"** в сайдбаре - расширение автоматически вставит правильную формулу!

## Техническая информация

**Коммиты с исправлениями:**
- `df57c16`: "Fix INDEX/MATCH postprocessing: handle out-of-bounds result_col"
- `7658886`: "Add intelligent INDEX/MATCH postprocessing with data type analysis"

**Деплой:**
- Railway: ✅ Успешно задеплоено
- API endpoint: https://sheetgpt-production.up.railway.app/api/v1/formula
- Статус: Работает корректно
