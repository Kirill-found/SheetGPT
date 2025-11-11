"""AI Service for SheetGPT v5.1.0 - Integrated AI Code Executor for 99% accuracy"""

import re
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from app.config import settings
import pandas as pd
from app.services.ai_code_executor import get_ai_executor

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"

    def _detect_aggregation_need(self, query: str) -> Tuple[bool, str, str]:
        """
        Returns: (needs_aggregation, aggregation_type, group_by_what)
        group_by_what can be: 'product', 'supplier', or 'auto'
        """
        query_lower = query.lower()

        # Check what to group by
        group_by = 'auto'
        if any(word in query_lower for word in ['товар', 'продукт', 'product']):
            group_by = 'product'
        elif any(word in query_lower for word in ['поставщик', 'компан', 'supplier']):
            group_by = 'supplier'

        # Check if aggregation needed
        patterns = [
            r'больше всего',
            r'топ\s+\d+',
            r'у\s+какого',
            r'какой\s+',
            r'максимальн',
            r'лидер',
            r'первое место',
            r'топ\s+'
        ]

        for pattern in patterns:
            if re.search(pattern, query_lower):
                return True, 'sum', group_by

        return False, "", ""

    def _perform_python_aggregation(self, column_names: List[str], data: List[List[Any]], query: str) -> Dict[str, Any]:
        try:
            df = pd.DataFrame(data, columns=column_names)
            query_lower = query.lower()

            # Determine what to group by based on query
            group_col = None
            group_type = None

            # Check if asking about products/товары
            if any(word in query_lower for word in ['товар', 'продукт', 'product']):
                group_type = 'product'
                # Find product column (usually column A)
                if 'Колонка A' in column_names:
                    group_col = 'Колонка A'
                elif 'Товар' in column_names:
                    group_col = 'Товар'
                else:
                    # First text column
                    for col in column_names:
                        if df[col].dtype == 'object':
                            group_col = col
                            break

            # Check if asking about suppliers/поставщики
            elif any(word in query_lower for word in ['поставщик', 'компан', 'supplier']):
                group_type = 'supplier'
                # Find supplier column (contains company names)
                for col in column_names:
                    sample = df[col].dropna().head(3)
                    if any('ООО' in str(v) or 'ИП' in str(v) for v in sample):
                        group_col = col
                        break

                if not group_col:
                    if 'Колонка B' in column_names:
                        group_col = 'Колонка B'
                    elif 'Поставщик' in column_names:
                        group_col = 'Поставщик'

            # Default to supplier if not specified
            if not group_col:
                group_type = 'supplier'
                for col in column_names:
                    sample = df[col].dropna().head(3)
                    if any('ООО' in str(v) or 'ИП' in str(v) for v in sample):
                        group_col = col
                        break
                if not group_col and 'Колонка B' in column_names:
                    group_col = 'Колонка B'

            # Find sales column (usually last numeric or column E)
            sales_col = None
            for col in reversed(column_names):
                try:
                    pd.to_numeric(df[col].dropna().head(3), errors='raise')
                    sales_col = col
                    break
                except:
                    continue

            if not sales_col:
                if 'Колонка E' in column_names:
                    sales_col = 'Колонка E'
                elif 'Продажи' in column_names:
                    sales_col = 'Продажи'

            if not group_col or not sales_col:
                return {"error": f"Cannot find columns. Group: {group_col}, Sales: {sales_col}"}

            # Aggregate
            df[sales_col] = pd.to_numeric(df[sales_col], errors='coerce').fillna(0)
            result = df.groupby(group_col)[sales_col].sum().reset_index()
            result.columns = ['item', 'total']
            result = result.sort_values('total', ascending=False)

            # Format response based on what was asked
            top3 = result.head(3)
            item_type = "Товар" if group_type == 'product' else "Поставщик"

            # Create summary
            if 'топ' in query_lower and '3' in query_lower:
                summary = f"Топ 3 {item_type.lower()}а по продажам:\n"
                for idx, row in top3.iterrows():
                    summary += f"{idx+1}. {row['item']}: {row['total']:,.2f} руб.\n"
            else:
                top = result.iloc[0]
                summary = f"{item_type} с наибольшими продажами - {top['item']} с общей суммой {top['total']:,.2f} руб."

            return {
                "summary": summary.strip(),
                "methodology": f"Сгруппировано по колонке '{group_col}' ({item_type.lower()}ы), просуммирована колонка '{sales_col}' (продажи)",
                "key_findings": [f"{row['item']}: {row['total']:,.2f} руб." for _, row in top3.iterrows()],
                "response_type": "analysis",
                "confidence": 0.95
            }
        except Exception as e:
            return {"error": str(e)}

    def process_formula_request(self, query: str, column_names: List[str], sheet_data: List[List[Any]], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        v5.1.0: Uses AI Code Executor for 99% accuracy
        Supports ANY query: top products, averages, sums, counts, etc.
        """
        try:
            # Use AI Code Executor for ALL queries (not just aggregations)
            executor = get_ai_executor()
            result = executor.process_with_code(
                query=query,
                column_names=column_names,
                sheet_data=sheet_data,
                history=history or []
            )

            # If successful, return result
            if "error" not in result:
                return result

            # If AI Code Executor failed, fallback to old method
            print(f"⚠️ AI Code Executor failed: {result.get('error')}")
            print("📞 Falling back to old _perform_python_aggregation...")

            # Try old method as fallback
            needs_agg, agg_type, group_by = self._detect_aggregation_need(query)
            if needs_agg:
                fallback_result = self._perform_python_aggregation(column_names, sheet_data, query)
                if "error" not in fallback_result:
                    return fallback_result

            # Last resort: GPT text response
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
                "key_findings": [],
                "confidence": 0.7
            }
        except Exception as e:
            return {"error": str(e), "response_type": "error", "confidence": 0.0}

ai_service = AIService()

def get_ai_service() -> AIService:
    return ai_service