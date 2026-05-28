from .topbar_cart_counts import (
    empty_topbar_cart_count_data,
    is_full_document_request,
    topbar_cart_count_context,
)


def cart_count_data(request):
    """
    cartCountData для header (бейджі замовлень/передзамовлень, попередження staff).
    Рахуємо лише на повному завантаженні сторінки — не на HTMX/AJAX фрагментах.
    Оновлення cart/precart/booked бейджів — через окремі hx-get ендпоінти з явним контекстом.
    """
    if not is_full_document_request(request):
        return {'cartCountData': empty_topbar_cart_count_data()}
    return topbar_cart_count_context(request)
