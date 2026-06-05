"""Поля AppSettings для мобільного додатку (GET/PATCH api/desktop/app-settings)."""

MOBILE_APP_SETTINGS_FIELDS = (
    'push_new_orders',
    'push_new_orders_clients_only',
    'push_new_preorders',
    'push_new_preorders_clients_only',
    'enable_show_other_booked_cart',
    'disable_order_confirmation_send_action',
    'enable_preorder_editing_awaiting_state',
    'home_show_edit_mode',
    'home_show_order_cart',
    'home_show_precart',
    'home_show_smn',
)

MOBILE_APP_SETTINGS_DEFAULTS = {
    'push_new_orders': True,
    'push_new_orders_clients_only': False,
    'push_new_preorders': True,
    'push_new_preorders_clients_only': False,
    'enable_show_other_booked_cart': False,
    'disable_order_confirmation_send_action': False,
    'enable_preorder_editing_awaiting_state': False,
    'home_show_edit_mode': True,
    'home_show_order_cart': True,
    'home_show_precart': True,
    'home_show_smn': True,
}

APP_SETTINGS_CREATE_DEFAULTS = dict(MOBILE_APP_SETTINGS_DEFAULTS)

WEB_APP_SETTINGS_FORM_FIELDS = (
    'enable_show_other_booked_cart',
    'disable_order_confirmation_send_action',
    'enable_preorder_editing_awaiting_state',
)


def serialize_app_settings(app_settings):
    if app_settings is None:
        return dict(MOBILE_APP_SETTINGS_DEFAULTS)
    return {
        field: bool(getattr(app_settings, field, MOBILE_APP_SETTINGS_DEFAULTS[field]))
        for field in MOBILE_APP_SETTINGS_FIELDS
    }
