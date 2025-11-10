"""AI Service for SheetGPT - Minimal v3.0"""

import re
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from app.config import settings
import pandas as pd

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"

    def _detect_aggregation_need(self, query: str) -> Tuple[bool, str]:
        query_lower = query.lower()
        patterns = [
            r'больше всего',
            r'у\s+какого',
            r'какой\s+поставщик',
            r'максимальн',
            r'топ\s',
            r'лидер'
        ]
        for pattern in patterns:
            if re.search(pattern, query_lower):
                return True, 'sum'
        return False, ""

    def _perform_python_aggregation(self, column_names: List[str], data: List[List[Any]], query: str) -> Dict[str, Any]:
        try:
            df = pd.DataFrame(data, columns=column_names)

            # Find supplier column (usually column B or contains company names)
            supplier_col = None
            for col in column_names:
                sample = df[col].dropna().head(3)
                if any('ООО' in str(v) or 'ИП' in str(v) for v in sample):
                    supplier_col = col
                    break

            if not supplier_col and 'Колонка B' in column_names:
                supplier_col = 'Колонка B'
            elif not supplier_col and 'Поставщик' in column_names:
                supplier_col = 'Поставщик'

            # Find sales column (usually last numeric column or column E)
            sales_col = None
            for col in reversed(column_names):
                try:
                    pd.to_numeric(df[col].dropna().head(3), errors='raise')
                    sales_col = col
                    break
                except:
                    continue

            if not sales_col and 'Колонка E' in column_names:
                sales_col = 'Колонка E'
            elif not sales_col and 'Продажи' in column_names:
                sales_col = 'Продажи'

            if not supplier_col or not sales_col:
                return {"error": "Cannot find columns"}

            # Aggregate
            df[sales_col] = pd.to_numeric(df[sales_col], errors='coerce').fillna(0)
            result = df.groupby(supplier_col)[sales_col].sum().reset_index()
            result.columns = ['supplier', 'total']
            result = result.sort_values('total', ascending=False)

            top = result.iloc[0]

            return {
                "summary": f"Поставщик с наибольшими продажами - {top['supplier']} с общей суммой {top['total']:,.2f} руб.",
                "methodology": f"Сгруппировано по колонке '{supplier_col}', просуммирована колонка '{sales_col}'",
                "key_findings": [f"{row['supplier']}: {row['total']:,.2f} руб." for _, row in result.head(3).iterrows()],
                "response_type": "analysis",
                "confidence": 0.95
            }
        except Exception as e:
            return {"error": str(e)}

    def process_formula_request(self, query: str, column_names: List[str], sheet_data: List[List[Any]], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        needs_agg, _ = self._detect_aggregation_need(query)

        if needs_agg:
            result = self._perform_python_aggregation(column_names, sheet_data, query)
            if "error" not in result:
                return result

        # Fallback to GPT
        try:
            context = f"Columns: {column_names}\nData: {sheet_data[:5]}\n"
            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": query}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            text = response.choices[0].message.content
            return {
                "formula": None,
                "explanation": text,
                "response_type": "explanation",
                "summary": text.split('.')[0] if '.' in text else text,
                "methodology": "GPT-4o analysis",
                "key_findings": []
            }
        except Exception as e:
            return {"error": str(e), "response_type": "error"}

ai_service = AIService()

def get_ai_service() -> AIService:
    return ai_service