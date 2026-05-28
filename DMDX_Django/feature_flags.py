"""
Перемикачі інтеграцій для діагностики продуктивності.

LIGHTWEIGHT_MODE=1 вимикає: Channels, wkhtmltopdf/xhtml2pdf
"""
from __future__ import annotations

import os


def _env_bool(name: str, default: str = '0') -> bool:
    return os.getenv(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


LIGHTWEIGHT_MODE = _env_bool('LIGHTWEIGHT_MODE')


def _flag(*, lightweight: bool, env_name: str, default: str = '1') -> bool:
    if LIGHTWEIGHT_MODE:
        return lightweight
    return _env_bool(env_name, default)


ENABLE_CHANNELS = _flag(lightweight=False, env_name='ENABLE_CHANNELS')
ENABLE_WKHTMLTOPDF = _flag(lightweight=False, env_name='ENABLE_WKHTMLTOPDF')

_APPS_TO_DROP = {
    'channels': lambda: not ENABLE_CHANNELS,
    'wkhtmltopdf': lambda: not ENABLE_WKHTMLTOPDF,
}


def filter_installed_apps(apps: list[str]) -> list[str]:
    out: list[str] = []
    for app in apps:
        drop = _APPS_TO_DROP.get(app)
        if drop and drop():
            continue
        out.append(app)
    return out
