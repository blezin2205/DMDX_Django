import logging
from pathlib import Path

from django.conf import settings

from .app_settings_fields import MOBILE_APP_SETTINGS_DEFAULTS

logger = logging.getLogger(__name__)

_firebase_initialized = False

ORDER_NOTIFICATION_KINDS = frozenset({'order', 'reminder_orders'})
PREORDER_NOTIFICATION_KINDS = frozenset({'preorder', 'reminder_preorders'})

ORDER_PUSH_CONFIG = {
    'order': ('push_new_orders', 'push_new_orders_clients_only'),
    'reminder_orders': ('push_new_orders', None),
}
PREORDER_PUSH_CONFIG = {
    'preorder': ('push_new_preorders', 'push_new_preorders_clients_only'),
    'reminder_preorders': ('push_new_preorders', None),
}


def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return True

    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
    if not cred_path:
        return False

    path = Path(cred_path)
    if not path.exists():
        logger.warning('Firebase credentials file not found: %s', path)
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(path))
            firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        return True
    except Exception:
        logger.exception('Failed to initialize Firebase Admin SDK')
        return False


def _deactivate_stale_tokens(tokens):
    if not tokens:
        return
    try:
        from .models import FcmDevice
        FcmDevice.objects.filter(token__in=tokens).update(is_active=False)
    except Exception:
        logger.exception('Failed to deactivate stale FCM tokens')


def send_push_to_tokens(tokens, title, body, data=None):
    tokens = [t for t in tokens if t]
    if not tokens:
        return

    if not _init_firebase():
        logger.info('Firebase not configured; skip push: %s', title)
        return

    try:
        from firebase_admin import messaging
        from firebase_admin.messaging import UnregisteredError

        payload_data = {k: str(v) for k, v in (data or {}).items()}
        success = 0
        failure = 0
        stale_tokens = []

        for fcm_token in tokens:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=payload_data,
                token=fcm_token,
            )
            try:
                messaging.send(message)
                success += 1
            except UnregisteredError:
                failure += 1
                stale_tokens.append(fcm_token)
            except Exception:
                failure += 1
                logger.exception(
                    'FCM send failed for token prefix %s...',
                    fcm_token[:12],
                )

        _deactivate_stale_tokens(stale_tokens)
        logger.info('FCM sent: success=%s failure=%s', success, failure)
    except Exception:
        logger.exception('Failed to send FCM push')


def _get_staff_push_tokens(notification_kind, creator=None):
    """Токени staff з урахуванням мобільних push-налаштувань; без відправки собі."""
    from .models import AppSettings, CustomUser, FcmDevice

    if notification_kind in ORDER_NOTIFICATION_KINDS:
        enabled_field, clients_only_field = ORDER_PUSH_CONFIG[notification_kind]
    elif notification_kind in PREORDER_NOTIFICATION_KINDS:
        enabled_field, clients_only_field = PREORDER_PUSH_CONFIG[notification_kind]
    else:
        return []

    staff_qs = CustomUser.objects.filter(is_active=True, is_staff=True)
    if creator and creator.pk:
        staff_qs = staff_qs.exclude(pk=creator.pk)

    staff_ids = list(staff_qs.values_list('pk', flat=True))
    if not staff_ids:
        return []

    settings_by_user = {
        row.userCreated_id: row
        for row in AppSettings.objects.filter(userCreated_id__in=staff_ids)
    }

    creator_is_client = creator.isClient() if creator else None
    recipient_ids = []

    for user_id in staff_ids:
        app_settings = settings_by_user.get(user_id)
        if app_settings is None:
            enabled = MOBILE_APP_SETTINGS_DEFAULTS[enabled_field]
            clients_only = (
                MOBILE_APP_SETTINGS_DEFAULTS[clients_only_field]
                if clients_only_field else False
            )
        else:
            enabled = getattr(app_settings, enabled_field)
            clients_only = (
                getattr(app_settings, clients_only_field)
                if clients_only_field else False
            )

        if not enabled:
            continue
        if clients_only_field and clients_only and creator is not None and not creator_is_client:
            continue
        recipient_ids.append(user_id)

    if not recipient_ids:
        return []

    return list(
        FcmDevice.objects.filter(user_id__in=recipient_ids, is_active=True).values_list('token', flat=True)
    )


def _creator_name(user):
    if not user:
        return 'Невідомо'
    name = f'{user.first_name or ""} {user.last_name or ""}'.strip()
    return name or user.username


def _place_label(place):
    if not place:
        return 'Без назви'
    city = getattr(getattr(place, 'city_ref', None), 'name', None)
    if city:
        return f'{place.name}, {city}'
    return place.name


def notify_staff_new_order(order):
    tokens = _get_staff_push_tokens('order', creator=order.userCreated)
    place_label = _place_label(order.place)
    creator_name = _creator_name(order.userCreated)
    send_push_to_tokens(
        tokens=tokens,
        title=f'Нове замовлення №{order.id}',
        body=f'{place_label}\nСтворив: {creator_name}',
        data={
            'type': 'new_order',
            'order_id': order.id,
            'place': place_label,
            'created_by': creator_name,
        },
    )


def notify_staff_new_preorder(preorder):
    tokens = _get_staff_push_tokens('preorder', creator=preorder.userCreated)
    place_label = _place_label(preorder.place)
    creator_name = _creator_name(preorder.userCreated)
    send_push_to_tokens(
        tokens=tokens,
        title=f'Нове передзамовлення №{preorder.id}',
        body=f'{place_label}\nСтворив: {creator_name}',
        data={
            'type': 'new_preorder',
            'preorder_id': preorder.id,
            'place': place_label,
            'created_by': creator_name,
        },
    )


def notify_staff_reminder(title, body, notification_kind):
    tokens = _get_staff_push_tokens(notification_kind, creator=None)
    send_push_to_tokens(
        tokens=tokens,
        title=title,
        body=body,
        data={'type': notification_kind},
    )


def send_push_new_order(order):
    try:
        notify_staff_new_order(order)
    except Exception:
        logger.exception('Failed to send push for order %s', getattr(order, 'id', '?'))


def send_push_new_preorder(preorder):
    try:
        notify_staff_new_preorder(preorder)
    except Exception:
        logger.exception('Failed to send push for preorder %s', getattr(preorder, 'id', '?'))
