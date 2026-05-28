"""Top bar badge counts (cart, orders, preorders). Used by context processor and legacy call sites."""

from __future__ import annotations

from datetime import date

from django.db.models import Count, Q, Sum

from .models import (
    BookedOrderInCart,
    Order,
    PreOrder,
    StatusNPParselFromDoucmentID,
)
from .user_request_cache import active_order_in_cart, active_preorder_in_cart

_NP_UNCOMPLETED_CODES = (
    '3', '4', '41', '5', '6', '7', '8', '10', '11', '12',
    '101', '102', '103', '104', '105', '106', '111', '112',
)

# Публічний алиас для інших модулів (синхрон з логікою бейджа в топбарі).
NP_UNCOMPLETED_STATUS_CODES = _NP_UNCOMPLETED_CODES


def is_full_document_request(request) -> bool:
    """
    True лише для «справжньої» сторінки в браузері (повний HTML з header).
    HTMX/AJAX часткові відповіді та службові refresh-ендпоінти — False.
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return False

    htmx = getattr(request, 'htmx', None)
    if htmx:
        # hx-boost / відновлення з history — фактично повне завантаження документа
        if htmx.boosted or htmx.history_restore_request:
            return True
        return False

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return False

    return True


def topbar_cart_count_context(request):
    """Контекст для шаблонів бейджів (cartCountData)."""
    if not request.user.is_authenticated:
        return {'cartCountData': empty_topbar_cart_count_data()}
    return {'cartCountData': build_topbar_cart_count_data(request)}


def queryset_orders_with_uncompleted_np_tracking():
    """
    Унікальні замовлення, де є хоча б одна накладна НП з «незавершеним» status_code
    (той самий набір кодів, що й для лічильника orders_with_uncompleted_np).
    """
    order_ids = (
        StatusNPParselFromDoucmentID.objects.filter(
            status_code__in=_NP_UNCOMPLETED_CODES,
            for_order_id__isnull=False,
        )
        .values_list('for_order_id', flat=True)
        .distinct()
    )
    return Order.objects.filter(id__in=order_ids).order_by('-id')


def empty_topbar_cart_count_data():
    return {
        'cart_items': 0,
        'precart_items': 0,
        'orders_incomplete': 0,
        'preorders_incomplete': 0,
        'preorders_await': 0,
        'preorders_partial': 0,
        'order_to_send_today': 0,
        'expired_orders': 0,
        'is_one_cart': '',
        'booked_cart_first': None,
        'orders_pinned': 0,
        'preorders_pinned': 0,
        'orders_with_uncompleted_np': 0,
    }


def build_topbar_cart_count_data(request):
    """
    Compute counts for header badges. Cached on the request object to avoid
    duplicate work when templates or code call this more than once per request.
    """
    cached = getattr(request, '_topbar_cart_counts_cache', None)
    if cached is not None:
        return cached

    user = request.user
    app_settings = user.get_app_settings()
    is_client = user.isClient()
    is_one_cart = ''
    booked_cart_first = None

    if app_settings.enable_show_other_booked_cart:
        booked_carts = BookedOrderInCart.objects.all()
    else:
        booked_carts = BookedOrderInCart.objects.filter(place__user=user)

    carts_count = booked_carts.count()
    if carts_count == 1:
        is_one_cart = 'IS_ONE'
    elif carts_count > 1:
        is_one_cart = 'IS_MANY'
    booked_cart_first = booked_carts.first()

    if is_client:
        booked_carts = booked_carts.filter(place__user=user)
        carts_count = booked_carts.count()
        if carts_count == 1:
            is_one_cart = 'IS_ONE'
        elif carts_count > 1:
            is_one_cart = 'IS_MANY'
        else:
            is_one_cart = ''
        booked_cart_first = booked_carts.first()

    order_in_cart = active_order_in_cart(user)
    if order_in_cart is None:
        cart_items = 0
    else:
        cart_items = (
            order_in_cart.supplyinorderincart_set.aggregate(t=Sum('count_in_order'))['t'] or 0
        )

    precart_order = active_preorder_in_cart(user)
    if precart_order is None:
        precart_items = 0
    else:
        precart_items = (
            precart_order.supplyinpreorderincart_set.aggregate(t=Sum('count_in_order'))['t'] or 0
        )

    order_incomplete_qs = Order.objects.filter(isComplete=False)
    if is_client:
        order_incomplete_qs = order_incomplete_qs.filter(place__user=user)
    orders_incomplete = order_incomplete_qs.count()

    preorder_incomplete_qs = PreOrder.objects.filter(isComplete=False)
    if is_client:
        preorder_incomplete_qs = preorder_incomplete_qs.filter(place__user=user)
    preorders_incomplete = preorder_incomplete_qs.count()

    preorders_await = 0
    preorders_partial = 0
    order_to_send_today = 0
    expired_orders = 0
    orders_with_uncompleted_np = 0
    orders_pinned = 0
    preorders_pinned = 0

    if not is_client:
        today = date.today()
        agg = PreOrder.objects.aggregate(
            preorders_await=Count('id', filter=Q(state_of_delivery='Awaiting')),
            preorders_partial=Count('id', filter=Q(state_of_delivery='Partial')),
            preorders_pinned=Count('id', filter=Q(isPinned=True)),
        )
        preorders_await = agg['preorders_await'] or 0
        preorders_partial = agg['preorders_partial'] or 0
        preorders_pinned = agg['preorders_pinned'] or 0

        order_agg = Order.objects.aggregate(
            order_to_send_today=Count('id', filter=Q(dateToSend=today, isComplete=False)),
            expired_orders=Count('id', filter=Q(dateToSend__lt=today, isComplete=False)),
            orders_pinned=Count('id', filter=Q(isPinned=True)),
        )
        order_to_send_today = order_agg['order_to_send_today'] or 0
        expired_orders = order_agg['expired_orders'] or 0
        orders_pinned = order_agg['orders_pinned'] or 0

        orders_with_uncompleted_np = StatusNPParselFromDoucmentID.objects.filter(
            status_code__in=_NP_UNCOMPLETED_CODES
        ).count()

    result = {
        'cart_items': cart_items,
        'precart_items': precart_items,
        'orders_incomplete': orders_incomplete,
        'preorders_incomplete': preorders_incomplete,
        'preorders_await': preorders_await,
        'preorders_partial': preorders_partial,
        'order_to_send_today': order_to_send_today,
        'expired_orders': expired_orders,
        'is_one_cart': is_one_cart,
        'booked_cart_first': booked_cart_first,
        'orders_pinned': orders_pinned,
        'preorders_pinned': preorders_pinned,
        'orders_with_uncompleted_np': orders_with_uncompleted_np,
    }
    request._topbar_cart_counts_cache = result
    return result
