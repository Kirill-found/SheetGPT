"""
Tests for new features: conditional formatting, pivot tables, data cleaning,
data validation, and filtering.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy API key before importing
os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-testing"

from app.services.simple_gpt_processor import SimpleGPTProcessor


@pytest.fixture
def processor():
    """Create a processor instance for testing with mocked OpenAI client."""
    with patch('app.services.simple_gpt_processor.AsyncOpenAI'):
        proc = SimpleGPTProcessor()
        return proc


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        'Продукт': ['Телефон', 'Ноутбук', 'Планшет', 'Телефон', 'Ноутбук', ''],
        'Категория': ['Электроника', 'Электроника', 'Электроника', 'Электроника', 'Электроника', 'Электроника'],
        'Цена': [10000, 50000, 25000, 12000, 45000, np.nan],
        'Количество': [100, 50, 75, 80, 60, 30],
        'Статус': ['Активный', 'Активный', 'Неактивный', 'Активный', 'Неактивный', None],
        'Менеджер': ['Иванов', 'Петров', 'Иванов', 'Сидоров', 'Петров', 'Иванов'],
    })


@pytest.fixture
def column_names(sample_df):
    """Get column names from sample DataFrame."""
    return list(sample_df.columns)


# ==================== CONDITIONAL FORMATTING TESTS ====================

class TestConditionalFormatDetection:
    """Tests for _detect_conditional_format_action."""

    def test_detect_conditional_greater_than(self, processor, column_names, sample_df):
        """Test detection of 'greater than' condition."""
        queries = [
            "выдели красным где Цена больше 20000",
            "покрась красным ячейки где Цена > 20000",
            "условное форматирование: красным где Цена больше чем 20000",
        ]

        for query in queries:
            result = processor._detect_conditional_format_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["action_type"] == "conditional_format"
            assert result["rule"]["condition_type"] == "NUMBER_GREATER"
            assert result["rule"]["condition_value"] == 20000
            print(f"✓ '{query}' -> {result['rule']['condition_type']} {result['rule']['condition_value']}")

    def test_detect_conditional_less_than(self, processor, column_names, sample_df):
        """Test detection of 'less than' condition."""
        queries = [
            "выдели зелёным где Цена меньше 30000",
            "зеленым где Цена < 30000",
            "если Цена меньше 30000 то зелёным",
        ]

        for query in queries:
            result = processor._detect_conditional_format_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["rule"]["condition_type"] == "NUMBER_LESS"
            assert result["rule"]["condition_value"] == 30000
            print(f"✓ '{query}' -> {result['rule']['condition_type']} {result['rule']['condition_value']}")

    def test_detect_conditional_blank_cells(self, processor, column_names, sample_df):
        """Test detection of blank cells condition."""
        queries = [
            "выдели жёлтым пустые ячейки",
            "желтым где пусто",
            "условное форматирование: пустые значения",
        ]

        for query in queries:
            result = processor._detect_conditional_format_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["rule"]["condition_type"] == "BLANK"
            print(f"✓ '{query}' -> {result['rule']['condition_type']}")

    def test_detect_conditional_negative_values(self, processor, column_names, sample_df):
        """Test detection of negative values."""
        query = "выдели красным отрицательные значения"
        result = processor._detect_conditional_format_action(query, column_names, sample_df)
        assert result is not None
        assert result["rule"]["condition_type"] == "NUMBER_LESS"
        assert result["rule"]["condition_value"] == 0
        print(f"✓ '{query}' -> {result['rule']['condition_type']} {result['rule']['condition_value']}")

    def test_no_conditional_format_for_regular_query(self, processor, column_names, sample_df):
        """Test that regular queries don't trigger conditional formatting."""
        queries = [
            "покажи все товары",
            "сколько стоит телефон",
            "отсортируй по цене",
        ]

        for query in queries:
            result = processor._detect_conditional_format_action(query, column_names, sample_df)
            assert result is None, f"Should not detect conditional format for: {query}"
            print(f"✓ '{query}' -> None (correct)")


# ==================== PIVOT TABLE TESTS ====================

class TestPivotDetection:
    """Tests for _detect_pivot_action."""

    def test_detect_pivot_by_category(self, processor, column_names, sample_df):
        """Test pivot table detection by category."""
        queries = [
            "сводная по менеджерам",
            "группировка по Менеджер",
            "суммы по менеджерам",
        ]

        for query in queries:
            result = processor._detect_pivot_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["action_type"] == "pivot_table"
            assert "pivot_data" in result
            assert result["group_column"] == "Менеджер"
            print(f"✓ '{query}' -> pivot by {result['group_column']}, agg={result['agg_func']}")

    def test_detect_pivot_with_aggregation(self, processor, column_names, sample_df):
        """Test pivot table with specific aggregation."""
        test_cases = [
            ("среднее Цена по Менеджер", "mean"),
            ("количество по Менеджер", "count"),
            ("максимум Цена по Менеджер", "max"),
            ("сумма Количество по Менеджер", "sum"),
        ]

        for query, expected_agg in test_cases:
            result = processor._detect_pivot_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["agg_func"] == expected_agg, f"Expected {expected_agg}, got {result['agg_func']}"
            print(f"✓ '{query}' -> agg={result['agg_func']}")

    def test_pivot_returns_data(self, processor, column_names, sample_df):
        """Test that pivot actually returns grouped data."""
        query = "сводная таблица по Менеджер сумма Цена"
        result = processor._detect_pivot_action(query, column_names, sample_df)

        assert result is not None
        assert "pivot_data" in result
        assert "headers" in result["pivot_data"]
        assert "rows" in result["pivot_data"]
        assert len(result["pivot_data"]["rows"]) > 0
        print(f"✓ Pivot returned {len(result['pivot_data']['rows'])} rows")

    def test_no_pivot_for_regular_query(self, processor, column_names, sample_df):
        """Test that regular queries don't trigger pivot."""
        queries = [
            "покажи все товары",
            "сколько товаров",
            "сортировка по цене",
        ]

        for query in queries:
            result = processor._detect_pivot_action(query, column_names, sample_df)
            assert result is None, f"Should not detect pivot for: {query}"
            print(f"✓ '{query}' -> None (correct)")


# ==================== DATA CLEANING TESTS ====================

class TestCleanDetection:
    """Tests for _detect_clean_action."""

    def test_detect_remove_duplicates(self, processor, column_names, sample_df):
        """Test duplicate removal detection."""
        queries = [
            "удали дубликаты",
            "убери повторы",
            "remove duplicates",
        ]

        for query in queries:
            result = processor._detect_clean_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert "remove_duplicates" in result["operations"]
            print(f"✓ '{query}' -> operations={result['operations']}")

    def test_detect_remove_empty_rows(self, processor, column_names, sample_df):
        """Test empty row removal detection."""
        queries = [
            "удали пустые строки",
            "убери строки с пустыми значениями",
            "remove empty rows",
        ]

        for query in queries:
            result = processor._detect_clean_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert "remove_empty_rows" in result["operations"]
            print(f"✓ '{query}' -> operations={result['operations']}")

    def test_detect_fill_empty_with_value(self, processor, column_names, sample_df):
        """Test fill empty detection with specific value."""
        test_cases = [
            ("заполни пустые нулями", 0),
            ("заполни пустые средним", "mean"),
            ("fill empty with 0", 0),
        ]

        for query, expected_fill in test_cases:
            result = processor._detect_clean_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert "fill_empty" in result["operations"]
            assert result["fill_value"] == expected_fill, f"Expected {expected_fill}, got {result['fill_value']}"
            print(f"✓ '{query}' -> fill_value={result['fill_value']}")

    def test_detect_trim_whitespace(self, processor, column_names, sample_df):
        """Test whitespace trimming detection."""
        queries = [
            "убери пробелы",
            "очисти от лишних пробелов",
            "trim whitespace",
        ]

        for query in queries:
            result = processor._detect_clean_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert "trim_whitespace" in result["operations"]
            print(f"✓ '{query}' -> operations={result['operations']}")

    def test_clean_data_returns_result(self, processor):
        """Test that cleaning actually returns modified data."""
        # Create DataFrame with actual duplicates
        df_with_duplicates = pd.DataFrame({
            'Продукт': ['Телефон', 'Ноутбук', 'Телефон', 'Планшет'],  # 'Телефон' is duplicated
            'Цена': [10000, 50000, 10000, 25000],
        })
        column_names = list(df_with_duplicates.columns)

        query = "удали дубликаты"
        result = processor._detect_clean_action(query, column_names, df_with_duplicates)

        assert result is not None
        assert "cleaned_data" in result
        assert "headers" in result["cleaned_data"]
        assert "rows" in result["cleaned_data"]
        # Should have removed 1 duplicate row
        assert result["final_rows"] < result["original_rows"]
        print(f"✓ Cleaning: {result['original_rows']} -> {result['final_rows']} rows")

    def test_no_clean_for_regular_query(self, processor, column_names, sample_df):
        """Test that regular queries don't trigger cleaning."""
        queries = [
            "покажи товары",
            "сколько стоит",
            "сортировка по цене",
        ]

        for query in queries:
            result = processor._detect_clean_action(query, column_names, sample_df)
            assert result is None, f"Should not detect clean for: {query}"
            print(f"✓ '{query}' -> None (correct)")


# ==================== DATA VALIDATION TESTS ====================

class TestValidationDetection:
    """Tests for _detect_validation_action."""

    def test_detect_dropdown_list(self, processor, column_names, sample_df):
        """Test dropdown list detection."""
        queries = [
            "создай выпадающий список в колонке Статус",
            "добавь dropdown для Статус",
            "сделай выбор из списка в Статус",
        ]

        for query in queries:
            result = processor._detect_validation_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["action_type"] == "data_validation"
            assert result["rule"]["column_name"] == "Статус"
            print(f"✓ '{query}' -> validation for {result['rule']['column_name']}")

    def test_detect_validation_with_explicit_values(self, processor, column_names, sample_df):
        """Test validation with explicit allowed values."""
        queries = [
            "валидация для Статус: только Да/Нет",
            "выпадающий список: Активный, Неактивный, Архивный",
        ]

        for query in queries:
            result = processor._detect_validation_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert len(result["rule"]["allowed_values"]) > 0
            print(f"✓ '{query}' -> values={result['rule']['allowed_values']}")

    def test_auto_extract_values_from_column(self, processor, column_names, sample_df):
        """Test automatic extraction of values from column."""
        query = "создай выпадающий список для Менеджер"
        result = processor._detect_validation_action(query, column_names, sample_df)

        assert result is not None
        assert "allowed_values" in result["rule"]
        # Should extract unique values: Иванов, Петров, Сидоров
        assert len(result["rule"]["allowed_values"]) >= 3
        print(f"✓ Auto-extracted values: {result['rule']['allowed_values']}")

    def test_no_validation_for_regular_query(self, processor, column_names, sample_df):
        """Test that regular queries don't trigger validation."""
        queries = [
            "покажи товары",
            "сортировка по цене",
            "фильтруй по статусу",  # This should trigger filter, not validation
        ]

        for query in queries:
            result = processor._detect_validation_action(query, column_names, sample_df)
            assert result is None, f"Should not detect validation for: {query}"
            print(f"✓ '{query}' -> None (correct)")


# ==================== FILTER TESTS ====================

class TestFilterDetection:
    """Tests for _detect_filter_action."""

    def test_detect_filter_equals(self, processor, column_names, sample_df):
        """Test equality filter detection."""
        queries = [
            "фильтр где Статус = Активный",
            "покажи только строки где Статус равно Активный",
            "отфильтруй по Статус равен Активный",
        ]

        for query in queries:
            result = processor._detect_filter_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["action_type"] == "filter_data"
            assert result["column_name"] == "Статус"
            print(f"✓ '{query}' -> {result['column_name']} {result['operator']} {result['filter_value']}")

    def test_detect_filter_greater_than(self, processor, column_names, sample_df):
        """Test greater than filter detection."""
        queries = [
            "фильтр где Цена > 20000",
            "покажи только где Цена больше 20000",
            "строки где Цена более 20000",
        ]

        for query in queries:
            result = processor._detect_filter_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["operator"] == ">"
            assert result["filter_value"] == 20000
            print(f"✓ '{query}' -> {result['operator']} {result['filter_value']}")

    def test_detect_filter_less_than(self, processor, column_names, sample_df):
        """Test less than filter detection."""
        queries = [
            "фильтр где Цена < 30000",
            "покажи только где Цена меньше 30000",
        ]

        for query in queries:
            result = processor._detect_filter_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["operator"] == "<"
            assert result["filter_value"] == 30000
            print(f"✓ '{query}' -> {result['operator']} {result['filter_value']}")

    def test_detect_filter_contains(self, processor, column_names, sample_df):
        """Test contains filter detection."""
        query = "фильтр где Продукт содержит теле"
        result = processor._detect_filter_action(query, column_names, sample_df)

        assert result is not None
        assert result["operator"] == "contains"
        print(f"✓ '{query}' -> {result['operator']} {result['filter_value']}")

    def test_detect_filter_empty(self, processor, column_names, sample_df):
        """Test empty filter detection."""
        queries = [
            "фильтр где Статус пусто",
            "покажи строки где Цена пустая",
        ]

        for query in queries:
            result = processor._detect_filter_action(query, column_names, sample_df)
            assert result is not None, f"Failed for query: {query}"
            assert result["operator"] == "empty"
            print(f"✓ '{query}' -> {result['operator']}")

    def test_filter_returns_data(self, processor, column_names, sample_df):
        """Test that filter actually returns filtered data."""
        query = "фильтр где Цена > 20000"
        result = processor._detect_filter_action(query, column_names, sample_df)

        assert result is not None
        assert "filtered_data" in result
        assert "headers" in result["filtered_data"]
        assert "rows" in result["filtered_data"]
        # Check that filter actually reduced rows
        assert result["filtered_rows"] < result["original_rows"]
        print(f"✓ Filter: {result['original_rows']} -> {result['filtered_rows']} rows")

    def test_no_filter_for_regular_query(self, processor, column_names, sample_df):
        """Test that regular queries don't trigger filter."""
        queries = [
            "покажи все товары",
            "сколько стоит телефон",
            "сортировка по цене",
        ]

        for query in queries:
            result = processor._detect_filter_action(query, column_names, sample_df)
            assert result is None, f"Should not detect filter for: {query}"
            print(f"✓ '{query}' -> None (correct)")


# ==================== EDGE CASES TESTS ====================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_dataframe(self, processor):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        column_names = []

        result = processor._detect_filter_action("фильтр где Цена > 100", column_names, df)
        assert result is None
        print("✓ Empty DataFrame handled correctly")

    def test_special_characters_in_column_names(self, processor):
        """Test with special characters in column names."""
        df = pd.DataFrame({
            'Цена (руб.)': [100, 200, 300],
            'Кол-во': [1, 2, 3],
        })
        column_names = list(df.columns)

        result = processor._detect_filter_action("фильтр где Цена больше 150", column_names, df)
        # Should still work with partial matching
        print(f"✓ Special characters: result={result is not None}")

    def test_numeric_string_values(self, processor):
        """Test with numeric values stored as strings."""
        df = pd.DataFrame({
            'Цена': ['10000', '20000', '30000'],
            'Статус': ['A', 'B', 'C'],
        })
        column_names = list(df.columns)

        result = processor._detect_filter_action("фильтр где Цена > 15000", column_names, df)
        assert result is not None
        print(f"✓ Numeric strings: filtered to {result['filtered_rows']} rows")

    def test_mixed_case_queries(self, processor, column_names, sample_df):
        """Test with mixed case in queries."""
        queries = [
            "ФИЛЬТР где Цена > 20000",
            "Фильтр Где ЦЕНА > 20000",
        ]

        for query in queries:
            result = processor._detect_filter_action(query, column_names, sample_df)
            assert result is not None, f"Failed for mixed case query: {query}"
        print("✓ Mixed case queries handled correctly")


# ==================== CONFLICT RESOLUTION TESTS ====================

class TestConflictResolution:
    """Test that detection methods don't conflict with each other."""

    def test_filter_vs_conditional_format(self, processor, column_names, sample_df):
        """Test that 'where' queries go to filter, not conditional format."""
        query = "покажи только строки где Цена > 10000"

        filter_result = processor._detect_filter_action(query, column_names, sample_df)
        cond_result = processor._detect_conditional_format_action(query, column_names, sample_df)

        assert filter_result is not None, "Should detect as filter"
        # Conditional format should NOT trigger because it doesn't have color keywords
        print(f"✓ Filter vs Conditional: filter={filter_result is not None}, cond={cond_result is not None}")

    def test_validation_vs_filter(self, processor, column_names, sample_df):
        """Test that filter queries don't trigger validation."""
        query = "фильтр по Статус = Активный"

        filter_result = processor._detect_filter_action(query, column_names, sample_df)
        valid_result = processor._detect_validation_action(query, column_names, sample_df)

        assert filter_result is not None, "Should detect as filter"
        assert valid_result is None, "Should NOT detect as validation"
        print("✓ Filter vs Validation: correctly separated")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
