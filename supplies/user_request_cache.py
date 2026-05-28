"""Per-request caches on the user instance (cart rows, group names)."""

from __future__ import annotations

from .models import OrderInCart, PreorderInCart, SupplyInOrderInCart, SupplyInPreorderInCart

_GROUP_NAMES_ATTR = '_dmdx_group_names_frozen'


def ensure_user_group_names(user) -> frozenset:
    if not getattr(user, 'is_authenticated', False):
        return frozenset()
    if not hasattr(user, _GROUP_NAMES_ATTR):
        cache = getattr(user, '_prefetched_objects_cache', None)
        if cache is not None and 'groups' in cache:
            names = frozenset(g.name for g in cache['groups'])
        else:
            names = frozenset(user.groups.values_list('name', flat=True))
        setattr(user, _GROUP_NAMES_ATTR, names)
    return getattr(user, _GROUP_NAMES_ATTR)


def active_order_in_cart(user):
    """Incomplete OrderInCart for this user (same lookup as add-to-cart on home)."""
    if not getattr(user, 'is_authenticated', False):
        return None
    cache_attr = '_dmdx_active_order_in_cart'
    if hasattr(user, cache_attr):
        return getattr(user, cache_attr)
    cart = OrderInCart.objects.filter(userCreated=user, isComplete=False).order_by('id').first()
    setattr(user, cache_attr, cart)
    return cart


def _precart_cache_key(place_id) -> str:
    return '_dmdx_active_preorder_%s' % ('none' if place_id is None else str(place_id))


def active_preorder_in_cart(user, place_id=None):
    if not getattr(user, 'is_authenticated', False):
        return None
    cache_attr = _precart_cache_key(place_id)
    if hasattr(user, cache_attr):
        return getattr(user, cache_attr)
    qs = PreorderInCart.objects.filter(userCreated=user, isComplete=False)
    if place_id is not None:
        qs = qs.filter(place_id=place_id)
    cart = qs.order_by('id').first()
    setattr(user, cache_attr, cart)
    return cart


def _precart_maps_cache_key(place_id) -> str:
    return '_dmdx_precart_maps_%s' % ('none' if place_id is None else str(place_id))


def precart_row_maps(user, place_id=None):
    """
    Cached maps for template tags: supply ids in precart and general_supply_id -> count.
    Built from a single PreorderInCart + one items query.
    """
    if not getattr(user, 'is_authenticated', False):
        return frozenset(), {}
    cache_attr = _precart_maps_cache_key(place_id)
    if hasattr(user, cache_attr):
        return getattr(user, cache_attr)

    preorder = active_preorder_in_cart(user, place_id=place_id)
    if preorder is None:
        result = (frozenset(), {})
    else:
        supply_ids = set()
        general_counts = {}
        rows = SupplyInPreorderInCart.objects.filter(supply_for_order=preorder).values_list(
            'supply_id', 'general_supply_id', 'count_in_order',
        )
        for supply_id, general_id, count in rows:
            if supply_id is not None:
                supply_ids.add(int(supply_id))
            if general_id is not None:
                general_counts[int(general_id)] = count
        result = (frozenset(supply_ids), general_counts)

    setattr(user, cache_attr, result)
    return result


def order_in_cart_supply_counts(user) -> dict:
    """supply_id -> count_in_order for the active order cart."""
    if not getattr(user, 'is_authenticated', False):
        return {}
    cache_attr = '_dmdx_cart_supply_count_map'
    if hasattr(user, cache_attr):
        return getattr(user, cache_attr)

    order = active_order_in_cart(user)
    if order is None:
        mapping = {}
    else:
        rows = SupplyInOrderInCart.objects.filter(supply_for_order=order).exclude(
            supply__isnull=True,
        ).values_list('supply_id', 'count_in_order')
        mapping = {int(sid): int(cnt or 0) for sid, cnt in rows if sid is not None}

    setattr(user, cache_attr, mapping)
    return mapping
