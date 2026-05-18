from .topbar_cart_counts import build_topbar_cart_count_data, empty_topbar_cart_count_data


def cart_count_data(request):
    """Inject cartCountData for all templates (top bar, cart badges)."""
    if not request.user.is_authenticated:
        return {'cartCountData': empty_topbar_cart_count_data()}
    return {'cartCountData': build_topbar_cart_count_data(request)}
