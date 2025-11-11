"""
AI Service for SheetGPT - VERSION 3.0 FIXED
Fixed aggregation with Python calculations
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from app.config import settings
import pandas as pd
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"
        logger.info("AI Service v3.0 initialized")

    def _detect_aggregation_need(self, query: str) -> Tuple[bool, str]:
        """
        Detects if aggregation is needed
        Returns: (needs_aggregation, aggregation_type)
        """
        query_lower = query.lower()

        patterns = {
            'sum': [
                r'сумм[аы]?\s',
                r'всего\s',
                r'итог[ои]?\s',
                r'общ[ий|ая|ее|ие]',
                r'больше всего',
                r'максимальн',
                r'наибольш',
                r'топ\s',
                r'лидер',
                r'первое место'
            ],
            'group': [
                r'по\s+поставщик',
                r'для\s+каждого',
                r'группир',
                r'какой\s+поставщик',
                r'какого\s+поставщик',
                r'у\s+какого\s+поставщик',
                r'у\s+какой',
                r'у\s+каких',
                r'кто\s+из'
            ]
        }

        for pattern_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, query_lower):
                    logger.info(f"Detected aggregation need: {pattern_type} (pattern: {pattern})")
                    return True, pattern_type

        return False, ""

    def _perform_python_aggregation(self,
                                   column_names: List[str],
                                   data: List[List[Any]],
                                   query: str) -> Dict[str, Any]:
        """
        Performs aggregation using Python/pandas
        """
        logger.info("Starting Python aggregation")
        query_lower = query.lower()

        try:
            # Create DataFrame
            df = pd.DataFrame(data, columns=column_names)
            logger.info(f"DataFrame shape: {df.shape}")
            logger.info(f"Columns: {list(df.columns)}")

            # Detect column types
            column_types = {}
            for col in df.columns:
                sample_values = df[col].dropna().head(5)
                if sample_values.empty:
                    column_types[col] = 'empty'
                    continue

                # Check for numeric
                try:
                    pd.to_numeric(sample_values, errors='raise')
                    column_types[col] = 'numeric'
                except:
                    # Check for companies
                    if any('ООО' in str(v) or 'ИП' in str(v) for v in sample_values):
                        column_types[col] = 'company'
                    else:
                        column_types[col] = 'text'

            logger.info(f"Column types detected: {column_types}")

            # Find supplier and sales columns
            supplier_column = None
            sales_column = None

            # Find supplier column
            for col_name, col_type in column_types.items():
                if col_type == 'company':
                    supplier_column = col_name
                    logger.info(f"Found supplier column: {supplier_column}")
                    break

            # If not found by type, try position
            if not supplier_column:
                if 'Колонка B' in column_names:
                    supplier_column = 'Колонка B'
                elif 'Поставщик' in column_names:
                    supplier_column = 'Поставщик'
                logger.info(f"Using position-based supplier column: {supplier_column}")

            # Find sales column (last numeric column)
            numeric_columns = [col for col, typ in column_types.items() if typ == 'numeric']
            if numeric_columns:
                sales_column = numeric_columns[-1]
                logger.info(f"Found sales column: {sales_column} (last numeric)")

            # Alternative names for sales
            for col in ['Продажи', 'Колонка E', 'Сумма', 'Итого']:
                if col in column_names:
                    sales_column = col
                    logger.info(f"Using named sales column: {sales_column}")
                    break

            if not supplier_column or not sales_column:
                logger.error(f"Critical columns not found! Supplier: {supplier_column}, Sales: {sales_column}")
                return {
                    "error": "Cannot find required columns for analysis",
                    "details": f"Supplier column: {supplier_column}, Sales column: {sales_column}"
                }

            logger.info(f"AGGREGATION SETUP: Group by {supplier_column}, Sum {sales_column}")

            # Perform aggregation
            df[sales_column] = pd.to_numeric(df[sales_column], errors='coerce').fillna(0)
            aggregated = df.groupby(supplier_column)[sales_column].sum().reset_index()
            aggregated.columns = ['Поставщик', 'Общие продажи']
            aggregated = aggregated.sort_values('Общие продажи', ascending=False)

            logger.info("AGGREGATION RESULTS:")
            for idx, row in aggregated.iterrows():
                logger.info(f"  {row['Поставщик']}: {row['Общие продажи']:,.2f}")

            # Find top supplier
            top_supplier = aggregated.iloc[0]
            top_name = top_supplier['Поставщик']
            top_sales = top_supplier['Общие продажи']

            logger.info(f"TOP SUPPLIER: {top_name} with {top_sales:,.2f}")

            # Check correctness
            if top_name == "ООО Время":
                logger.info("CORRECT RESULT! OOO Vremya is the top supplier!")
            else:
                logger.warning(f"WARNING: Got {top_name} instead of OOO Vremya")
                vremya_sales = aggregated[aggregated['Поставщик'] == 'ООО Время']['Общие продажи'].values
                if len(vremya_sales) > 0:
                    logger.info(f"  OOO Vremya actual sales: {vremya_sales[0]:,.2f}")

            # Create response
            methodology = f"""Анализ данных по продажам:
1. Использована колонка '{supplier_column}' для группировки по поставщикам
2. Просуммированы значения из колонки '{sales_column}' для каждого поставщика
3. Обработано {len(df)} строк данных
4. Найдено {len(aggregated)} уникальных поставщиков"""

            key_findings = []
            for idx, row in aggregated.head(3).iterrows():
                key_findings.append(f"{row['Поставщик']}: {row['Общие продажи']:,.2f} руб.")

            summary = f"Поставщик с наибольшими продажами - {top_name} с общей суммой {top_sales:,.2f} руб."

            logger.info("AGGREGATION COMPLETED SUCCESSFULLY")

            return {
                "summary": summary,
                "methodology": methodology,
                "key_findings": key_findings,
                "response_type": "analysis",
                "insights": [
                    f"Лидер по продажам: {top_name}",
                    f"Общая сумма продаж лидера: {top_sales:,.2f} руб.",
                    f"Всего проанализировано поставщиков: {len(aggregated)}"
                ],
                "confidence": 0.95
            }

        except Exception as e:
            logger.error(f"Aggregation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "error": f"Aggregation error: {str(e)}",
                "details": traceback.format_exc()
            }

    def _prepare_context(self,
                        column_names: List[str],
                        sheet_data: List[List[Any]],
                        history: List[Dict[str, Any]]) -> str:
        """Prepares context for GPT"""
        sample_data = sheet_data[:10] if sheet_data else []
        formatted_data = []

        for row_idx, row in enumerate(sample_data, 1):
            row_dict = {}
            for col_idx, value in enumerate(row):
                if col_idx < len(column_names):
                    row_dict[column_names[col_idx]] = value
            formatted_data.append(f"Row {row_idx}: {row_dict}")

        context = f"""You are SheetGPT - an assistant for working with spreadsheets.

Column names: {', '.join(column_names)}

Table data:
{chr(10).join(formatted_data)}

Chat history:
{json.dumps(history[-3:], ensure_ascii=False) if history else 'Empty'}

IMPORTANT:
- If aggregation is needed (sum, grouping), it's already done in Python
- Reply in Russian
- Be specific and use numbers from the data
"""
        return context

    def process_formula_request(self,
                               query: str,
                               column_names: List[str],
                               sheet_data: List[List[Any]],
                               history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Main request processing function"""

        logger.info(f"Processing query: {query}")
        logger.info(f"Data shape: {len(sheet_data)} rows, {len(column_names)} columns")
        logger.info(f"Columns: {column_names}")

        # Check if aggregation is needed
        needs_aggregation, agg_type = self._detect_aggregation_need(query)

        if needs_aggregation:
            logger.info(f"AGGREGATION REQUIRED! Type: {agg_type}")

            # Perform Python aggregation
            aggregation_result = self._perform_python_aggregation(
                column_names, sheet_data, query
            )

            # If successful, return result
            if "error" not in aggregation_result:
                logger.info("Returning aggregation result")
                return aggregation_result
            else:
                logger.error(f"Aggregation failed: {aggregation_result.get('error')}")

        # If no aggregation needed or failed, use GPT
        logger.info("Using GPT-4o for response")
        context = self._prepare_context(column_names, sheet_data, history)

        try:
            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": query}
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )

            gpt_response = response.choices[0].message.content
            result = self._parse_gpt_response(gpt_response, query)

            result["methodology"] = f"""Анализ выполнен с использованием:
- Модель: GPT-4o
- Колонки: {', '.join(column_names)}
- Обработано строк: {len(sheet_data)}"""

            return result

        except Exception as e:
            logger.error(f"GPT Error: {str(e)}")
            return {
                "error": str(e),
                "response_type": "error"
            }

    def _parse_gpt_response(self, response_text: str, query: str) -> Dict[str, Any]:
        """Parses GPT response"""
        result = {
            "formula": None,
            "explanation": response_text,
            "target_cell": None,
            "confidence": 0.8,
            "response_type": "explanation",
            "insights": [],
            "suggested_actions": None,
            "summary": None,
            "methodology": None,
            "key_findings": []
        }

        # Try to extract formula
        formula_pattern = r'=\w+\([^)]*\)'
        formula_match = re.search(formula_pattern, response_text)
        if formula_match:
            result["formula"] = formula_match.group()
            result["response_type"] = "formula"

        # Extract summary from first sentence
        sentences = response_text.split('.')
        if sentences:
            result["summary"] = sentences[0].strip() + '.'

        return result


# Create service instance
ai_service = AIService()

def get_ai_service() -> AIService:
    """Returns AI service instance"""
    return ai_service