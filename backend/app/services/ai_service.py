from openai import AsyncOpenAI, RateLimitError
import json
import time
import asyncio
import re
from typing import List, Any, Dict, Optional
from app.core.config import settings
from app.services.formula_validator import FormulaValidator
from app.services.formula_fixer import FormulaFixer
from app.services.formula_executor import MockFormulaExecutor
from app.services.healing_service import HealingService
import pandas as pd
import numpy as np

# PHASE 1.3:   timeout  limits
# EMERGENCY DEPLOYMENT: 2025-11-10 15:00 UTC - v1.5.0 - GPT-4o ONLY (Railway cache issue)
MAX_HEAL_ATTEMPTS = 3
TOTAL_GENERATION_TIMEOUT = 30.0  # 
PER_ATTEMPT_TIMEOUT = 10.0  #     healing

# Retry settings for OpenAI rate limits
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # 
MAX_RETRY_DELAY = 10.0  #    


class AIService:
    """ AI   Google Sheets"""

    def __init__(self, openai_api_key: Optional[str] = None, enable_test_and_heal: bool = False):
        """
        Args:
            openai_api_key: OpenAI API key ( None,  settings.OPENAI_API_KEY)
            enable_test_and_heal:  Test-and-Heal loop ( Google credentials)
        """
        api_key = openai_api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"  # Upgraded from gpt-4o-mini for better reasoning

        # Validator & Fixer    
        self.validator = FormulaValidator()
        self.fixer = FormulaFixer()

        # Test-and-Heal  ()
        self.enable_test_and_heal = enable_test_and_heal
        if enable_test_and_heal:
            self.executor = MockFormulaExecutor()  # Mock  ,    
            self.healing_service = HealingService(self.client)
        else:
            self.executor = None
            self.healing_service = None

        # 
        self.stats = {
            "total_requests": 0,
            "template_hits": 0,
            "gpt_calls": 0,
            "auto_fixes": 0,
            "healing_attempts": 0,
            "healing_successes": 0
        }

    async def process_query(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None, history: List[dict] = None,
        selected_range: str = None, active_cell: str = None
    ) -> dict:
        """
          -     AI   

        Args:
            query:  
            column_names:  
            sample_data:  
            history:     
            selected_range:   ( 'H5:H17')
            active_cell:   ( 'H5')

        Returns:
            dict     
        """
        # CRITICAL: column_names  ,  sample_data   !
        #     -   !
        data_without_headers = sample_data if sample_data else []

        #  AI    (   )
        intent_analysis = await self._analyze_intent(query, column_names, data_without_headers, history)

        intent = intent_analysis.get("intent", "ANALYZE_PROBLEM")

        #    
        if intent in ["VISUALIZE_DATA", "FORMAT_PRESENTATION", "CREATE_STRUCTURE", "COMPARE_DATA", "FIND_INSIGHTS"]:
            #     (, , ) -   action plan
            return await self.generate_action_plan(query, column_names, data_without_headers, history, selected_range, active_cell)
        elif intent == "CALCULATE":
            #  
            return await self.generate_formula(query, column_names, data_without_headers, selected_range, active_cell)
        elif intent in ["QUESTION", "ANALYZE_PROBLEM", "QUERY_DATA"]:
            # ,        
            return await self.analyze_data(query, data_without_headers, column_names)
        else:
            #    
            return await self.analyze_data(query, data_without_headers, column_names)


    async def generate_formula(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None,
        selected_range: str = None, active_cell: str = None
    ) -> dict:
        """ Google Sheets """
        start_time = time.time()

        #  1:    template (  )
        from app.services.template_matcher import TemplateMatcher
        matcher = TemplateMatcher()
        template_result = matcher.find_template(query, column_names)

        if template_result:
            #   -  
            template, params = template_result

            try:
                #    
                formula = template.formula_pattern.format(**params)

                #    ( )
                formula, validation_issues = self._validate_and_fix_formula(formula, column_names, sample_data)

                #   (clean_formula  )
                formula = self._clean_formula(formula, column_names, sample_data)

                # PHASE 2.4: Calculate confidence for templates
                confidence = self._calculate_confidence("template", validation_issues)

                return {
                    "type": "formula",
                    "formula": formula,
                    "explanation": f"{template.description} (: {template.name})",
                    "target_cell": active_cell or "A1",
                    "confidence": confidence,
                    "processing_time": time.time() - start_time,
                    "source": "template",  #     
                    "validation_log": {
                        "issues_found": len(validation_issues),
                        "auto_fixed": True
                    } if validation_issues else None
                }
            except Exception as e:
                #     , fallback  AI
                print(f"Template application failed: {e}, falling back to AI")

        #  2: Fallback  AI reasoning (  )
        #     
        column_types = self._analyze_column_types(column_names, sample_data)

        #   
        prompt = self._build_formula_prompt(query, column_names, sample_data, column_types, selected_range, active_cell)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert Google Sheets formula generator.

CRITICAL RULES:
1. NEVER use spaces in formulas - formulas must be compact
2. Use ONLY valid Google Sheets syntax (not Excel!)
3. Column references must be exact: A, B, C or A2:A100
4. Always test logic before responding
5. Respond ONLY in valid JSON format

Example GOOD formula: =SORT(FILTER(A2:G;C2:C>500000);3;FALSE)
Example BAD formula: =SORT( FILTER( A2:G; C2:C > 500000 ); 3; FALSE )

NO SPACES IN FORMULAS!"""
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=600,
            )

            result = json.loads(response.choices[0].message.content)

            #    AI  ( )
            if "formula" in result:
                formula, validation_issues = self._validate_and_fix_formula(
                    result["formula"],
                    column_names,
                    sample_data
                )

                #    
                result["formula"] = self._clean_formula(formula, column_names, sample_data)

                # PHASE 2.4: Calculate confidence score
                confidence = self._calculate_confidence("gpt", validation_issues)
                result["confidence"] = confidence

                #       
                if validation_issues:
                    critical_issues = [i for i in validation_issues if i.severity == "critical"]
                    if critical_issues:
                        result["validation_log"] = {
                            "issues_found": len(validation_issues),
                            "critical_issues": len(critical_issues),
                            "auto_fixed": True,
                            "confidence_impact": f"-{100 - int(confidence * 100)}%"
                        }

            result["processing_time"] = time.time() - start_time
            result["type"] = "formula"
            result["source"] = "gpt"  # Mark as GPT-generated

            return result

        except Exception as e:
            return {
                "type": "error",
                "formula": "=ERROR()",
                "explanation": f"  : {str(e)}",
                "confidence": 0.0,
                "processing_time": time.time() - start_time
            }

    def _clean_formula(self, formula: str, column_names: List[str] = None, sample_data: List[List[Any]] = None) -> str:
        """    .

        : Google Sheets        ,
               (SUM, AVERAGE, VLOOKUP, IF, etc.)
        """
        #    
        formula = formula.replace(" >", ">").replace("> ", ">")
        formula = formula.replace(" <", "<").replace("< ", "<")
        formula = formula.replace(" =", "=").replace("= ", "=")
        formula = formula.replace(" ,", ",").replace(", ", ",")
        formula = formula.replace(" )", ")").replace("( ", "(")

        #   
        while "  " in formula:
            formula = formula.replace("  ", "")

        # NOTE:   -    
        # Google Sheets      
        import re

        #  QUERY : A/B/C  Col1/Col2/Col3
        # AI     QUERY,  
        if 'QUERY(' in formula.upper():
            import re
            #    SELECT   
            pattern = r'"(SELECT[^"]+)"'

            def fix_query_columns(match):
                sql = match.group(1)
                #     Col1, Col2, etc.
                #  regex  word boundaries     
                column_map = {
                    'A': 'Col1', 'B': 'Col2', 'C': 'Col3', 'D': 'Col4',
                    'E': 'Col5', 'F': 'Col6', 'G': 'Col7', 'H': 'Col8',
                    'I': 'Col9', 'J': 'Col10', 'K': 'Col11', 'L': 'Col12',
                    'M': 'Col13', 'N': 'Col14', 'O': 'Col15', 'P': 'Col16',
                }

                #    ,      
                # :   , ,   / 
                for letter, col in column_map.items():
                    # : (?<![A-Z])  "  ", (?![A-Z])  "  "
                    #       B   "BY"  "GROUP BY"
                    sql = re.sub(
                        rf'(?<![A-Za-z])({letter})(?![A-Za-z])',
                        col,
                        sql,
                        flags=re.IGNORECASE
                    )

                return f'"{sql}"'

            formula = re.sub(pattern, fix_query_columns, formula, flags=re.IGNORECASE)

        #  VLOOKUP  ARRAYFORMULA: VLOOKUP  INDEX/MATCH
        # VLOOKUP    ARRAYFORMULA,   INDEX/MATCH 
        if 'ARRAYFORMULA' in formula.upper() and 'VLOOKUP' in formula.upper():
            import re
            #    VLOOKUP(lookup_value; table_range; col_index; [FALSE])
            # \s*        
            vlookup_pattern = r'VLOOKUP\(([^;]+);\s*([^;]+);\s*(\d+);?\s*([^)]*)\)'

            def replace_vlookup_with_index_match(match):
                lookup_value = match.group(1).strip()
                table_range = match.group(2).strip()
                col_index = int(match.group(3).strip())

                #  table_range  
                # : H:I  $H:$I  H2:I100
                if ':' in table_range:
                    parts = table_range.split(':')
                    first_col = parts[0].strip()
                    last_col = parts[1].strip()

                    #  $   
                    has_dollar = '$' in first_col or '$' in last_col
                    dollar_prefix = '$' if has_dollar else ''

                    #    (   $)
                    first_col_letter = ''.join([c for c in first_col if c.isalpha()])
                    last_col_letter = ''.join([c for c in last_col if c.isalpha()])

                    #  result_col  col_index
                    # col_index=1   , col_index=2   
                    if col_index == 1:
                        result_col_letter = first_col_letter
                    elif col_index == 2:
                        result_col_letter = last_col_letter
                    else:
                        #  col_index > 2   
                        first_col_num = ord(first_col_letter.upper()) - ord('A')
                        result_col_num = first_col_num + col_index - 1
                        result_col_letter = chr(ord('A') + result_col_num)

                    #      
                    search_col = f"{dollar_prefix}{first_col_letter}:{dollar_prefix}{first_col_letter}"
                    result_col = f"{dollar_prefix}{result_col_letter}:{dollar_prefix}{result_col_letter}"

                    return f'INDEX({result_col}; MATCH({lookup_value}; {search_col}; 0))'
                else:
                    #  table_range   :,   
                    return match.group(0)

            formula = re.sub(vlookup_pattern, replace_vlookup_with_index_match, formula, flags=re.IGNORECASE)

        #  INDEX/MATCH:       
        # AI   INDEX/MATCH     
        #    (INDEX/MATCH),    (/)  
        has_index_match = ('INDEX' in formula.upper() and 'MATCH' in formula.upper()) or \
                          ('' in formula and '' in formula)

        if has_index_match and column_names and sample_data:
            import re

            #     
            column_types = self._analyze_column_types(column_names, sample_data)

            #   INDEX/MATCH (   )
            index_match_pattern_en = r'INDEX\(([^;]+);\s*MATCH\(([^;]+);\s*([^;]+);\s*0\)\)'
            index_match_pattern_ru = r'\(([^;(]+);\s*\(([^;]+);\s*([^;]+);\s*0\)\)'

            def fix_index_match_columns(match, is_russian=False):
                result_col = match.group(1).strip()
                lookup_value = match.group(2).strip()
                search_col = match.group(3).strip()

                #     lookup_value (, B2:B  B)
                lookup_col_letter = None
                lookup_match = re.search(r'\$?([A-Z]+)\d*:\$?[A-Z]+', lookup_value)
                if lookup_match:
                    lookup_col_letter = lookup_match.group(1)

                #     search_col (, $H:$H  H)
                search_col_letter = None
                search_match = re.search(r'\$?([A-Z]+):\$?\1', search_col)
                if search_match:
                    search_col_letter = search_match.group(1)

                #     result_col (, $I:$I  I)
                result_col_letter = None
                result_match = re.search(r'\$?([A-Z]+):\$?\1', result_col)
                if result_match:
                    result_col_letter = result_match.group(1)

                if not lookup_col_letter or not search_col_letter or not result_col_letter:
                    return match.group(0)  #   ,   

                #    (A=0, B=1, C=2, ...)
                lookup_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(lookup_col_letter))) - 1
                search_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(search_col_letter))) - 1
                result_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(result_col_letter))) - 1

                #    ( lookup  search )
                if lookup_col_idx >= len(column_names) or search_col_idx >= len(column_names):
                    return match.group(0)

                #   
                lookup_col_name = column_names[lookup_col_idx]
                search_col_name = column_names[search_col_idx]

                # result_col     -  , AI  
                result_col_name = column_names[result_col_idx] if result_col_idx < len(column_names) else None

                lookup_type = column_types.get(lookup_col_name, "unknown")
                search_type = column_types.get(search_col_name, "unknown")
                result_type = column_types.get(result_col_name, "unknown") if result_col_name else "unknown"

                #  :      
                if lookup_type == "text" and search_type in ["number", "number_formatted"]:
                    #       search_col
                    #     (, H   G )
                    correct_search_idx = None

                    #      search_col
                    if search_col_idx > 0:
                        neighbor_col_name = column_names[search_col_idx - 1]
                        neighbor_type = column_types.get(neighbor_col_name, "unknown")
                        if neighbor_type == "text" and neighbor_col_name:  #   
                            correct_search_idx = search_col_idx - 1

                    #    ,  
                    if correct_search_idx is None and search_col_idx + 1 < len(column_names):
                        neighbor_col_name = column_names[search_col_idx + 1]
                        neighbor_type = column_types.get(neighbor_col_name, "unknown")
                        if neighbor_type == "text" and neighbor_col_name:
                            correct_search_idx = search_col_idx + 1

                    #    ,  
                    if correct_search_idx is not None:
                        #     search_col
                        correct_search_letter = chr(ord('A') + correct_search_idx)

                        #     result_col (   )
                        #    search_col (  )
                        correct_result_letter = search_col_letter

                        #  $   
                        has_dollar = '$' in search_col
                        dollar_prefix = '$' if has_dollar else ''

                        #   
                        new_search_col = f"{dollar_prefix}{correct_search_letter}:{dollar_prefix}{correct_search_letter}"
                        new_result_col = f"{dollar_prefix}{correct_result_letter}:{dollar_prefix}{correct_result_letter}"

                        #     
                        if is_russian:
                            return f'({new_result_col}; ({lookup_value}; {new_search_col}; 0))'
                        else:
                            return f'INDEX({new_result_col}; MATCH({lookup_value}; {new_search_col}; 0))'

                #    ,   
                return match.group(0)

            #       
            is_russian = '' in formula and '' in formula

            if is_russian:
                #   
                formula = re.sub(index_match_pattern_ru, lambda m: fix_index_match_columns(m, is_russian=True), formula)
            else:
                #   
                formula = re.sub(index_match_pattern_en, lambda m: fix_index_match_columns(m, is_russian=False), formula, flags=re.IGNORECASE)

        #  INDEX/MATCH  VLOOKUP  ARRAYFORMULA
        # INDEX/MATCH      ARRAYFORMULA,   VLOOKUP
        is_in_arrayformula = 'ARRAYFORMULA' in formula.upper() or '' in formula
        has_index_match_after = ('INDEX' in formula.upper() and 'MATCH' in formula.upper()) or \
                                ('' in formula and '' in formula)

        if is_in_arrayformula and has_index_match_after and column_names:
            #    INDEX/MATCH  
            #  : INDEX($H:$H; MATCH(B2:B; $G:$G; 0))  INDEX($H$2:$H; MATCH(B2:B; $G$2:$G; 0))
            #  : $H:$H, $H$2:$H, $H$2:$H$999
            index_match_array_pattern_en = r'INDEX\((\$?[A-Z]+(?:\$\d+)?:\$?[A-Z]+(?:\$\d+)?);\s*MATCH\(([A-Z]+\d+:[A-Z]+);\s*(\$?[A-Z]+(?:\$\d+)?:\$?[A-Z]+(?:\$\d+)?);\s*0\)\)'
            index_match_array_pattern_ru = r'\((\$?[A-Z]+(?:\$\d+)?:\$?[A-Z]+(?:\$\d+)?);\s*\(([A-Z]+\d+:[A-Z]+);\s*(\$?[A-Z]+(?:\$\d+)?:\$?[A-Z]+(?:\$\d+)?);\s*0\)\)'

            def replace_with_vlookup(match, is_russian=False):
                result_col_ref = match.group(1).strip()  # $H:$H
                lookup_array = match.group(2).strip()     # B2:B
                search_col_ref = match.group(3).strip()   # $G:$G

                #   
                result_col_letter = re.search(r'([A-Z]+)', result_col_ref).group(1)
                search_col_letter = re.search(r'([A-Z]+)', search_col_ref).group(1)

                #   
                result_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(result_col_letter))) - 1
                search_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(search_col_letter))) - 1

                #    VLOOKUP (  )
                vlookup_col_index = result_col_idx - search_col_idx + 1

                #    VLOOKUP: $G$2:$H
                has_dollar = '$' in search_col_ref
                dollar_prefix = '$' if has_dollar else ''
                table_range = f"{dollar_prefix}{search_col_letter}{dollar_prefix}2:{dollar_prefix}{result_col_letter}"

                #  VLOOKUP   
                if is_russian:
                    return f'({lookup_array}; {table_range}; {vlookup_col_index}; )'
                else:
                    return f'VLOOKUP({lookup_array}; {table_range}; {vlookup_col_index}; FALSE)'

            #  
            is_russian_after = '' in formula and '' in formula

            if is_russian_after:
                formula = re.sub(index_match_array_pattern_ru, lambda m: replace_with_vlookup(m, is_russian=True), formula)
            else:
                formula = re.sub(index_match_array_pattern_en, lambda m: replace_with_vlookup(m, is_russian=False), formula, flags=re.IGNORECASE)

        return formula

    def _validate_and_fix_formula(
        self,
        formula: str,
        column_names: List[str] = None,
        sample_data: List[List[Any]] = None
    ) -> tuple[str, list]:
        """
              

        Returns:
            (fixed_formula, issues) -      
        """
        # PHASE 2.2:  column_count  context  column reference validation
        context = {
            "row_count": len(sample_data) if sample_data else 100,
            "column_names": column_names or [],
            "column_count": len(column_names) if column_names else 0
        }

        #  1: 
        issues = self.validator.validate(formula, context)

        if not issues:
            return formula, []

        #  2:  
        fixable_issues = [i for i in issues if i.auto_fixable]

        if fixable_issues:
            fixed_formula = self.fixer.fix(formula, fixable_issues, context)
            return fixed_formula, issues

        #   auto-fixable ,  
        return formula, issues

    def _calculate_confidence(
        self,
        source: str,
        validation_issues: list
    ) -> float:
        """
        PHASE 2.4:  confidence score (0.0 - 1.0)

        Args:
            source: "template"  "gpt"
            validation_issues:  ValidationIssue

        Returns:
            Confidence score  0.0  1.0

        :
        - Template baseline: 0.95
        - GPT baseline: 0.70
        -  issue  score:
          - critical ( -): -0.20
          - critical (-): -0.10
          - high: -0.08
          - medium: -0.05
          - low: -0.02
        """
        #  score   
        if source == "template":
            base_score = 0.95
        elif source == "gpt":
            base_score = 0.70
        else:
            base_score = 0.50

        if not validation_issues:
            return base_score

        #     issue
        penalty = 0.0

        severity_penalties = {
            "critical": 0.20,  #  
            "high": 0.08,       #  
            "medium": 0.05,     #  
            "low": 0.02         #  
        }

        for issue in validation_issues:
            severity_penalty = severity_penalties.get(issue.severity, 0.05)

            #  issue -,  
            if issue.auto_fixable:
                severity_penalty *= 0.5

            penalty += severity_penalty

        #  score (  0.1)
        final_score = max(0.1, base_score - penalty)

        return round(final_score, 2)

    def _analyze_column_types(self, column_names: List[str], sample_data: List[List[Any]]) -> Dict[str, str]:
        """    """
        column_types = {}

        if not sample_data or len(sample_data) == 0:
            return column_types

        for i, col_name in enumerate(column_names):
            #     
            values = [row[i] if i < len(row) else None for row in sample_data[:5]]
            values = [v for v in values if v is not None]

            if not values:
                column_types[col_name] = "unknown"
                continue

            #  
            if all(isinstance(v, (int, float)) for v in values):
                column_types[col_name] = "number"
            elif all(str(v).replace('.', '').replace(',', '').replace('%', '').replace('', '').replace('p', '').strip().replace('-', '').isdigit() for v in values):
                column_types[col_name] = "number_formatted"
            else:
                column_types[col_name] = "text"

        return column_types

    def _build_formula_prompt(
        self, query: str, column_names: List[str], sample_data: List[List[Any]], column_types: Dict,
        selected_range: str = None, active_cell: str = None
    ) -> str:
        """    """

        #  sample data 
        sample_rows = []
        if sample_data:
            for row in sample_data[:3]:
                sample_rows.append(" | ".join([str(v) for v in row]))

        columns_info = []
        for i, col in enumerate(column_names):
            col_letter = chr(65 + i)  # A, B, C...
            col_type = column_types.get(col, "unknown")
            columns_info.append(f"{col_letter}: {col} ({col_type})")

        #     
        selection_info = ""
        if selected_range:
            selection_info = f"\n :    {selected_range}.      {selected_range.split(':')[0]}!"
        elif active_cell:
            selection_info = f"\n : {active_cell}"

        prompt = f"""Generate a Google Sheets formula for this request.

TABLE STRUCTURE:
Columns: {len(column_names)}
{chr(10).join(columns_info)}

SAMPLE DATA (without headers):
{chr(10).join(sample_rows) if sample_rows else "No data"}{selection_info}

USER REQUEST (Russian): {query}

# GOOGLE SHEETS QUICK REFERENCE

## Aggregation ():
- SUM(A2:A) - 
- AVERAGE(A2:A) - 
- COUNT(A2:A) -  
- MAX(A2:A), MIN(A2:A) - /

## Conditional ():
- SUMIF($A$2:$A,"",$B$2:$B) -    ( $  !)
- SUMIFS($C$2:$C,$A$2:$A,"",$B$2:$B,">100") -    
- COUNTIF($A$2:$A,"") -   
- AVERAGEIF($A$2:$A,"",$B$2:$B) -   
- IF(A2>100,"","") - 
  ARRAYFORMULA  SUMIF/COUNTIF:   $   /!

## Arrays ( - MODERN!):
- UNIQUE(A2:A) -  
- FILTER(A2:B,B2:B>1000) - 
- SORT(A2:B,2,FALSE) -  ( 2,  )
- QUERY(A2:C,"SELECT Col1, SUM(Col2) GROUP BY Col1",0) - SQL-
      QUERY:  Col1, Col2, Col3 ( A, B, C!)
       !

## Lookup () -  !:
  ARRAYFORMULA   INDEX/MATCH,  VLOOKUP!

   LOOKUP :
   "  ", " ", "  /" -
  LOOKUP  (    ,   ).

  LOOKUP :
Lookup       (   ):
1. Search column () -      
2. Result column () -      

 :
:
- Lookup table G:H  search in G, return from H
  =INDEX($H:$H,MATCH(B2,$G:$G,0))

- Lookup table D:E  search in D, return from E
  =INDEX($E:$E,MATCH(A2,$D:$D,0))

-  ARRAYFORMULA  :
  =ARRAYFORMULA(IF(B2:B="","",IF(C2:C<5,INDEX($H:$H,MATCH(B2:B,$G:$G,0)),INDEX($H:$H,MATCH(B2:B,$G:$G,0))*1.05)))

:
 =INDEX($H:$H,MATCH(B2:B,$H:$H,0)) -       (H)!
 VLOOKUP  ARRAYFORMULA -  !

  INDEX/MATCH:
INDEX(result_column, MATCH(lookup_value, search_column, 0))
                            

search_column =   / ()
result_column =      (/)

    :
1.   lookup_value ( ) -       
2.           (text  text)
3.   = search_column ( )
4.    = result_column ( )

 :
: column_names = ["" (text), "" (number), "" (empty), ..., " ()" (text), " " (number)]
                        A                B               C                      G                           H

: "   "
1. lookup_value = B2:B () -  
2.  : G:H
3. G = " ()" (text) -   lookup_value  !  search_column = $G:$G
4. H = " " (number) -    result_column = $H:$H
5. : INDEX($H:$H, MATCH(B2:B, $G:$G, 0))

 : INDEX($H:$H, MATCH(B2:B, $H:$H, 0)) -   ""  !
 : INDEX($H:$H, MATCH(B2:B, $G:$G, 0)) -   ""  !

   -    !!!

 #1:      
 : INDEX(I:I; MATCH(B2:B; H:H; 0))
    B2:B  "" (),  H:H  55000 ()
   : #ERROR!   MATCH  ""  !

 : INDEX(H:H; MATCH(B2:B; G:G; 0))
    B2:B  "" (), G:G  "" (), H:H  55000 ()
   : 55000 (!)

 #2:   search_column  result_column
 INDEX/MATCH  :
INDEX(__; MATCH(_; _; 0))

 : INDEX(G:G; MATCH(B2:B; H:H; 0)) -    !
 : INDEX(H:H; MATCH(B2:B; G:G; 0)) -    H,   G

 #3:   lookup 
  column_names = ["", "", "", "", "", "", " "]
                              A       B      C     D  E   G          H
  D,E     !
 = G:H (G= "", H= " ")

 :   H:H (),   I:I
 :   G:G (),   H:H ()

    :
1. lookup_value ( ) = B2:B    sample_data    ("", "HR")
2.   column_names   (   "")
3.      = search_column  MATCH
4.   = result_column  INDEX
5. : lookup_value ()      ,   !

## Text ():
- A2&" "&B2 - 
- LEFT(A2,5), RIGHT(A2,5) - / 
- UPPER(A2), LOWER(A2) - 

## Dates ():
- TODAY() - 
- YEAR(A2), MONTH(A2), DAY(A2) -  

## Common Patterns ( ):
" "  UNIQUE(A2:A) + SUMIF($A$2:$A,E2,$B$2:$B)
" 10"  SORT(A2:B,2,FALSE)
" "  AVERAGE(B2:B)  SUM()/COUNT()
""     =(B3-B2)/B2*100
"  "  B2/SUM($B$2:$B)*100

   -  :
 SUMIF    !

 :
=SUMIF($B$2:$B,"",$C$2:$C*$D$2:$D)  // ! SUMIF   

  -  SUMPRODUCT:
=SUMPRODUCT(($B$2:$B="")*($C$2:$C*$D$2:$D))

  SUMPRODUCT:
- "   " (  )  =SUMPRODUCT(($B$2:$B="1")*($C$2:$C*$D$2:$D))
- "   ="  =SUMPRODUCT(($A$2:$A="")*($B$2:$B*$C$2:$C))
- "     X"  =SUMPRODUCT(($B$2:$B=" X")*($C$2:$C*1.2))

:         SUMPRODUCT,  SUMIF!

     ( SUMPRODUCT   ):
     ( ""  " "):
  ( ): =SUMPRODUCT(($B$2:$B="")*($C$2:$C*$D$2:$D))
  ( ): =SUMPRODUCT(ISNUMBER(SEARCH("";$B$2:$B))*($C$2:$C*$D$2:$D))

SEARCH     (  ).
    :
- "  "  =SUMPRODUCT(ISNUMBER(SEARCH("";$B$2:$B))*($C$2:$C*$D$2:$D))
- "  "  =SUMPRODUCT(ISNUMBER(SEARCH("";$A$2:$A))*($B$2:$B*$C$2:$C))

IMPORTANT REQUIREMENTS:
1.   :     (;)     !
    : =SUMPRODUCT(A2:A,B2:B)  =IFERROR(A2,"")
    : =SUMPRODUCT(A2:A;B2:B)  =IFERROR(A2;"")
2. NO SPACES in formula - must be compact like =SORT(FILTER(A2:G;C2:C>500000);3;FALSE)
3. Use correct column letters (A, B, C, etc.)
4. Data starts from row 2 (row 1 is headers)
5. Use open ranges (A2:A, not A2:A100) when referencing entire column
6. Use $ for absolute references when needed ($A$2:$A)
7. Respond in Russian but formula in English

Response format (JSON):
{{
  "formula": "=SORT(FILTER(A2:G;C2:C>500000);3;FALSE)",
  "explanation": "      ",
  "target_cell": "I2",
  "confidence": 0.95
}}

If request is unclear, set confidence < 0.6 and explain what's missing."""

        return prompt

    def _detect_aggregation_need(self, query: str) -> Optional[Dict[str, str]]:
        """
           Python-     

        Returns:
            Dict     ,  None    
        """
        query_lower = query.lower()

        #    
        aggregation_patterns = [
            # " // [X]   [Y]"
            (r'\s+(||)\s+\S+\s+.*( | ||)', 'group_sum'),
            # "/ [X] /  "
            (r'(|||)\s+\S+\s+(||||).*( | ||)', 'group_sum'),
            # " /  "
            (r'(\s+|)\s+( | ||)', 'group_sum'),
            # " 3 [X]  "
            (r'\s+\d+\s+\S+\s+\s+(|||)', 'group_sum_top'),
            # "   "
            (r'(|)\s+\S+\s+(||)\s+\S+', 'group_count'),
            # "   "
            (r'.+\s+(||)\s+(||)\s+\S+', 'group_avg'),
        ]

        for pattern, agg_type in aggregation_patterns:
            if re.search(pattern, query_lower):
                return {'type': agg_type, 'query': query}

        return None

    def _perform_python_aggregation(
        self,
        query: str,
        sample_data: List[List[Any]],
        column_names: List[str],
        agg_config: Dict[str, str]
    ) -> Optional[Dict]:
        """
          Python-   pandas

        Args:
            query:  
            sample_data:  
            column_names:  
            agg_config:    _detect_aggregation_need

        Returns:
            Dict     None   
        """
        try:
            #  DataFrame
            df = pd.DataFrame(sample_data, columns=column_names)

            print(f"\n Python aggregation started:")
            print(f"Query: {query}")
            print(f"Agg type: {agg_config['type']}")
            print(f"DataFrame shape: {df.shape}")
            print(f"Columns: {column_names}")

            #       
            #  :  ,      !
            group_column = None
            value_column = None
            query_lower = query.lower()

            print(f"\n COLUMN DETECTION DEBUG:")
            print(f" Query (lowercase): '{query_lower}'")
            print(f" Available columns: {column_names}")

            #  :    ( A, B, C...)
            has_auto_headers = all(col.startswith(' ') for col in column_names[:5] if col)

            if has_auto_headers:
                print(f" DETECTED AUTOMATIC HEADERS! Using position-based detection")

                #      
                if '' in query_lower or '' in query_lower or '' in query_lower:
                    #  :      
                    for i, col in enumerate(column_names):
                        if i > 0 and i < len(sample_data[0]):  #   
                            #     
                            first_val = sample_data[0][i] if sample_data else None
                            if first_val and isinstance(first_val, str) and '' in str(first_val):
                                group_column = col
                                print(f" SELECTED group column by position {i}: '{col}' (found company names)")
                                break
                    #    ,    ( )
                    if not group_column and len(column_names) > 1:
                        group_column = column_names[1]
                        print(f" SELECTED group column by default position 1: '{group_column}'")

                elif '' in query_lower or '' in query_lower:
                    #  :  
                    group_column = column_names[0] if column_names else None
                    print(f" SELECTED group column for products: '{group_column}'")

            else:
                #     
                #     -    
                group_keywords = {
                    '': [''],
                    '': ['', ''],
                    '': ['', ''],
                    '': ['', '', ''],
                    '': [''],
                    '': ['', '']
                }

                #       
                for keyword_group, synonyms in group_keywords.items():
                    query_has_keyword = any(syn in query_lower for syn in synonyms)
                    if query_has_keyword:
                        print(f" Found keyword '{keyword_group}' in query (synonyms: {synonyms})")
                        #      
                        for col in column_names:
                            col_lower = col.lower()
                            col_has_keyword = any(syn in col_lower for syn in synonyms)
                            print(f"  Checking column '{col}': keyword match = {col_has_keyword}, has '' = {'' in col_lower}")
                            if col_has_keyword and '' not in col_lower:
                                group_column = col
                                print(f" SELECTED group column: '{col}' (matched keyword '{keyword_group}')")
                                break
                        if group_column:
                            break

            #      -   
            if not group_column:
                all_group_keywords = ['', '', '', '', '', '', '']
                for col in column_names:
                    col_lower = col.lower()
                    if any(keyword in col_lower for keyword in all_group_keywords):
                        if '' not in col_lower:
                            group_column = col
                            print(f"  Group column by fallback: '{col}'")
                            break

            #     -  ""  
            print(f"\n VALUE COLUMN DETECTION:")

            if has_auto_headers:
                #    -   
                print(f" Using position-based value column detection")

                if '' in query_lower or '' in query_lower or ' ' in query_lower:
                    #     (   )
                    for i in range(len(column_names) - 1, -1, -1):
                        col = column_names[i]
                        try:
                            #    
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            if df[col].notna().sum() > len(df) * 0.5:  #   50%  
                                value_column = col
                                print(f" SELECTED value column by position {i}: '{col}' (last numeric column)")
                                break
                        except:
                            continue

                elif '' in query_lower or '' in query_lower:
                    #   -   
                    numeric_cols = []
                    for i, col in enumerate(column_names):
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            if df[col].notna().sum() > len(df) * 0.5:
                                numeric_cols.append((i, col))
                        except:
                            continue
                    if len(numeric_cols) >= 2:
                        value_column = numeric_cols[-2][1]  #  
                        print(f" SELECTED value column for volume: '{value_column}'")

            else:
                #     
                value_priority_keywords = [
                    (['', ''], ['']),
                    (['', ''], ['', '']),
                    (['', ''], ['', '']),
                ]

                #   
                for query_keywords, column_keywords in value_priority_keywords:
                    query_has_value_keyword = any(kw in query_lower for kw in query_keywords)
                    if query_has_value_keyword:
                        print(f" Found value keyword in query: {[kw for kw in query_keywords if kw in query_lower]}")
                        for col in column_names:
                            col_lower = col.lower()
                            col_has_keyword = any(kw in col_lower for kw in column_keywords)
                            print(f"  Checking column '{col}': keyword match = {col_has_keyword}")
                            if col_has_keyword:
                                try:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                                    has_values = df[col].notna().any()
                                    print(f"  '{col}' is numeric: {has_values}")
                                    if has_values:
                                        value_column = col
                                        print(f" SELECTED value column: '{col}' (matched keywords {column_keywords})")
                                        break
                                except Exception as e:
                                    print(f"  '{col}' conversion error: {e}")
                                    continue
                        if value_column:
                            break

            #      -    
            if not value_column:
                for col in column_names:
                    col_lower = col.lower()
                    if any(kw in col_lower for kw in ['', '', '', '', '']):
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            if df[col].notna().any():
                                value_column = col
                                print(f"  Value column by fallback: '{col}'")
                                break
                        except:
                            continue

            if not group_column or not value_column:
                print(f"  Could not detect columns: group={group_column}, value={value_column}")
                return None

            print(f" Detected: group_by='{group_column}', aggregate='{value_column}'")
            print(f"\n DataFrame before aggregation (first 5 rows):")
            print(df[[group_column, value_column]].head())

            #  
            if agg_config['type'] in ['group_sum', 'group_sum_top']:
                # GROUP BY + SUM
                print(f"\n Executing: df.groupby('{group_column}')['{value_column}'].sum()")
                result_df = df.groupby(group_column, as_index=False)[value_column].sum()
                result_df = result_df.sort_values(value_column, ascending=False)
                print(f" Aggregation complete. Top result: {result_df.iloc[0][group_column]} = {result_df.iloc[0][value_column]}")

                #  -N    
                if agg_config['type'] == 'group_sum_top':
                    top_match = re.search(r'\s+(\d+)', query.lower())
                    if top_match:
                        top_n = int(top_match.group(1))
                        result_df = result_df.head(top_n)

                print(f" Aggregation result:\n{result_df}")

                #  
                top_entity = result_df.iloc[0]
                summary = f"{top_entity[group_column]}   : {top_entity[value_column]:,.2f}"

                key_findings = []
                for idx, row in result_df.head(5).iterrows():
                    key_findings.append(
                        f"{idx+1} {row[group_column]}: {row[value_column]:,.2f}"
                    )

                return {
                    'summary': summary,
                    'methodology': f"  :     '{group_column}',      '{value_column}'   ,   ",
                    'key_findings': key_findings,
                    'explanation': f" {len(df)}  .     '{group_column}'   .",
                    'confidence': 0.98,
                    'source': 'python_aggregation'
                }

            elif agg_config['type'] == 'group_count':
                # GROUP BY + COUNT
                result_df = df.groupby(group_column, as_index=False)[value_column].count()
                result_df = result_df.sort_values(value_column, ascending=False)

                top_entity = result_df.iloc[0]
                summary = f"{top_entity[group_column]}: {top_entity[value_column]} "

                return {
                    'summary': summary,
                    'methodology': f"  :      '{group_column}'",
                    'key_findings': [f"{row[group_column]}: {row[value_column]} " for _, row in result_df.head(5).iterrows()],
                    'explanation': f"      '{group_column}'",
                    'confidence': 0.98,
                    'source': 'python_aggregation'
                }

            elif agg_config['type'] == 'group_avg':
                # GROUP BY + AVG
                result_df = df.groupby(group_column, as_index=False)[value_column].mean()
                result_df = result_df.sort_values(value_column, ascending=False)

                top_entity = result_df.iloc[0]
                summary = f"{top_entity[group_column]}:  {top_entity[value_column]:,.2f}"

                return {
                    'summary': summary,
                    'methodology': f"  :    '{value_column}'   '{group_column}'",
                    'key_findings': [f"{row[group_column]}: {row[value_column]:,.2f} ()" for _, row in result_df.head(5).iterrows()],
                    'explanation': f"     '{group_column}'",
                    'confidence': 0.98,
                    'source': 'python_aggregation'
                }

            return None

        except Exception as e:
            print(f" Python aggregation error: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def analyze_data(
        self, query: str, sample_data: List[List[Any]], column_names: List[str]
    ) -> dict:
        """
             
        """
        start_time = time.time()

        #    
        sample_rows = []
        if sample_data:
            for row in sample_data[:10]:  #     
                sample_rows.append(row)

        # DEBUG: Log input data
        print(f"\n DEBUG analyze_data:")
        print(f"Query: {query}")
        print(f"Columns: {column_names}")
        print(f"Sample data (first 5): {sample_rows[:5]}")

        # CRITICAL: Check if Python aggregation is needed
        agg_config = self._detect_aggregation_need(query)
        if agg_config and sample_data:
            print(f" Python aggregation detected: {agg_config['type']}")
            python_result = self._perform_python_aggregation(query, sample_data, column_names, agg_config)
            if python_result:
                print(f" Python aggregation successful!")
                python_result["processing_time"] = time.time() - start_time
                python_result["type"] = "analysis"
                return python_result
            else:
                print(f"  Python aggregation failed, falling back to GPT")

        prompt = f"""Analyze this Google Sheets data.

 TABLE:
Columns: {', '.join(column_names)}

Data (first 10 rows):
{json.dumps(sample_rows, ensure_ascii=False)}

 USER QUESTION: {query}

 CRITICAL: You MUST return ALL fields below. NO optional fields!

 REQUIRED JSON FORMAT:
{{
  "summary": "   1  (50-80 )",
  "methodology": "  : [       - ///]",
  "key_findings": [
    " 1  ",
    " 2  "
  ],
  "explanation": "  ",
  "confidence": 0.9
}}

 METHODOLOGY EXAMPLES:
- "  :   '' (B)  ,  -3"
- "  :     '' (C),   '' (A) = ''"
- "  :      '' (D) = ''"

 METHODOLOGY RULES:
1.    "  :"
2.       ( !)
3.  : ////
4. : 80-120 

RULES:
1. summary -    (1-2 ,  100 )
2. methodology -     :   ,   ,    (100-150 )
   -    "    :"
   -    
   -    (, , ,   ..)
3. key_findings -     (3-5   50-80 )
4. insights -      (2-4   50-80 )
5. suggested_actions -      (2-3   50-80 )

DETERMINISTIC SORTING (CRITICAL FOR " N" QUERIES):
- ALWAYS sort by value DESCENDING (highest first)
- If values are equal, sort alphabetically by name ASCENDING (A to Z)
- NEVER randomize or vary results between calls
- Example: For " 3   " with sales [800, 800, 600]:
  * If " A" and " B" both have 800 sales  sort alphabetically: " A" comes first
  * Result MUST be consistent: [ A (800),  B (800),  C (600)]

EXAMPLES:

Good summary: "   40%  .    Q4."
Bad summary: "    ,       ..."

Good methodology: "    :   '',     ,     Q1  Q4"
Bad methodology: "     "

Good key_finding: "-:   150  90 (-40%)"
Bad key_finding: "        ..."

Good insight: "       "
Bad insight: "       ..."

Good action: "       Q4"
Bad action: "     ..."

 CRITICAL: AGGREGATION AND GROUPING 

When query asks " [ENTITY] [ / ] [METRIC]":
- ENTITY = category to group by (, , , , etc.)
- METRIC = value to aggregate (, , , etc.)

YOU MUST:
1. **GROUP BY** ENTITY column
2. **SUM/COUNT/AVG** METRIC column for each group
3. **FIND** which ENTITY has max/min total

 WRONG APPROACH (just sorting):
Query: "    ?"
Wrong: Sort '' column  find max value  return supplier from that ONE row
Problem: Ignores that supplier may have MULTIPLE sales!

 CORRECT APPROACH (group + aggregate):
Query: "    ?"
Step 1: GROUP BY '' column
Step 2: SUM '' for each supplier (sum ALL rows for each supplier!)
Step 3: Find supplier with maximum total
Example:
-  "": row 4 (44297.96) + row 7 (145550.44) + row 16 (88595.92) = 278444.32
-  "": row 10 (378191.85) = 378191.85
Result:  "" has maximum total

Methodology: "  :     '',      ,  "

 AGGREGATION KEYWORDS:
- "/ [X]  / "  GROUP BY X, SUM metric
- " /  "  GROUP BY, SUM/COUNT
- " 3 [X]  [metric]"  GROUP BY X, SUM metric, sort, take top 3

CRITICAL FOR METHODOLOGY:
- If query asks " 3 "  explain: which column was used for products, which for sorting, how top 3 was selected
- If query asks "     "  explain: which column for suppliers, which for products, how count was calculated
- If query asks "   "  provide DETAILED explanation of previous calculation

 EXAMPLE FOR " 3   ":
Input:
Columns: , , 
Data: [[" A", 800, 50], [" B", 800, 45], [" C", 600, 30], [" D", 400, 20]]

CORRECT RESPONSE:
{{
  "summary": "  A   B  800  ",
  "methodology": "  :   ''  ,    -  ,  -3",
  "key_findings": [
    "1  A: 800  (-1)",
    "2  B: 800  (-2)",
    "3  C: 600  (-3)"
  ],
  "explanation": " A   B      (800),     C  600 .",
  "confidence": 0.95
}}

Be CONCISE, SPECIFIC, SCANNABLE!"""

        # Retry logic for rate limiting
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a data analyst who creates STRUCTURED, SCANNABLE reports.

CRITICAL:
- NO walls of text - users won't read them
- Each point must be SHORT (50-80 chars max)
- Use CONCRETE numbers, not vague descriptions
- Be SPECIFIC and ACTIONABLE
- All text in Russian with emojis for visual structure
- DETERMINISTIC: Always sort data the same way (descending by value, then alphabetically by name)
- CONSISTENCY: Same query MUST return same results every time"""
                        },
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=1000,
            )

                result = json.loads(response.choices[0].message.content)

                # DEBUG: Log GPT response
                print(f" GPT-4o response keys: {list(result.keys())}")
                print(f" Has methodology: {('methodology' in result)}")
                if 'methodology' in result:
                    print(f" methodology value: {result['methodology']}")

                result["processing_time"] = time.time() - start_time
                result["type"] = "analysis"

                # CRITICAL FIX: If GPT-4o didn't return methodology, generate default one
                if not result.get("methodology"):
                    print("  GPT didn't return methodology, generating fallback...")
                    column_list = ", ".join([f"'{col}'" for col in column_names[:5]])  # First 5 columns
                    if len(column_names) > 5:
                        column_list += f"   {len(column_names) - 5}"
                    result["methodology"] = f"  :     (: {column_list})"
                    print(f" Fallback methodology: {result['methodology']}")

                print(f" Final result keys before return: {list(result.keys())}")
                return result

            except RateLimitError as e:
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                    print(f"  Rate limit hit (attempt {attempt + 1}/{MAX_RETRIES}). Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f" Rate limit exceeded after {MAX_RETRIES} attempts")
                    return {
                        "type": "error",
                        "answer": "    AI. ,  1    .",
                        "insights": [],
                        "suggested_actions": [" 60    "],
                        "confidence": 0.0,
                        "processing_time": time.time() - start_time
                    }
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  Error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
                    delay = INITIAL_RETRY_DELAY * (attempt + 1)
                    await asyncio.sleep(delay)
                    continue
                else:
                    return {
                        "type": "error",
                        "answer": f" : {str(e)}",
                        "insights": [],
                        "suggested_actions": [],
                        "confidence": 0.0,
                        "processing_time": time.time() - start_time
                    }

    async def answer_question(
        self, query: str, sample_data: List[List[Any]], column_names: List[str]
    ) -> dict:
        """    """
        #       analyze_data
        return await self.analyze_data(query, sample_data, column_names)

    async def _analyze_intent(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None, history: List[dict] = None
    ) -> dict:
        """
        Step 1:       

        Args:
            query:  
            column_names:  
            sample_data:  
            history:   
        """
        row_count = len(sample_data) if sample_data else 0

        #    
        history_text = ""
        if history and len(history) > 0:
            history_text = "\n\n# PREVIOUS ACTIONS (CONTEXT)\n"
            for i, item in enumerate(history[-3:]):  #  3 
                #    item
                if not isinstance(item, dict):
                    continue

                history_text += f"\n{i+1}. User: \"{item.get('query', '')}\"\n"
                if 'actions' in item:
                    actions = item['actions']
                    #   actions  
                    if not isinstance(actions, list):
                        continue

                    history_text += f"   Actions performed: {len(actions)} actions\n"
                    for action in actions:
                        #   action  
                        if not isinstance(action, dict):
                            continue
                        history_text += f"   - {action.get('type')}: {action.get('config', {})}\n"

        prompt = f"""Analyze user's intent and determine what they REALLY want.

USER REQUEST: "{query}"

DATA AVAILABLE:
- Columns: {', '.join(column_names)}
- {row_count} rows of data{history_text}

# INTENT CATEGORIES (PRIORITY ORDER - CHECK FROM TOP!)

1. QUESTION - User asks HOW/WHY/WHAT and wants text explanation (NOT actions!)
   CRITICAL Keywords: " ", " ", " ", "  ", "  ", "", " "
   Examples: "   ?", "    ?", "    ?"
    PRIORITY: If query has " / / "  ALWAYS use QUESTION!

2. QUERY_DATA - User wants TEXT LIST of items (top, best, worst) WITHOUT chart
   CRITICAL Rule: Has "//// / " BUT NO "////"
   Examples:
   - " 3   "  QUERY_DATA (text list!)
   - "     "  QUERY_DATA (text answer!)
   - " "  QUERY_DATA (text list!)
   - " "  QUERY_DATA (text list!)
    CRITICAL: "//" WITHOUT visualization keywords  QUERY_DATA!

3. VISUALIZE_DATA - User EXPLICITLY asks for chart/graph/visualization
   CRITICAL Keywords: "", "", "  ", "", " ", " "
   Examples:
   - "   3"  VISUALIZE_DATA (has ""!)
   - "  "  VISUALIZE_DATA (has ""!)
   - " 3  "  VISUALIZE_DATA (has ""!)
    ONLY if query explicitly mentions chart/graph!

4. ANALYZE_PROBLEM - User wants detailed data analysis with text insights
   Keywords: "", "", "", " "

5. FIND_INSIGHTS - User wants to discover patterns/trends with actions
   Keywords: "", "", "", "", ""

6. COMPARE_DATA - User wants to compare values
   Keywords: "", "vs", ""

7. FORMAT_PRESENTATION - User wants to make data look good
   Keywords: "", "", "", ""

8. CREATE_STRUCTURE - User wants to create data structure (pivot, summary table, etc)
   Keywords: "", "", "", "pivot", "", ""

9. CALCULATE - User wants computed value
   Keywords: "", "", "", ""

# CRITICAL DECISION ALGORITHM (CHECK IN ORDER!):

STEP 1: Check for QUESTION keywords first
- Has " / / // "?  QUESTION

STEP 2: Check for visualization keywords
- Has "//  //"?  VISUALIZE_DATA

STEP 3: Check for data query keywords WITHOUT visualization
- Has "//// / " AND NO visualization keywords?  QUERY_DATA

STEP 4: Other intents...

# OUTPUT FORMAT (valid JSON):
{{
  "intent": "QUERY_DATA",
  "depth": 1,
  "must_include": [],
  "context": "User wants text list of top items"
}}

# CRITICAL TEST CASES - MUST PASS ALL:

 " 3   "  {{"intent": "QUERY_DATA", "depth": 1}} (text list, NO visualization!)
 "     "  {{"intent": "QUERY_DATA", "depth": 1}} (text answer!)
 "   ?"  {{"intent": "QUESTION", "depth": 1}} (explanation!)
 "    ?"  {{"intent": "QUESTION", "depth": 1}} (explanation!)
 " "  {{"intent": "QUERY_DATA", "depth": 1}} (text list!)
 "   3"  {{"intent": "VISUALIZE_DATA", "depth": 1}} (has ""!)
 " 3  "  {{"intent": "VISUALIZE_DATA", "depth": 1}} (has ""!)
 "  "  {{"intent": "VISUALIZE_DATA", "depth": 1}} (has ""!)

# CONTEXT-AWARE MODIFICATIONS
If history exists AND user modifies previous action:
- Previous: create_chart, User: "  "  {{"intent": "VISUALIZE_DATA"}}
- Previous: create_chart, User: "  "  {{"intent": "VISUALIZE_DATA"}}

Return ONLY valid JSON. No explanations."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an intent analyzer. Output valid JSON only, no explanations."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=200,
            )

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            # Fallback:   intent   
            query_lower = query.lower()

            # Priority 1: Questions
            if any(kw in query_lower for kw in [" ", " ", " ", " ", " ", ""]):
                return {"intent": "QUESTION", "depth": 1, "must_include": [], "context": "Question fallback"}

            # Priority 2: Query data (top/best/worst WITHOUT visualization)
            has_query_keywords = any(kw in query_lower for kw in [" ", "", "", "", " ", " "])
            has_viz_keywords = any(kw in query_lower for kw in ["", "", "", "", " "])

            if has_query_keywords and not has_viz_keywords:
                return {"intent": "QUERY_DATA", "depth": 1, "must_include": [], "context": "Query data fallback"}

            # Priority 3: Visualization
            if has_viz_keywords or "" in query_lower or "" in query_lower:
                return {"intent": "VISUALIZE_DATA", "depth": 1, "must_include": ["create_chart"], "context": "Visualization fallback"}

            # Default: text answer (safer than creating chart)
            return {"intent": "QUESTION", "depth": 1, "must_include": [], "context": "Default fallback"}

    async def generate_action_plan(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None, history: List[dict] = None,
        selected_range: str = None, active_cell: str = None
    ) -> dict:
        """
              (2-step prompting)
        Step 1: Analyze intent
        Step 2: Generate minimal actions

        Args:
            query:  
            column_names:  
            sample_data:  
            history:     
            selected_range:   ( 'H5:H17')
            active_cell:   ( 'H5')
        """
        start_time = time.time()

        # STEP 1: Analyze intent
        intent_analysis = await self._analyze_intent(query, column_names, sample_data, history)

        #    
        columns_info = []
        for i, col in enumerate(column_names):
            col_letter = chr(65 + i)  # A, B, C...
            columns_info.append(f"{col_letter}: {col}")

        #  sample data  
        sample_rows = []
        if sample_data:
            for row in sample_data[:5]:
                sample_rows.append(row)

        #    
        history_context = ""
        if history and len(history) > 0:
            history_context = "\n\n# PREVIOUS ACTIONS (CONVERSATION HISTORY)\n"
            history_context += "User has already performed these actions:\n"
            for i, item in enumerate(history[-3:]):  #  3 
                #    item
                if not isinstance(item, dict):
                    continue

                history_context += f"\n{i+1}. User asked: \"{item.get('query', '')}\"\n"
                if 'actions' in item:
                    actions = item['actions']
                    #   actions  
                    if not isinstance(actions, list):
                        continue

                    history_context += f"   We performed {len(actions)} action(s):\n"
                    for action in actions:
                        #   action  
                        if not isinstance(action, dict):
                            continue
                        config_str = str(action.get('config', {}))[:100]  # First 100 chars
                        history_context += f"   - {action.get('type')}: {config_str}\n"
            history_context += "\n# CRITICAL RULES FOR MODIFYING EXISTING OBJECTS:\n"
            history_context += "\nIf user says ' ', ' ', ' ', ' ' - they refer to objects from PREVIOUS ACTIONS!\n"
            history_context += "\nWhen MODIFYING existing object:\n"
            history_context += "1. COPY ALL parameters from the last matching action in history\n"
            history_context += "2. ONLY change the parameter user asks to change\n"
            history_context += "3. Keep everything else EXACTLY the same (type, dataRange, colors, etc.)\n"
            history_context += "\nEXAMPLE:\n"
            history_context += "Previous: {\"type\": \"create_chart\", \"config\": {\"type\": \"pie\", \"dataRange\": \"A2:B10\", \"title\": \"\"}}\n"
            history_context += "User says: '   '\n"
            history_context += "Correct response: {\"type\": \"create_chart\", \"config\": {\"type\": \"pie\", \"dataRange\": \"A2:B10\", \"title\": \"\"}}\n"
            history_context += "WRONG: Changing type from 'pie' to 'column' - USER DID NOT ASK FOR THIS!\n"

        # STEP 2: Generate actions based on intent
        prompt = f"""Create minimal executable actions based on intent analysis.

# INTENT ANALYSIS
{json.dumps(intent_analysis, ensure_ascii=False)}

# DATA CONTEXT

Columns: {', '.join(columns_info)}
Sample data (5 rows): {json.dumps(sample_rows[:5], ensure_ascii=False) if sample_rows else "[]"}

USER REQUEST: "{query}"{history_context}

# AVAILABLE ACTIONS (USE ONLY THESE 5 TYPES!)

1. create_chart (for graphs/charts)
   Config: {{"dataRange": "A2:B10", "type": "column|bar|line|pie|area", "title": "..."}}

2. format_cells (for static highlighting/coloring of specific cells)
   Config: {{"range": "A1:B10", "backgroundColor": "#hex", "textColor": "#hex", "bold": true, "fontSize": 12}}

3. apply_conditional_format (for DYNAMIC formatting based on conditions - when user wants cells to auto-update color based on value/date)

   SCENARIO A - Ready expiration date column exists:
   Config: {{"range": "A2:H100", "type": "date_expired", "column": "I", "backgroundColor": "#f4cccc"}}
   Use when: There's a column with END date (e.g., " ", "  " as DATE, "Deadline")

   SCENARIO B - Need to calculate expiration (start date + duration in days):
   Config: {{"range": "A2:H100", "type": "custom_formula", "formula": "=$G2+$I2<TODAY()", "backgroundColor": "#f4cccc"}}
   Use when: You have START date column (e.g., " ") + DURATION column (e.g., "  ": 60, 90, 270)
   Formula pattern: =$START_COL2+$DURATION_COL2<TODAY()
   Example: If " " is column G and "   " is column I, use: "=$G2+$I2<TODAY()"

   SCENARIO C - Custom conditions:
   Config: {{"range": "A2:C100", "type": "custom_formula", "formula": "=$B2>1000", "backgroundColor": "#d9ead3"}}

   USE THIS WHEN:
   - User says "  ...", " ...", "   "
   - Formatting should CHANGE automatically when data changes
   - Checking dates (expired, upcoming), comparing values, conditional highlighting

   CRITICAL DECISION LOGIC FOR DATE EXPIRATION:
   1. Check column names carefully - look for "   ", "", "" (these are DURATIONS, not dates!)
   2. If you see duration in DAYS (number like 60, 90, 270), use SCENARIO B with custom_formula: =$START_DATE_COL+$DURATION_COL<TODAY()
   3. If you see actual END DATE (date like 01.05.2023), use SCENARIO A with type="date_expired"
   4. "range" must cover ALL data rows from A to last column (e.g., A2:I100, not A2:H5)
   5. Formula in custom_formula uses $ for absolute column reference (e.g., =$G2, not =G2)

4. insert_formula (for calculations/formulas)
   Config: {{"formula": "=SUM(A2:A10)", "cell": "B2"}}

5. sort_data (for sorting data)
   Config: {{"range": "A2:C10", "column": 2, "ascending": true}}

CRITICAL: NEVER invent new action types. ONLY use these 5 types above!

# ACTION TEMPLATES BY INTENT

## ANALYZE_PROBLEM (depth=3) - Need: sort + format + chart + formula
Example for declining sales analysis:
[
  {{"type": "sort_data", "config": {{"range": "A2:B13", "column": 2, "ascending": false}}}},
  {{"type": "format_cells", "config": {{"range": "B2:B3", "backgroundColor": "#ff0000", "textColor": "#ffffff", "bold": true}}}},
  {{"type": "insert_formula", "config": {{"cell": "C2", "formula": "=AVERAGE(B2:B13)"}}}},
  {{"type": "create_chart", "config": {{"dataRange": "A2:B13", "type": "line", "title": " "}}}}
]

## VISUALIZE_DATA (depth=1) - Need: single chart only
[
  {{"type": "create_chart", "config": {{"dataRange": "A2:B10", "type": "column", "title": ""}}}}
]

## FIND_INSIGHTS (depth=3) - Need: formula + format + chart
[
  {{"type": "insert_formula", "config": {{"cell": "C2", "formula": "=AVERAGE(B:B)"}}}},
  {{"type": "format_cells", "config": {{"range": "B2:B10", "backgroundColor": "#ffeb3b"}}}},
  {{"type": "create_chart", "config": {{"dataRange": "A2:B10", "type": "line", "title": ""}}}}
]

## COMPARE_DATA (depth=2) - Need: sort + chart
[
  {{"type": "sort_data", "config": {{"range": "A2:B10", "column": 2, "ascending": false}}}},
  {{"type": "create_chart", "config": {{"dataRange": "A2:B10", "type": "bar", "title": ""}}}}
]

## FORMAT_PRESENTATION (depth=1) - Need: formatting only
[
  {{"type": "format_cells", "config": {{"range": "A1:B1", "bold": true, "fontSize": 14}}}}
]

## CREATE_STRUCTURE (depth=2-3) - Use REASONING FRAMEWORK!
Think: What data structure is needed? Apply Steps 1-4.

## All Operations - APPLY REASONING FIRST!
Don't look for examples - THINK through Steps 1-4 from system message!

# YOUR TASK
Based on intent analysis above, generate MINIMAL actions to fulfill user's request.
- Use EXACT column letters from DATA CONTEXT
- Match depth level from intent (1 action for depth=1, 2-3 for depth=2, 4+ for depth=3)
- Use must_include actions from intent
- Chart types: column (compare), line (trend), pie (proportions), bar (rankings)
- Titles max 30 chars in Russian
- Be SPECIFIC with ranges

# OUTPUT FORMAT (valid JSON):
{{
  "explanation": "Brief action description in Russian (max 50 chars)",
  "actions": [
    {{"type": "...", "config": {{...}}}}
  ],
  "confidence": 0.85
}}

CRITICAL: Response must be valid JSON. No extra text."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an action generator with REASONING capabilities. Think step-by-step before generating actions.

CRITICAL RESTRICTIONS:
- ONLY 5 action types allowed: create_chart, format_cells, apply_conditional_format, insert_formula, sort_data
- NEVER invent new types like "highlight_trends", "add_summary", etc.
- Output valid JSON only, all explanations in Russian (max 50 chars)
- Use apply_conditional_format (NOT format_cells) when user wants DYNAMIC highlighting based on conditions

# REASONING FRAMEWORK (USE THIS TO THINK!)

Before generating ANY formula, ask yourself these questions:

## STEP 1: Task Scope Analysis
Q: Does this task apply to ONE cell or ALL rows?

Indicators for ALL ROWS:
- Keywords: "", "", "", " ", " ", "  X"
- User wants NEW column with computed values for each row
- Result should auto-fill as data grows

Indicators for ONE CELL:
- Keywords: "", "", " ", ""
- User wants single aggregate value
- Result is one number/text

Decision: If ALL ROWS  MUST use ARRAYFORMULA pattern!

## STEP 2: Operation Type & Context Analysis
What is the core operation?
- Text merge: A&" "&B&" "&C
- Math aggregate: SUM(), AVERAGE(), COUNT()
- Conditional aggregate: SUMIF(), COUNTIF(), AVERAGEIF()
- Unique values: UNIQUE()
- Lookup: VLOOKUP() or INDEX/MATCH
- Grouping: UNIQUE() + SUMIF/COUNTIF or QUERY

  : SUMIF vs QUERY
 THIS IS THE MOST IMPORTANT DECISION! 

STEP-BY-STEP ANALYSIS:
1. Does user mention TWO DIFFERENT columns? (e.g., "  G" + "  H")
2. Check for these EXACT phrases:
   - "  X   Y"
   - "     G"
   - "    Y"
   - "  X   Y"
   - "  H  X   G"
   - ANY variation with " " (from column)

If ANY of these phrases found  100% use SUMIF!

If YES (  ) - USE SUMIF:
- Keywords: "  X   Y", "  H    G", " "
- User mentions TWO columns: criteria column (where to get values FROM) + result column (where to put sums INTO)
- Example: "  H        G"
   Column G = criteria list (already exists)
   Column H = where to put results
 MUST use: ARRAYFORMULA with SUMIF($source$; criteria_column; $sum_column$)
 Example: =ARRAYFORMULA(IF(G2:G=""; ""; SUMIF($D$2:$D; G2:G; $B$2:$B)))

If NO (  ) - USE QUERY:
- Keywords: "   ", " ", "", " "
- User does NOT mention existing criteria column
- User wants to CREATE new unique list + aggregation
 Use QUERY or UNIQUE() + SUMIF pattern

 BEFORE choosing QUERY, ask yourself: "Did user say '  X'?" If YES  SUMIF!

## STEP 3: Formula Construction
Apply the correct pattern based on Steps 1 & 2:

### Pattern for ALL ROWS (ARRAYFORMULA):
```
=ARRAYFORMULA(IF(first_col:first_col=""; ""; operation_here))
```
  :     (;)  !
  Google Sheets       .

Why IF check? Avoids errors on empty rows.

Example thinking:
- User: "    D"
- Step 1: "  D" = ALL ROWS 
- Step 2: "" = text merge  A&" "&B&" "&C
- Step 3: Apply pattern  =ARRAYFORMULA(IF(A2:A="";"";A2:A&" "&B2:B&" "&C2:C))

### Pattern for ONE CELL (simple):
```
=OPERATION(range)
```

Example thinking:
- User: " "
- Step 1: ONE value = ONE CELL 
- Step 2: "" = AVERAGE()
- Step 3: =AVERAGE(B2:B)

## STEP 4: Actions Structure
For column operations, ALWAYS create 3 actions:
1. Header (D1) - insert_formula with text
2. Formula (D2) - insert_formula with actual formula
3. Format header (D1:D1) - format_cells bold

THINK THROUGH THESE STEPS FOR EVERY TASK!

# GOOGLE SHEETS FORMULA REFERENCE (QUICK LOOKUP ONLY)

 :       (;)    !
    Google Sheets.    (,)  !

## 1.   
- SUM(A2:A10) -  
- AVERAGE(A2:A10) -  
- COUNT(A2:A10) -  
- COUNTA(A2:A10) -   
- MAX(A2:A10) -  
- MIN(A2:A10) -  
- MEDIAN(A2:A10) - 
- STDEV(A2:A10) -  

## 2.  
- SUMIF($A$2:$A; ""; $B$2:$B) -    (  !)
- SUMIFS($C$2:$C; $A$2:$A; ""; $B$2:$B; ">100") -    
- COUNTIF($A$2:$A; "") -   
- COUNTIFS($A$2:$A; ""; $B$2:$B; ">100") -    
- AVERAGEIF($A$2:$A; ""; $B$2:$B) -   
- AVERAGEIFS($C$2:$C; $A$2:$A; ""; $B$2:$B; ">100") -    
- IF(A2>100; ""; "") - 
- IFS(A2>1000; ""; A2>500; ""; A2>0; "") -  

    SUMIF/COUNTIF/AVERAGEIF  ARRAYFORMULA:
    ($)     !
: =ARRAYFORMULA(IF(G2:G=""; ""; SUMIF($D$2:$D; G2:G; $B$2:$B)))
         D  B -  ($),  G -  ( $)

## 3.    ( )
- UNIQUE(A2:A100) -   (   !)
- FILTER(A2:B100; B2:B100>1000) -  
- SORT(A2:B100; 2; FALSE) -  ( 2,  )
- QUERY(A2:C100; "SELECT Col1, SUM(Col2) WHERE Col3='' GROUP BY Col1"; 0) - SQL- 
      QUERY:
  1.  Col1, Col2, Col3... ( A, B, C!)
  2.     ,    SELECT/WHERE
  3. Col1 =   , Col2 = ,  ..
  4.   (0  1) =   
  :      B  D,    A2:D ( B2:D),
    QUERY  Col2  Col4 ( A2:D)  Col1  Col3 ( B2:D)
- ARRAYFORMULA(A2:A100 * B2:B100) -    

## 4.   
- VLOOKUP(A2; D2:E100; 2; FALSE) -   (   !)
- XLOOKUP(A2; D2:D100; E2:E100) -   ( )
- INDEX(D2:D100; MATCH(A2; C2:C100; 0)) -   
- MATCH(A2; C2:C100; 0) -    

  : VLOOKUP    ARRAYFORMULA!
 : =ARRAYFORMULA(IF(B2:B=""; ""; VLOOKUP(B2:B; H:I; 2; FALSE)))
 : =ARRAYFORMULA(IF(B2:B=""; ""; INDEX($H:$H; MATCH(B2:B; $I:$I; 0))))

  lookup    INDEX/MATCH!
  : =ARRAYFORMULA(IF(B2:B=""; ""; INDEX($H:$H; MATCH(B2:B; $I:$I; 0)) * IF(C2:C<5; 1; 1.05)))

## 5.  
- CONCATENATE(A2; " "; B2)  A2&" "&B2 -  
- LEFT(A2; 5) -  N 
- RIGHT(A2; 5) -  N 
- MID(A2; 3; 5) -   
- LEN(A2) -  
- TRIM(A2) -   
- UPPER(A2), LOWER(A2), PROPER(A2) -  

## 6.   
- TODAY() -  
- NOW() -    
- DATE(2024, 12, 31) -  
- YEAR(A2), MONTH(A2), DAY(A2) -  
- DATEDIF(A2, B2, "D") -   
- EOMONTH(A2, 0) -  
- WEEKDAY(A2) -   (1-7)

## 7. COMMON PATTERNS (Apply reasoning first!)

Pivot table: UNIQUE() + SUMIF()
Concatenation: ARRAYFORMULA(IF(A2:A="","",A2:A&B2:B))
Top N: SORT() descending
Percentage: value/SUM($range)*100
Grouping: UNIQUE() + conditional functions

REMEMBER: Don't memorize patterns - THINK through Steps 1-4 for each task!"""
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=800,
            )

            result = json.loads(response.choices[0].message.content)

            # Clean formulas in actions before mapping
            if 'actions' in result:
                for action in result['actions']:
                    if action.get('type') == 'insert_formula' and 'config' in action:
                        if 'formula' in action['config']:
                            action['config']['formula'] = self._clean_formula(action['config']['formula'])
                    # :     conditional_format !
                    elif action.get('type') == 'apply_conditional_format' and 'config' in action:
                        if 'formula' in action['config']:
                            action['config']['formula'] = self._clean_formula(action['config']['formula'])

            # Map 'actions' to 'insights' for frontend compatibility
            if 'actions' in result:
                result['insights'] = result.pop('actions')

            # Add intent analysis metadata
            result["intent"] = intent_analysis.get("intent", "UNKNOWN")
            result["depth"] = intent_analysis.get("depth", 1)
            result["processing_time"] = time.time() - start_time
            result["type"] = "action"

            return result

        except Exception as e:
            return {
                "type": "error",
                "explanation": f"  action plan: {str(e)}",
                "insights": [],
                "confidence": 0.0,
                "intent": "UNKNOWN",
                "depth": 0,
                "processing_time": time.time() - start_time
            }

    def get_stats(self) -> Dict[str, Any]:
        """
           
        """
        return self.stats.copy()

    async def generate_actions(
        self,
        query: str,
        sheet_data: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
             Test-and-Heal loop ( )
        PHASE 1.3:  timeout 30 
        CONVERSATION HISTORY:   

        Args:
            query:  
            sheet_data:   :
                {
                    "columns": ["", "", ...],
                    "row_count": 100,
                    "sample_data": [[...], [...], ...],
                    "sheet_id": "abc123"
                }
            conversation_id: ID     ()

        Returns:
            {
                "success": True/False,
                "actions": [...],
                "source": "template" | "gpt",
                "validation_log": {...} (  ),
                "execution": {...} ( Test-and-Heal ),
                "conversation_id": "..." (  ),
                "error": "..." ( )
            }
        """
        self.stats["total_requests"] += 1

        # PHASE 1.3: Timeout wrapper
        try:
            result = await asyncio.wait_for(
                self._generate_actions_internal(query, sheet_data, conversation_id),
                timeout=TOTAL_GENERATION_TIMEOUT
            )
            return result
        except asyncio.TimeoutError:
            # PHASE 1.5: Honest failure message
            return {
                "success": False,
                "error": f"Generation timeout ({TOTAL_GENERATION_TIMEOUT}s exceeded). Try simplifying your request or break it into smaller tasks.",
                "actions": [],
                "error_type": "timeout"
            }
        except Exception as e:
            # PHASE 1.5: Honest failure message
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
                "actions": [],
                "error_type": "internal_error"
            }

    async def _generate_actions_internal(
        self,
        query: str,
        sheet_data: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal implementation of generate_actions (wrapped with timeout)

          (Interactive Builder):
        1. Intent Parser ->    certainty (  !)
        2.  certainty < 0.9 ->    
        3.  certainty >= 0.9 -> Action Composer   action
        4. Fallback     GPT  -   
        5. CONVERSATION HISTORY:  reference queries ("  ", etc.)
        """

        try:
            # ===== INTERACTIVE BUILDER PATH =====
            from app.services.intent_parser import IntentParser, IntentType
            from app.services.clarification_dialog import ClarificationDialog
            from app.services.action_composer import ActionComposer, ActionCompositionError
            from app.services.intent_store import intent_store

            column_names = sheet_data.get("columns", [])
            sample_data = sheet_data.get("sample_data", [])
            row_count = sheet_data.get("row_count", len(sample_data) if sample_data else 100)

            context = {
                "columns": [chr(65 + i) for i in range(len(column_names))],  # A, B, C, ...
                "column_names": column_names,
                "sample_data": sample_data[:10] if sample_data else [],  #  10   
                "row_count": row_count
            }

            #  1:  conversation   intent ( )
            conversation = None
            previous_intent = None

            if conversation_id:
                conversation = intent_store.get_conversation(conversation_id)
                if conversation:
                    previous_intent = conversation.get_last_successful_intent()

            #  conversation_id  ,  
            if not conversation_id:
                conversation_id = intent_store.create_conversation()

            #  2:  intent    ( )
            parser = IntentParser()

            if previous_intent:
                #  parse_with_history   reference queries
                intent = parser.parse_with_history(query, context, previous_intent)
            else:
                #    
                intent = parser.parse(query, context)

            #  2:    
            dialog = ClarificationDialog(certainty_threshold=0.9)

            if dialog.needs_clarification(intent):
                #    
                questions = dialog.generate_questions(intent)

                #  Intent   
                intent_id = intent_store.save(intent)

                result = {
                    "success": False,
                    "needs_clarification": True,
                    "intent_id": intent_id,  # ID   
                    "conversation_id": conversation_id,  #  conversation_id
                    "questions": [
                        {
                            "parameter": q.parameter_name,
                            "text": q.question_text,
                            "type": q.question_type,
                            "options": q.options,
                            "required": q.required,
                            "help": q.help_text
                        }
                        for q in questions
                    ],
                    "intent_certainty": intent.certainty,
                    "message": ",      "
                }

                #  turn  conversation history ( clarification questions)
                intent_store.add_conversation_turn(
                    conversation_id=conversation_id,
                    query=query,
                    intent=intent,
                    result=result
                )

                return result

            #  3:   action  Action Composer
            composer = ActionComposer(min_certainty=0.9)

            try:
                action_obj = composer.compose(intent)

                #     API
                action = {
                    "type": action_obj.type,
                    "config": action_obj.config,
                    "reasoning": action_obj.explanation,
                    "source": "interactive_builder",  #  !
                    "confidence": action_obj.confidence
                }

                #  4: Test-and-Heal loop (  )
                if action["type"] == "insert_formula" and self.enable_test_and_heal and self.executor:
                    formula = action["config"]["formula"]
                    cell = action["config"]["cell"]

                    healing_result = await self._test_and_heal_formula(
                        formula,
                        cell,
                        sheet_data.get("sheet_id", "test-sheet"),
                        {
                            "query": query,
                            "columns": column_names
                        }
                    )

                    action["execution"] = healing_result

                    if not healing_result["success"]:
                        return {
                            "success": False,
                            "error": "Formula failed after healing attempts",
                            "actions": [action],
                            "conversation_id": conversation_id
                        }

                #  
                result = {
                    "success": True,
                    "actions": [action],
                    "source": "interactive_builder",
                    "confidence": action_obj.confidence,
                    "explanation": action_obj.explanation,
                    "conversation_id": conversation_id  #  conversation_id
                }

                #  5:  turn  conversation history
                intent_store.add_conversation_turn(
                    conversation_id=conversation_id,
                    query=query,
                    intent=intent,
                    result=result
                )

                return result

            except ActionCompositionError as e:
                # Action Composer    action -   
                #  dialog.needs_clarification()   !
                #  edge case -  
                return {
                    "success": False,
                    "error": f"Cannot create action: {str(e)}",
                    "needs_clarification": True,
                    "message": "     .   ."
                }

        except Exception as interactive_error:
            # ===== FALLBACK TO OLD PATH =====
            #  Interactive Builder  ,   
            print(f"[FALLBACK] Interactive Builder failed: {interactive_error}. Using old path.")

            try:
                #  1:   ( generate_formula)
                column_names = sheet_data.get("columns", [])
                sample_data = sheet_data.get("sample_data", [])

                formula_result = await self.generate_formula(
                    query,
                    column_names,
                    sample_data
                )

                if formula_result.get("type") == "error":
                    return {
                        "success": False,
                        "error": formula_result.get("explanation", "Unknown error"),
                        "actions": []
                    }

                formula = formula_result.get("formula")

                #  action
                action = {
                    "type": "insert_formula",
                    "config": {
                        "cell": formula_result.get("target_cell", "D1"),
                        "formula": formula
                    },
                    "reasoning": formula_result.get("explanation", ""),
                    "source": formula_result.get("source", "gpt")
                }

                #  2: Test-and-Heal loop ( )
                if self.enable_test_and_heal and self.executor:
                    healing_result = await self._test_and_heal_formula(
                        formula,
                        action["config"]["cell"],
                        sheet_data.get("sheet_id", "test-sheet"),
                        {
                            "query": query,
                            "columns": column_names
                        }
                    )

                    action["execution"] = healing_result

                    if not healing_result["success"]:
                        return {
                            "success": False,
                            "error": "Formula failed after healing attempts",
                            "actions": [action],
                            "validation_log": formula_result.get("validation_log")
                        }

                return {
                    "success": True,
                    "actions": [action],
                    "source": formula_result.get("source"),
                    "validation_log": formula_result.get("validation_log")
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "actions": []
                }

    async def apply_clarification(
        self,
        intent_id: str,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
            clarification    action

        Args:
            intent_id: ID  Intent
            answers:   {parameter_name: value}

        Returns:
              action  
        """
        try:
            #   Intent
            from app.services.intent_store import intent_store
            from app.services.clarification_dialog import ClarificationDialog
            from app.services.action_composer import ActionComposer, ActionCompositionError

            intent = intent_store.get(intent_id)

            if not intent:
                return {
                    "success": False,
                    "error": "Intent not found or expired. Please start over.",
                    "error_type": "intent_expired"
                }

            #    Intent
            dialog = ClarificationDialog()
            intent_with_answers = dialog.apply_answers(intent, answers)

            #  action  Action Composer
            composer = ActionComposer(min_certainty=0.9)

            try:
                action_obj = composer.compose(intent_with_answers)

                #    API
                action = {
                    "type": action_obj.type,
                    "config": action_obj.config,
                    "reasoning": action_obj.explanation,
                    "source": "interactive_builder",
                    "confidence": action_obj.confidence
                }

                #  Intent  store (  )
                intent_store.delete(intent_id)

                return {
                    "success": True,
                    "actions": [action],
                    "source": "interactive_builder",
                    "confidence": action_obj.confidence,
                    "explanation": action_obj.explanation
                }

            except ActionCompositionError as e:
                #    
                return {
                    "success": False,
                    "error": f"Cannot create action: {str(e)}",
                    "needs_more_clarification": True
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "internal_error"
            }

    async def _test_and_heal_formula(
        self,
        formula: str,
        cell: str,
        sheet_id: str,
        context: Dict[str, Any],
        max_attempts: int = MAX_HEAL_ATTEMPTS  # PHASE 1.3: Use constant
    ) -> Dict[str, Any]:
        """
        Test-and-Heal loop

            Sheets,    -   

        Returns:
            {
                "tested": True,
                "success": True/False,
                "attempts": 2,
                "healed": True/False,
                "final_formula": "=...",
                "error": "..." (  )
            }
        """

        current_formula = formula
        attempt = 1

        while attempt <= max_attempts:
            #  
            exec_result = await self.executor.execute_and_verify(
                sheet_id,
                cell,
                current_formula
            )

            if exec_result.success:
                # !
                return {
                    "tested": True,
                    "success": True,
                    "attempts": attempt,
                    "healed": attempt > 1,
                    "final_formula": current_formula
                }

            #    -  
            self.stats["healing_attempts"] += 1

            if attempt >= max_attempts:
                # PHASE 1.5: Honest failure message -  
                return {
                    "tested": True,
                    "success": False,
                    "attempts": attempt,
                    "healed": False,
                    "error": f"Formula failed after {max_attempts} attempts. Last error: {exec_result.error}",
                    "error_type": exec_result.error_type,
                    "suggestion": "Try rephrasing your request or breaking it into smaller steps"
                }

            #  healing
            healed_formula = await self.healing_service.heal_formula(
                current_formula,
                {
                    "error_type": exec_result.error_type,
                    "error_message": exec_result.error,
                    "result_preview": exec_result.result_preview
                },
                context,
                attempt
            )

            if healed_formula and healed_formula != current_formula:
                #    -  
                current_formula = healed_formula
                attempt += 1
                continue
            else:
                # PHASE 1.5: Honest failure - healing   
                return {
                    "tested": True,
                    "success": False,
                    "attempts": attempt,
                    "healed": False,
                    "error": f"Unable to fix formula automatically. Original error: {exec_result.error}",
                    "error_type": exec_result.error_type,
                    "suggestion": "This task may be too complex for automatic formula generation. Consider manual approach or break into simpler steps."
                }

        # PHASE 1.5: Honest failure - fallback case
        return {
            "tested": True,
            "success": False,
            "attempts": max_attempts,
            "healed": False,
            "error": f"Formula generation failed after {max_attempts} attempts",
            "suggestion": "Try breaking your task into smaller, simpler steps"
        }


# 
ai_service = AIService()
