"""Планы подписки и их лимиты"""

from typing import Dict, Any

# Планы подписки
SUBSCRIPTION_PLANS: Dict[str, Dict[str, Any]] = {
    'free': {
        'name': 'Free',
        'price': 0,
        'currency': 'USD',
        'billing_cycle': 'monthly',
        'queries_limit': 50,
        'features': [
            'basic_analysis',
            'sidebar_interface',
            'community_support'
        ],
        'description': 'Попробуйте SheetGPT бесплатно'
    },
    'starter': {
        'name': 'Starter',
        'price': 9,
        'currency': 'USD',
        'billing_cycle': 'monthly',
        'queries_limit': 500,
        'features': [
            'basic_analysis',
            'sidebar_interface',
            'formulas',
            'batch_processing',
            'email_support'
        ],
        'description': 'Для индивидуальных пользователей'
    },
    'pro': {
        'name': 'Pro',
        'price': 19,
        'currency': 'USD',
        'billing_cycle': 'monthly',
        'queries_limit': 2000,
        'features': [
            'basic_analysis',
            'sidebar_interface',
            'formulas',
            'batch_processing',
            'advanced_analytics',
            'priority_support',
            'custom_models'
        ],
        'description': 'Для профессионалов и команд'
    },
    'business': {
        'name': 'Business',
        'price': 49,
        'currency': 'USD',
        'billing_cycle': 'monthly',
        'queries_limit': -1,  # unlimited
        'features': [
            'basic_analysis',
            'sidebar_interface',
            'formulas',
            'batch_processing',
            'advanced_analytics',
            'priority_support',
            'custom_models',
            'api_access',
            'white_label',
            'dedicated_support',
            'sla'
        ],
        'description': 'Для enterprise клиентов'
    }
}


def get_plan_limits(tier: str) -> Dict[str, Any]:
    """
    Получить лимиты для плана подписки

    Args:
        tier: Название плана (free, starter, pro, business)

    Returns:
        Словарь с лимитами плана
    """
    plan = SUBSCRIPTION_PLANS.get(tier.lower())
    if not plan:
        # Fallback на free plan
        plan = SUBSCRIPTION_PLANS['free']

    return {
        'tier': tier,
        'queries_limit': plan['queries_limit'],
        'features': plan['features'],
        'name': plan['name'],
        'price': plan['price']
    }


def has_feature(tier: str, feature: str) -> bool:
    """
    Проверить, есть ли у плана определенная фича

    Args:
        tier: Название плана
        feature: Название фичи

    Returns:
        True если фича доступна, False иначе
    """
    plan = SUBSCRIPTION_PLANS.get(tier.lower(), SUBSCRIPTION_PLANS['free'])
    return feature in plan['features']


def is_unlimited(tier: str) -> bool:
    """
    Проверить, безлимитный ли план

    Args:
        tier: Название плана

    Returns:
        True если план безлимитный, False иначе
    """
    plan = SUBSCRIPTION_PLANS.get(tier.lower(), SUBSCRIPTION_PLANS['free'])
    return plan['queries_limit'] == -1
