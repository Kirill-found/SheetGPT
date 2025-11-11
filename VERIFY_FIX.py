#!/usr/bin/env python3
"""
Скрипт для проверки что агрегация работает правильно
"""

import requests
import json
from colorama import init, Fore, Style

init()

def test_aggregation():
    """Тестирует агрегацию напрямую через API"""

    print(f"{Fore.CYAN}{'='*60}")
    print(f"PROVERKA ISPRAVLENIYA AGREGATSII")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    # Тестовые данные
    test_data = {
        "query": "у какого поставщика больше всего продаж",
        "column_names": ["Колонка A", "Колонка B", "Колонка C", "Колонка D", "Колонка E"],
        "sheet_data": [
            ["Товар 1", "ООО Время", 10730.32, 1010, 107303.2],
            ["Товар 2", "ООО Сатурн", 8568.37, 1030, 257051.1],
            ["Товар 3", "ООО Луна", 7318.09, 1020, 146361.8],
            ["Товар 14", "ООО Время", 6328.28, 1007, 44297.96],
            ["Товар 5", "ООО Персектив", 1196.9, 1017, 20347.3],
            ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44],
            ["Товар 7", "ООО Космос", 2499.28, 1012, 29991.36],
            ["Товар 8", "ООО Радость", 25212.79, 1015, 378191.85],
            ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44],
            ["Товар 10", "ИП Разум", 17789.22, 1010, 177892.2]
        ],
        "history": []
    }

    # Правильный ответ
    correct_answer = {
        "supplier": "ООО Время",
        "total": 442702.04
    }

    # Отправляем запрос
    url = "https://sheetgpt-production.up.railway.app/api/v1/formula"

    print(f"Otpravlyayu zapros na {url}")
    print(f"Dannye: {len(test_data['sheet_data'])} strok\n")

    try:
        response = requests.post(url, json=test_data, timeout=30)

        if response.status_code == 200:
            result = response.json()

            print(f"{Fore.GREEN}[OK] Otvet poluchen!{Style.RESET_ALL}")
            print(f"\nSummary: {result.get('summary', 'НЕТ')}")
            print(f"\nMethodology:\n{result.get('methodology', 'НЕТ')}")
            print(f"\nKey Findings:")
            for finding in result.get('key_findings', []):
                print(f"   • {finding}")

            # Проверяем правильность
            summary = result.get('summary', '').lower()

            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"ПРОВЕРКА РЕЗУЛЬТАТА:")
            print(f"{'='*60}{Style.RESET_ALL}\n")

            if 'время' in summary and '442' in summary:
                print(f"{Fore.GREEN}[CORRECT] PRAVILNO! Sistema vozvrashaet OOO Vremya!{Style.RESET_ALL}")
                print(f"[OK] Ozhidaetsya: {correct_answer['supplier']}: {correct_answer['total']:,.2f}")
                print(f"[OK] Polucheno: {result.get('summary', '')}")
            elif 'радость' in summary:
                print(f"{Fore.RED}[ERROR] OSHIBKA! Sistema vse eshe vozvrashaet OOO Radost!{Style.RESET_ALL}")
                print(f"[X] Ozhidaetsya: {correct_answer['supplier']}: {correct_answer['total']:,.2f}")
                print(f"[X] Polucheno: {result.get('summary', '')}")
                print(f"\n{Fore.YELLOW}[WARNING] NUZHNO PROVERIT:{Style.RESET_ALL}")
                print("1. Версия API (должна быть 3.0.0)")
                print("2. Логи Railway на наличие 'PYTHON AGGREGATION v3.0'")
                print("3. Правильно ли заменён ai_service.py")
            else:
                print(f"{Fore.YELLOW}[?] Neopredelennyy rezultat{Style.RESET_ALL}")
                print(f"Polucheno: {result.get('summary', 'Net summary')}")

            # Полный ответ для отладки
            print(f"\n{Fore.CYAN}Polnyy otvet API:{Style.RESET_ALL}")
            print(json.dumps(result, ensure_ascii=False, indent=2))

        else:
            print(f"{Fore.RED}[X] Oshibka HTTP {response.status_code}{Style.RESET_ALL}")
            print(f"Otvet: {response.text}")

    except requests.exceptions.Timeout:
        print(f"{Fore.RED}[X] Timeout zaprosa (30 sek){Style.RESET_ALL}")
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}[X] Ne mogu podkluchitsya k API{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[X] Oshibka: {str(e)}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"Тест завершён")
    print(f"{'='*60}{Style.RESET_ALL}\n")


def check_version():
    """Проверяет версию API"""
    url = "https://sheetgpt-production.up.railway.app/"

    print(f"Proveryayu versiyu API...")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            version = data.get('version', 'unknown')

            if version == "3.0.0":
                print(f"{Fore.GREEN}[OK] Versiya API: {version} - PRAVILNAYA!{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[!] Versiya API: {version} - nuzhno obnovit do 3.0.0{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[X] Ne mogu poluchit versiyu{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[X] Oshibka: {str(e)}{Style.RESET_ALL}")
    print()


if __name__ == "__main__":
    # Сначала проверяем версию
    check_version()

    # Затем тестируем агрегацию
    test_aggregation()

    input("\nНажми Enter для выхода...")