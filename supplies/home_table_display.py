"""Налаштування виду таблиці на головній (Всі) — зберігаються в AppSettings."""

HOME_TABLE_DISPLAY_JS_TO_MODEL = {
    'edit': 'home_show_edit_mode',
    'cart': 'home_show_order_cart',
    'precart': 'home_show_precart',
    'smn': 'home_show_smn',
}

HOME_TABLE_DISPLAY_DEFAULTS = {
    'edit': True,
    'cart': True,
    'precart': True,
    'smn': True,
}


def home_table_display_settings_for_user(user):
    app = user.get_app_settings()
    return {
        key: bool(getattr(app, field, True))
        for key, field in HOME_TABLE_DISPLAY_JS_TO_MODEL.items()
    }
