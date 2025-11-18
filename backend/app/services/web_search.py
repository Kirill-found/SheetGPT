"""
Web Search Service
Использует DuckDuckGo для поиска информации в интернете (100% бесплатно, без API ключей)
"""

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class WebSearchService:
    """Сервис для поиска информации в интернете"""

    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Выполняет поиск в интернете через DuckDuckGo

        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов (по умолчанию 10)

        Returns:
            Список словарей с результатами:
            [
                {
                    "title": "Заголовок",
                    "body": "Описание",
                    "href": "URL"
                },
                ...
            ]
        """
        try:
            logger.info(f"[WEB_SEARCH] Searching for: {query}")

            # Выполняем поиск текстовых результатов
            results = []
            for result in self.ddgs.text(query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "body": result.get("body", ""),
                    "href": result.get("href", "")
                })

            logger.info(f"[WEB_SEARCH] Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"[WEB_SEARCH] Error during search: {e}")
            return []

    def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Поиск новостей через DuckDuckGo

        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов

        Returns:
            Список новостей с датами публикации
        """
        try:
            logger.info(f"[WEB_SEARCH_NEWS] Searching news for: {query}")

            results = []
            for result in self.ddgs.news(query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "body": result.get("body", ""),
                    "href": result.get("url", ""),
                    "date": result.get("date", "")
                })

            logger.info(f"[WEB_SEARCH_NEWS] Found {len(results)} news articles")
            return results

        except Exception as e:
            logger.error(f"[WEB_SEARCH_NEWS] Error during news search: {e}")
            return []

    def format_search_results_for_ai(self, results: List[Dict[str, str]]) -> str:
        """
        Форматирует результаты поиска для передачи в GPT-4

        Args:
            results: Список результатов поиска

        Returns:
            Отформатированная строка с результатами
        """
        if not results:
            return "Результатов не найдено."

        formatted = "РЕЗУЛЬТАТЫ ПОИСКА В ИНТЕРНЕТЕ:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. {result['title']}\n"
            formatted += f"   {result['body'][:200]}...\n"
            formatted += f"   Источник: {result['href']}\n\n"

        return formatted


# Singleton
web_search_service = WebSearchService()


def get_web_search_service() -> WebSearchService:
    """Возвращает singleton instance веб-поиска"""
    return web_search_service
