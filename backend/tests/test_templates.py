"""
Тесты для template engine
"""

from app.services.template_matcher import TemplateMatcher

def test_sum_column():
    """Тест: сумма столбца"""
    matcher = TemplateMatcher()
    
    query = "Посчитай сумму продаж"
    columns = ["Товар", "Продажи", "Регион"]
    
    result = matcher.find_template(query, columns)
    
    assert result is not None
    template, params = result
    assert template.id == "sum_column"
    assert params["column"] == "B"  # Продажи
    
    print("✅ Test sum_column passed")

def test_full_name():
    """Тест: объединение ФИО"""
    matcher = TemplateMatcher()
    
    query = "Создай полное ФИО"
    columns = ["Фамилия", "Имя", "Отчество"]
    
    result = matcher.find_template(query, columns)
    
    assert result is not None
    template, params = result
    assert template.id == "concatenate_full_name"
    assert params["col1"] == "A"
    assert params["col2"] == "B"
    assert params["col3"] == "C"
    
    print("✅ Test full_name passed")

def test_vlookup():
    """Тест: VLOOKUP"""
    matcher = TemplateMatcher()
    
    query = "Найди цену товара"
    columns = ["Товар", "Количество"]
    
    result = matcher.find_template(query, columns)
    
    assert result is not None
    template, params = result
    assert template.id == "vlookup_basic"
    
    print("✅ Test vlookup passed")

if __name__ == "__main__":
    test_sum_column()
    test_full_name()
    test_vlookup()
    print("\n✅ All tests passed!")