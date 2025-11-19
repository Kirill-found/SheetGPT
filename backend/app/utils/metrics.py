"""
Monitoring и metrics для отслеживания performance и успешности запросов
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps
import json

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Собирает и логирует метрики выполнения запросов
    """

    def __init__(self):
        self.metrics = []

    def log_execution(
        self,
        function_name: str,
        success: bool,
        duration_ms: float,
        query: str = "",
        error: Optional[str] = None,
        response_type: str = "",
        confidence: float = 0.0,
        num_functions_sent: int = 100,
        categories: list = None
    ):
        """
        Логирует метрики выполнения функции
        """
        metric = {
            "timestamp": datetime.now().isoformat(),
            "function": function_name,
            "success": success,
            "duration_ms": round(duration_ms, 2),
            "query_preview": query[:50] if query else "",
            "error": error,
            "response_type": response_type,
            "confidence": confidence,
            "num_functions_sent": num_functions_sent,
            "categories": categories or [],
        }

        self.metrics.append(metric)

        # Логируем в консоль
        if success:
            logger.info(f"[METRICS] ✅ {function_name} | {duration_ms:.0f}ms | {num_functions_sent} functions")
        else:
            logger.error(f"[METRICS] ❌ {function_name} | {duration_ms:.0f}ms | Error: {error}")

        # Можно отправить в внешний сервис (Datadog, CloudWatch, etc.)
        # self._send_to_external_service(metric)

    def log_fuzzy_match(
        self,
        requested_column: str,
        matched_column: Optional[str],
        available_columns: list,
        method: str = "unknown"
    ):
        """
        Логирует результаты fuzzy matching для анализа
        """
        metric = {
            "timestamp": datetime.now().isoformat(),
            "type": "fuzzy_match",
            "requested": requested_column,
            "matched": matched_column,
            "available": available_columns,
            "method": method,
            "success": matched_column is not None
        }

        self.metrics.append(metric)

        if matched_column:
            logger.info(f"[FUZZY] ✅ '{requested_column}' → '{matched_column}' ({method})")
        else:
            logger.warning(f"[FUZZY] ❌ '{requested_column}' not found in {available_columns}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Возвращает summary метрик
        """
        if not self.metrics:
            return {"total": 0}

        execution_metrics = [m for m in self.metrics if m.get("function")]

        total = len(execution_metrics)
        success = sum(1 for m in execution_metrics if m["success"])
        failed = total - success

        avg_duration = sum(m["duration_ms"] for m in execution_metrics) / total if total > 0 else 0

        # Самые популярные функции
        function_counts = {}
        for m in execution_metrics:
            func = m.get("function", "unknown")
            function_counts[func] = function_counts.get(func, 0) + 1

        top_functions = sorted(function_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Самые частые ошибки
        error_counts = {}
        for m in execution_metrics:
            if not m["success"] and m.get("error"):
                error = m["error"]
                error_counts[error] = error_counts.get(error, 0) + 1

        top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_requests": total,
            "successful": success,
            "failed": failed,
            "success_rate": f"{success/total*100:.1f}%" if total > 0 else "0%",
            "avg_duration_ms": round(avg_duration, 2),
            "top_functions": top_functions,
            "top_errors": top_errors,
        }

    def print_summary(self):
        """
        Выводит summary в консоль
        """
        summary = self.get_summary()

        print("\n" + "=" * 80)
        print("📊 METRICS SUMMARY")
        print("=" * 80)

        print(f"\n📈 Overall Stats:")
        print(f"   Total Requests: {summary.get('total_requests', 0)}")
        print(f"   Success Rate: {summary.get('success_rate', '0%')}")
        print(f"   Avg Duration: {summary.get('avg_duration_ms', 0)}ms")

        if summary.get("top_functions"):
            print(f"\n🔥 Top Functions:")
            for func, count in summary["top_functions"]:
                print(f"   {func}: {count}")

        if summary.get("top_errors"):
            print(f"\n❌ Top Errors:")
            for error, count in summary["top_errors"]:
                print(f"   {error[:60]}: {count}")

        print("\n" + "=" * 80 + "\n")


# Global instance
metrics_collector = MetricsCollector()


def track_execution(func):
    """
    Decorator для автоматического отслеживания времени выполнения
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        error = None
        success = True

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error = str(e)
            success = False
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            metrics_collector.log_execution(
                function_name=func.__name__,
                success=success,
                duration_ms=duration_ms,
                error=error
            )

    return wrapper


# Пример использования
if __name__ == "__main__":
    # Симулируем несколько запросов
    metrics = MetricsCollector()

    # Успешные запросы
    metrics.log_execution("calculate_sum", True, 1250, "Сумма продаж", confidence=0.98, num_functions_sent=15)
    metrics.log_execution("filter_top_n", True, 2100, "Топ 5", confidence=0.95, num_functions_sent=20)
    metrics.log_execution("group_by_column", True, 1800, "Группировка", confidence=0.92, num_functions_sent=25)

    # Провал
    metrics.log_execution("filter_rows", False, 1500, "Фильтр", error="Column 'Продажи' not found", num_functions_sent=20)

    # Fuzzy matching
    metrics.log_fuzzy_match("Продажи", "Сумма продаж", ["Менеджер", "Сумма продаж", "Дата"], method="synonym")
    metrics.log_fuzzy_match("Несуществующая", None, ["Менеджер", "Продажи"], method="none")

    # Summary
    metrics.print_summary()
