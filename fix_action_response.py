# Скрипт для исправления response_type="action" → "formula" для единичных формул

# Читаем файл
with open('backend/app/api/formula.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Старый код (строки 96-111)
old_code = '''        elif response_type == "action":
            # Для action plan возвращаем план действий
            response_data = FormulaResponse(
                formula=None,  # Нет формулы
                explanation=result.get("explanation", ""),
                insights=result.get("insights", []),  # Действия передаем в insights
                suggested_actions=None,
                target_cell=None,
                confidence=result["confidence"],
                response_type="action"
            )
            # Добавляем metadata из 2-step prompting
            response_dict = response_data.model_dump()
            response_dict["intent"] = result.get("intent")
            response_dict["depth"] = result.get("depth")
            return response_dict'''

# Новый код с оптимизацией
new_code = '''        elif response_type == "action":
            # ОПТИМИЗАЦИЯ: Если это единственное действие "insert_formula", возвращаем как простую формулу
            insights = result.get("insights", [])
            if len(insights) == 1 and insights[0].get("type") == "insert_formula":
                # Извлекаем формулу из action и возвращаем как обычный formula response
                formula_config = insights[0].get("config", {})
                return FormulaResponse(
                    formula=formula_config.get("formula"),
                    explanation=result.get("explanation", ""),
                    target_cell=formula_config.get("cell"),
                    confidence=result["confidence"],
                    response_type="formula"
                )

            # Для множественных actions возвращаем план действий
            response_data = FormulaResponse(
                formula=None,  # Нет формулы
                explanation=result.get("explanation", ""),
                insights=result.get("insights", []),  # Действия передаем в insights
                suggested_actions=None,
                target_cell=None,
                confidence=result["confidence"],
                response_type="action"
            )
            # Добавляем metadata из 2-step prompting
            response_dict = response_data.model_dump()
            response_dict["intent"] = result.get("intent")
            response_dict["depth"] = result.get("depth")
            return response_dict'''

# Заменяем
if old_code in content:
    content = content.replace(old_code, new_code)
    print('OK: Response optimization added!')
else:
    print('ERROR: Insertion point not found')
    exit(1)

# Записываем обратно
with open('backend/app/api/formula.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('File updated successfully!')
