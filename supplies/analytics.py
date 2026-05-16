from datetime import datetime, timedelta
from django.db.models import Count, Avg, F, Q, Sum, Max, Min, Exists, OuterRef
from django.db.models.functions import TruncMonth, Coalesce
from django.utils import timezone
from .models import Place, PreOrder, SupplyInPreorder, GeneralSupply, SupplyInOrder, NPDeliveryCreatedDetailInfo, Supply, Order, Workers, Device

class PreorderAnalytics:
    def __init__(self, place):
        self.place = place
        self.preorders = PreOrder.objects.filter(place=place)
        
    def analyze_order_frequency(self):
        """Аналізує частоту замовлень для місця"""
        if not self.preorders.exists():
            return None
            
        # Отримуємо всі дати замовлень
        order_dates = self.preorders.values_list('dateCreated', flat=True)
        order_dates = sorted(order_dates)
        
        # Розраховуємо середній інтервал між замовленнями
        intervals = []
        for i in range(1, len(order_dates)):
            interval = (order_dates[i] - order_dates[i-1]).days
            intervals.append(interval)
            
        avg_interval = sum(intervals) / len(intervals) if intervals else None
        return avg_interval
        
    def analyze_product_patterns(self):
        """Аналізує патерни замовлень товарів"""
        if not self.preorders.exists():
            return []
            
        # Отримуємо всі товари з передзамовлень, групуємо по generalSupply
        supply_patterns = SupplyInPreorder.objects.filter(
            supply_for_order__in=self.preorders,
            generalSupply__isnull=False
        ).values(
            'generalSupply'
        ).annotate(
            total_orders=Count('id'),  # Кількість разів, коли товар був у замовленнях
            total_quantity=Sum('count_in_order'),  # Загальна кількість замовлених одиниць
            avg_quantity=Avg('count_in_order'),  # Середня кількість в одному замовленні
            max_quantity=Max('count_in_order'),  # Максимальна кількість в одному замовленні
            min_quantity=Min('count_in_order'),  # Мінімальна кількість в одному замовленні
            last_order_date=Max('supply_for_order__dateCreated'),
            first_order_date=Min('supply_for_order__dateCreated')
        )
        
        return list(supply_patterns)
        
    def predict_next_order_date(self):
        """Прогнозує дату наступного замовлення"""
        avg_interval = self.analyze_order_frequency()
        if not avg_interval:
            return None
            
        last_order = self.preorders.order_by('-dateCreated').first()
        if not last_order:
            return None
            
        predicted_date = last_order.dateCreated + timedelta(days=avg_interval)
        return predicted_date
        
    def calculate_product_score(self, pattern):
        """Розраховує оцінку для товару на основі загальної кількості та частоти замовлень"""
        if not pattern['total_orders']:
            return 0
            
        # Фактор 1: Загальна кількість замовлених одиниць (0-1)
        # Нормалізуємо відносно максимальної кількості
        max_quantity = SupplyInPreorder.objects.filter(
            supply_for_order__in=self.preorders,
            generalSupply__isnull=False
        ).values('generalSupply').annotate(
            total=Sum('count_in_order')
        ).aggregate(max_total=Max('total'))['max_total'] or 1
        
        quantity_score = min(pattern['total_quantity'] / max_quantity, 1.0)
        
        # Фактор 2: Частота замовлень (0-1)
        # Нормалізуємо відносно максимальної кількості замовлень
        max_orders = SupplyInPreorder.objects.filter(
            supply_for_order__in=self.preorders,
            generalSupply__isnull=False
        ).values('generalSupply').annotate(
            count=Count('id')
        ).aggregate(max_count=Max('count'))['max_count'] or 1
        
        frequency_score = min(pattern['total_orders'] / max_orders, 1.0)
        
        # Фактор 3: Стабільність кількості (0-1)
        # Розраховуємо на основі відношення середньої кількості до загальної
        if pattern['total_quantity'] > 0:
            stability_score = min(pattern['avg_quantity'] / (pattern['total_quantity'] / pattern['total_orders']), 1.0)
        else:
            stability_score = 0
            
        # Фактор 4: Час з останнього замовлення (0-1)
        days_since_last = (timezone.now().date() - pattern['last_order_date']).days
        recency_score = max(0, 1 - (days_since_last / 365))  # Зменшується протягом року
        
        # Комбінуємо фактори
        weights = {
            'quantity': 0.4,    # Вага загальної кількості
            'frequency': 0.3,   # Вага частоти замовлень
            'stability': 0.2,   # Вага стабільності
            'recency': 0.1      # Вага актуальності
        }
        
        total_score = (
            quantity_score * weights['quantity'] +
            frequency_score * weights['frequency'] +
            stability_score * weights['stability'] +
            recency_score * weights['recency']
        )
        
        return total_score
        
    def calculate_suggested_quantity(self, pattern):
        """Розраховує рекомендовану кількість для товару"""
        if pattern['total_orders'] < 2:
            return pattern['avg_quantity']
            
        # Отримуємо останні 3 замовлення
        recent_orders = SupplyInPreorder.objects.filter(
            supply_for_order__in=self.preorders,
            generalSupply_id=pattern['generalSupply']
        ).order_by('-supply_for_order__dateCreated')[:3]
        
        if recent_orders.exists():
            # Розраховуємо середню кількість з останніх замовлень
            recent_avg = recent_orders.aggregate(avg=Avg('count_in_order'))['avg']
            
            # Використовуємо 70% від середньої кількості останніх замовлень
            # та 30% від загальної середньої
            suggested = (recent_avg * 0.7) + (pattern['avg_quantity'] * 0.3)
        else:
            # Якщо немає останніх замовлень, використовуємо загальну середню
            suggested = pattern['avg_quantity']
            
        # Округляємо до цілого числа
        suggested = round(suggested)
        
        # Перевіряємо, чи не перевищує максимальну кількість
        if suggested > pattern['max_quantity']:
            suggested = pattern['max_quantity']
            
        # Перевіряємо, чи не менша за мінімальну кількість
        if suggested < pattern['min_quantity']:
            suggested = pattern['min_quantity']
            
        return suggested
        
    def generate_suggestions(self):
        """Генерує пропозиції для наступного передзамовлення"""
        suggestions = []
        
        # Отримуємо патерни замовлень
        patterns = self.analyze_product_patterns()
        
        # Аналізуємо кожен товар
        for pattern in patterns:
            try:
                general_supply = GeneralSupply.objects.get(id=pattern['generalSupply'])
                
                # Розраховуємо оцінку товару
                score = self.calculate_product_score(pattern)
                
                # Додаємо до пропозицій, якщо оцінка достатньо висока
                if score > 0.2:  # Зменшуємо поріг для включення більшої кількості товарів
                    suggested_quantity = self.calculate_suggested_quantity(pattern)
                    
                    suggestion = {
                        'product': general_supply,
                        'suggested_quantity': suggested_quantity,
                        'confidence': score,
                        'total_orders': pattern['total_orders'],
                        'total_quantity': pattern['total_quantity'],
                        'avg_quantity': pattern['avg_quantity'],
                        'max_quantity': pattern['max_quantity'],
                        'min_quantity': pattern['min_quantity'],
                        'last_order_date': pattern['last_order_date']
                    }
                    suggestions.append(suggestion)
                    
            except GeneralSupply.DoesNotExist:
                continue
                
        # Сортуємо пропозиції за впевненістю
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)

        
        return suggestions
        
    def get_analytics_report(self):
        """Генерує повний звіт аналітики"""
        return {
            'place': self.place,
            'order_frequency': self.analyze_order_frequency(),
            'next_predicted_order': self.predict_next_order_date(),
            'suggestions': self.generate_suggestions(),
            'total_orders': self.preorders.count(),
            'last_order_date': self.preorders.order_by('-dateCreated').first().dateCreated if self.preorders.exists() else None
        }


def build_orders_analytics(order_qs, *, include_top_places=True, for_user=None):
    """
    Знімок для дашборду замовлень (графіки Chart.js).
    order_qs — вже відфільтрований набір (наприклад orderFilter.qs).
    for_user — поточний користувач для метрик «створено / відправлено мною».
    """
    empty = {
        'total': 0,
        'completed': 0,
        'pending': 0,
        'merged': 0,
        'with_preorders': 0,
        'created_by_me': 0,
        'sent_by_me': 0,
        'with_documents_id': 0,
        'avg_line_positions': 0.0,
        'top_places': {'labels': [], 'counts': []},
        'top_products': {'labels': [], 'quantities': [], 'categories': []},
        'monthly': {'labels': [], 'counts': []},
        'meta': {'show_top_places': include_top_places},
    }
    total = order_qs.count()
    if total == 0:
        return empty

    agg = order_qs.aggregate(
        completed=Count('id', filter=Q(isComplete=True)),
        pending=Count('id', filter=Q(isComplete=False)),
        merged=Count('id', filter=Q(isMerged=True)),
    )
    completed = agg['completed'] or 0
    pending = agg['pending'] or 0
    merged = agg['merged'] or 0
    line_rows = SupplyInOrder.objects.filter(supply_for_order__in=order_qs).count()
    avg_line_positions = round(line_rows / total, 2) if total else 0.0
    with_preorders = order_qs.filter(
        Q(for_preorder__isnull=False) | Q(related_preorders__isnull=False)
    ).distinct().count()
    has_np_invoice = Exists(
        NPDeliveryCreatedDetailInfo.objects.filter(for_order_id=OuterRef('pk'))
    )
    has_documents_array = Q(documentsId__isnull=False) & ~Q(documentsId=[])
    with_documents_id = order_qs.filter(has_documents_array | has_np_invoice).distinct().count()

    uid = getattr(for_user, 'pk', None)
    if getattr(for_user, 'is_authenticated', False) and uid is not None:
        i_created_np = Exists(
            NPDeliveryCreatedDetailInfo.objects.filter(
                for_order_id=OuterRef('pk'),
                userCreated_id=uid,
            )
        )
        created_by_me = order_qs.filter(Q(userCreated_id=uid) | i_created_np).distinct().count()
        sent_by_me = order_qs.filter(userSent_id=uid).count()
    else:
        created_by_me = 0
        sent_by_me = 0

    top_places = {'labels': [], 'counts': []}
    if include_top_places:
        rows = (
            order_qs.values('place__name', 'place__city_ref__name')
            .annotate(c=Count('id'))
            .order_by('-c')[:50]
        )
        for r in rows:
            name = (r.get('place__name') or '').strip() or '—'
            city = (r.get('place__city_ref__name') or '').strip()
            label = f'{name}' if not city else f'{name}, {city}'
            top_places['labels'].append(label[:80])
            top_places['counts'].append(r['c'])

    month_rows = list(
        order_qs.annotate(period=TruncMonth(Coalesce('dateSent', 'dateCreated')))
        .exclude(period__isnull=True)
        .values('period')
        .annotate(c=Count('id'))
        .order_by('period')
    )
    monthly = {'labels': [], 'counts': []}
    for r in month_rows:
        p = r['period']
        if p:
            monthly['labels'].append(p.strftime('%m.%Y'))
            monthly['counts'].append(r['c'])

    top_products = {'labels': [], 'quantities': [], 'categories': []}
    for r in (
        SupplyInOrder.objects.filter(
            supply_for_order__in=order_qs,
            generalSupply__isnull=False,
        )
        .values('generalSupply__name', 'generalSupply__category__name')
        .annotate(total_qty=Sum('count_in_order'))
        .order_by('-total_qty')[:50]
    ):
        lab = (r.get('generalSupply__name') or '').strip() or '—'
        cat = (r.get('generalSupply__category__name') or '').strip() or '—'
        top_products['labels'].append(lab[:95])
        top_products['quantities'].append(int(r['total_qty'] or 0))
        top_products['categories'].append(cat[:80])

    return {
        'total': total,
        'completed': completed,
        'pending': pending,
        'merged': merged,
        'with_preorders': with_preorders,
        'created_by_me': created_by_me,
        'sent_by_me': sent_by_me,
        'with_documents_id': with_documents_id,
        'avg_line_positions': avg_line_positions,
        'top_places': top_places,
        'top_products': top_products,
        'monthly': monthly,
        'meta': {'show_top_places': include_top_places},
    }


_PREORDER_STATUS_CHART_STYLE = {
    # Узгоджено з `partials/preorders/preorder_preview_cell.html` (badge + bi-іконки).
    'awaiting_from_customer': ('#0dcaf0', 'bi-pencil-square'),
    'accepted_by_customer': ('#0d6efd', 'bi-check2-all'),
    'Awaiting': ('#ffc107', 'bi-truck'),
    'Partial': ('#fd7e14', 'bi-hourglass-split'),
    'Complete': ('#198754', 'bi-check-circle'),
    'Complete_Handle': ('#146c43', 'bi-check-circle'),
}


def _build_preorder_status_breakdown(preorder_qs):
    rows = list(preorder_qs.values('state_of_delivery').annotate(c=Count('id')))
    raw = {r['state_of_delivery']: r['c'] for r in rows}
    label_by_key = dict(PreOrder.STATE_CHOICES)
    known = [k for k, _ in PreOrder.STATE_CHOICES]

    items = []
    for key in known:
        lab = label_by_key.get(key, key or '—')
        color, icon = _PREORDER_STATUS_CHART_STYLE.get(key, ('#6c757d', 'bi-question-circle'))
        items.append({
            'key': key,
            'label': lab,
            'count': int(raw.get(key) or 0),
            'color': color,
            'icon': icon,
        })

    seen = set(known)
    orphan_keys = sorted(k for k in raw.keys() if k not in seen and k is not None)
    if None in raw and None not in seen:
        orphan_keys = [None] + orphan_keys
    for key in orphan_keys:
        color, icon = _PREORDER_STATUS_CHART_STYLE.get(key, ('#6c757d', 'bi-question-circle'))
        lab = label_by_key.get(key, '—' if key is None else str(key))
        items.append({
            'key': key,
            'label': lab,
            'count': int(raw.get(key) or 0),
            'color': color,
            'icon': icon,
        })
    return items


def build_preorders_analytics(preorder_qs, *, include_top_places=True, for_user=None):
    """
    Дашборд передзамовлень (Chart.js) — та сама ідея, що build_orders_analytics.
    preorder_qs — відфільтрований набір (наприклад preorderFilter.qs).
    """
    empty = {
        'total': 0,
        'completed': 0,
        'pending': 0,
        'pinned': 0,
        'with_orders': 0,
        'created_by_clients': 0,
        'unique_client_creators': 0,
        'created_by_me': 0,
        'date_sent_by_me': 0,
        'with_date_sent': 0,
        'avg_line_positions': 0.0,
        'not_archived': 0,
        'in_archive': 0,
        'top_places': {'labels': [], 'counts': []},
        'top_products': {'labels': [], 'quantities': [], 'categories': []},
        'monthly': {'labels': [], 'counts': []},
        'status_breakdown': [],
        'meta': {'show_top_places': include_top_places, 'dashboard': 'preorders'},
    }
    total = preorder_qs.count()
    if total == 0:
        return empty

    state_done = ('Complete', 'Complete_Handle')
    agg = preorder_qs.aggregate(
        completed=Count('id', filter=Q(state_of_delivery__in=state_done)),
        pending=Count('id', filter=~Q(state_of_delivery__in=state_done)),
        pinned=Count('id', filter=Q(isPinned=True)),
        with_date_sent=Count('id', filter=Q(dateSent__isnull=False)),
        in_archive=Count('id', filter=Q(isClosed=True)),
        not_archived=Count('id', filter=Q(isClosed=False)),
    )
    completed = agg['completed'] or 0
    pending = agg['pending'] or 0
    pinned = agg['pinned'] or 0
    with_date_sent = agg['with_date_sent'] or 0
    in_archive = agg['in_archive'] or 0
    not_archived = agg['not_archived'] or 0

    created_by_clients = preorder_qs.filter(userCreated__groups__name='client').distinct().count()
    unique_client_creators = (
        preorder_qs.filter(userCreated__isnull=False, userCreated__groups__name='client')
        .values('userCreated_id')
        .distinct()
        .count()
    )

    line_rows = SupplyInPreorder.objects.filter(supply_for_order__in=preorder_qs).count()
    avg_line_positions = round(line_rows / total, 2) if total else 0.0

    with_orders = preorder_qs.filter(
        Q(orders_for_preorder__isnull=False) | Q(related_orders__isnull=False)
    ).distinct().count()

    uid = getattr(for_user, 'pk', None)
    if getattr(for_user, 'is_authenticated', False) and uid is not None:
        created_by_me = preorder_qs.filter(userCreated_id=uid).count()
        date_sent_by_me = preorder_qs.filter(
            userCreated_id=uid, dateSent__isnull=False
        ).count()
    else:
        created_by_me = 0
        date_sent_by_me = 0

    top_places = {'labels': [], 'counts': []}
    if include_top_places:
        rows = (
            preorder_qs.values('place__name', 'place__city_ref__name')
            .annotate(c=Count('id'))
            .order_by('-c')[:50]
        )
        for r in rows:
            name = (r.get('place__name') or '').strip() or '—'
            city = (r.get('place__city_ref__name') or '').strip()
            label = f'{name}' if not city else f'{name}, {city}'
            top_places['labels'].append(label[:80])
            top_places['counts'].append(r['c'])

    month_rows = list(
        preorder_qs.annotate(period=TruncMonth(Coalesce('dateSent', 'dateCreated')))
        .exclude(period__isnull=True)
        .values('period')
        .annotate(c=Count('id'))
        .order_by('period')
    )
    monthly = {'labels': [], 'counts': []}
    for r in month_rows:
        p = r['period']
        if p:
            monthly['labels'].append(p.strftime('%m.%Y'))
            monthly['counts'].append(r['c'])

    top_products = {'labels': [], 'quantities': [], 'categories': []}
    for r in (
        SupplyInPreorder.objects.filter(
            supply_for_order__in=preorder_qs,
            generalSupply__isnull=False,
        )
        .values('generalSupply__name', 'generalSupply__category__name')
        .annotate(total_qty=Sum('count_in_order'))
        .order_by('-total_qty')[:50]
    ):
        lab = (r.get('generalSupply__name') or '').strip() or '—'
        cat = (r.get('generalSupply__category__name') or '').strip() or '—'
        top_products['labels'].append(lab[:95])
        top_products['quantities'].append(int(r['total_qty'] or 0))
        top_products['categories'].append(cat[:80])

    status_breakdown = _build_preorder_status_breakdown(preorder_qs)

    return {
        'total': total,
        'completed': completed,
        'pending': pending,
        'pinned': pinned,
        'with_orders': with_orders,
        'created_by_clients': created_by_clients,
        'unique_client_creators': unique_client_creators,
        'created_by_me': created_by_me,
        'date_sent_by_me': date_sent_by_me,
        'with_date_sent': with_date_sent,
        'not_archived': not_archived,
        'in_archive': in_archive,
        'avg_line_positions': avg_line_positions,
        'top_places': top_places,
        'top_products': top_products,
        'monthly': monthly,
        'status_breakdown': status_breakdown,
        'meta': {'show_top_places': include_top_places, 'dashboard': 'preorders'},
    }


def build_supply_statistics(user):
    """
    Агрегована статистика по номенклатурі, партіях, замовленнях — для сторінки «Статистика товарів».
    Для клієнтів — лише дозволені категорії та їхні замовлення.
    """
    today = timezone.now().date()
    is_client = bool(user.isClient() and not user.is_staff)

    if is_client:
        allowed = set()
        for plc in user.place_set.all():
            allowed.update(plc.allowed_categories.values_list('id', flat=True))
        if not allowed:
            gen_qs = GeneralSupply.objects.none()
        else:
            gen_qs = GeneralSupply.objects.filter(category_id__in=allowed)
        sup_qs = Supply.objects.filter(general_supply__in=gen_qs) if gen_qs.exists() else Supply.objects.none()
        order_qs = Order.objects.filter(place__user=user)
        preorder_qs = PreOrder.objects.filter(place__user=user)
    else:
        gen_qs = GeneralSupply.objects.all()
        sup_qs = Supply.objects.all()
        order_qs = Order.objects.all()
        preorder_qs = PreOrder.objects.all()

    nomen_count = gen_qs.count()
    lots_count = sup_qs.count()
    agg_sup = sup_qs.aggregate(
        u=Sum('count'),
        h=Sum('countOnHold'),
    )
    total_units = int(agg_sup['u'] or 0)
    total_on_hold = int(agg_sup['h'] or 0)

    expired_lots = sup_qs.filter(expiredDate__lt=today).count()
    good_dated = sup_qs.filter(expiredDate__gte=today).count()

    categories_nom = {'labels': [], 'counts': []}
    for r in (
        gen_qs.values('category__name')
        .annotate(c=Count('id'))
        .order_by('-c')
    ):
        lab = (r.get('category__name') or '').strip() or '—'
        categories_nom['labels'].append(lab[:80])
        categories_nom['counts'].append(r['c'])

    categories_stock = {'labels': [], 'units': []}
    for r in (
        sup_qs.values('general_supply__category__name')
        .annotate(s=Sum('count'))
        .order_by('-s')
    ):
        lab = (r.get('general_supply__category__name') or '').strip() or '—'
        categories_stock['labels'].append(lab[:80])
        categories_stock['units'].append(int(r['s'] or 0))

    top_stock = {'labels': [], 'units': []}
    for r in (
        sup_qs.values('general_supply__name')
        .annotate(total=Sum('count'))
        .order_by('-total')[:50]
    ):
        lab = (r.get('general_supply__name') or '').strip() or '—'
        top_stock['labels'].append(lab[:95])
        top_stock['units'].append(int(r['total'] or 0))

    top_orders = {'labels': [], 'quantities': []}
    sio_base = SupplyInOrder.objects.filter(
        supply_for_order__in=order_qs, generalSupply__isnull=False
    )
    if is_client and gen_qs.exists():
        sio_base = sio_base.filter(generalSupply__in=gen_qs)
    for r in (
        sio_base.values('generalSupply__name')
        .annotate(total_qty=Sum('count_in_order'))
        .order_by('-total_qty')[:50]
    ):
        lab = (r.get('generalSupply__name') or '').strip() or '—'
        top_orders['labels'].append(lab[:95])
        top_orders['quantities'].append(int(r['total_qty'] or 0))

    top_preorders = {'labels': [], 'quantities': []}
    sip_base = SupplyInPreorder.objects.filter(
        supply_for_order__in=preorder_qs, generalSupply__isnull=False
    )
    if is_client and gen_qs.exists():
        sip_base = sip_base.filter(generalSupply__in=gen_qs)
    for r in (
        sip_base.values('generalSupply__name')
        .annotate(total_qty=Sum('count_in_order'))
        .order_by('-total_qty')[:50]
    ):
        lab = (r.get('generalSupply__name') or '').strip() or '—'
        top_preorders['labels'].append(lab[:95])
        top_preorders['quantities'].append(int(r['total_qty'] or 0))

    lot_month_rows = list(
        sup_qs.annotate(m=TruncMonth('dateCreated'))
        .exclude(m__isnull=True)
        .values('m')
        .annotate(c=Count('id'))
        .order_by('m')
    )
    lots_monthly = {'labels': [], 'counts': []}
    for r in lot_month_rows:
        m = r['m']
        if m:
            lots_monthly['labels'].append(m.strftime('%m.%Y'))
            lots_monthly['counts'].append(r['c'])

    ship_rows = list(
        sio_base.annotate(
            sm=TruncMonth(Coalesce('supply_for_order__dateSent', 'supply_for_order__dateCreated'))
        )
        .exclude(sm__isnull=True)
        .values('sm')
        .annotate(total=Sum('count_in_order'))
        .order_by('sm')
    )
    shipped_monthly = {'labels': [], 'units': []}
    for r in ship_rows:
        m = r['sm']
        if m:
            shipped_monthly['labels'].append(m.strftime('%m.%Y'))
            shipped_monthly['units'].append(int(r['total'] or 0))

    return {
        'summary': {
            'nomenclature': nomen_count,
            'lots': lots_count,
            'total_units': total_units,
            'total_on_hold': total_on_hold,
            'expired_lots': expired_lots,
            'good_dated_lots': good_dated,
            'orders_in_scope': order_qs.count(),
        },
        'top_stock': top_stock,
        'top_orders': top_orders,
        'top_preorders': top_preorders,
        'categories_nomenclature': categories_nom,
        'categories_stock': categories_stock,
        'lots_monthly': lots_monthly,
        'shipped_monthly': shipped_monthly,
        'expiry': {
            'labels': ['Прострочено', 'Придатні'],
            'counts': [expired_lots, good_dated],
        },
        'meta': {'is_client_scope': is_client},
    }


def build_clients_info_analytics(place_qs):
    """
    Аналітика списку організацій (Place) на /clientsInfo.
    place_qs — повна вибірка після PlaceFilter, без пагінації.
    """
    empty = {
        'total': 0,
        'private_places': 0,
        'public_places': 0,
        'with_login_users': 0,
        'without_login_users': 0,
        'in_np': 0,
        'related_orders': 0,
        'related_preorders': 0,
        'related_workers': 0,
        'related_devices': 0,
        'top_cities': {'labels': [], 'counts': []},
        'meta': {},
    }
    total = place_qs.count()
    if not total:
        return empty

    agg = place_qs.aggregate(
        private_places=Count('id', filter=Q(isPrivatePlace=True)),
        public_places=Count('id', filter=Q(isPrivatePlace=False)),
        in_np=Count('id', filter=Q(isAddedToNP=True)),
    )
    private_places = int(agg['private_places'] or 0)
    public_places = int(agg['public_places'] or 0)
    in_np = int(agg['in_np'] or 0)

    with_login_users = place_qs.annotate(nu=Count('user', distinct=True)).filter(nu__gt=0).count()
    without_login_users = total - with_login_users

    related_orders = Order.objects.filter(place__in=place_qs).count()
    related_preorders = PreOrder.objects.filter(place__in=place_qs).count()
    related_workers = Workers.objects.filter(for_place__in=place_qs).count()
    related_devices = Device.objects.filter(in_place__in=place_qs).count()

    top_cities = {'labels': [], 'counts': []}
    for r in (
        place_qs.values('city_ref__name')
        .annotate(c=Count('id'))
        .order_by('-c')[:20]
    ):
        lab = (r.get('city_ref__name') or '').strip() or '—'
        top_cities['labels'].append(lab[:80])
        top_cities['counts'].append(r['c'])

    return {
        'total': total,
        'private_places': private_places,
        'public_places': public_places,
        'with_login_users': with_login_users,
        'without_login_users': without_login_users,
        'in_np': in_np,
        'related_orders': related_orders,
        'related_preorders': related_preorders,
        'related_workers': related_workers,
        'related_devices': related_devices,
        'top_cities': top_cities,
        'type_chart': {
            'labels': ['Приватні', 'Державні / інші'],
            'counts': [private_places, public_places],
            'colors': ['#0d6efd', '#6c757d'],
        },
        'meta': {},
    }


def build_booked_supplies_analytics(booked_qs):
    """
    Агрегати для списку заброньованих позицій (SupplyInBookedOrder) після BookedSuppliesFilter.
    """
    empty = {
        'total_lines': 0,
        'distinct_products': 0,
        'total_units': 0,
        'total_on_hold': 0,
        'categories': {'labels': [], 'units': []},
        'top_products': {'labels': [], 'units': []},
        'expiry': {'labels': ['Прострочено', 'Придатні / без дати'], 'counts': [0, 0]},
        'meta': {},
    }
    total_lines = booked_qs.count()
    if not total_lines:
        return empty

    today = timezone.now().date()
    agg = booked_qs.aggregate(
        total_units=Sum(Coalesce('count_in_order', 0)),
        total_on_hold=Sum(Coalesce('countOnHold', 0)),
        distinct_products=Count('generalSupply', distinct=True),
    )
    total_units = int(agg['total_units'] or 0)
    total_on_hold = int(agg['total_on_hold'] or 0)
    distinct_products = int(agg['distinct_products'] or 0)

    expired = booked_qs.filter(date_expired__lt=today).count()
    good_or_nodate = booked_qs.filter(
        Q(date_expired__gte=today) | Q(date_expired__isnull=True)
    ).count()

    categories = {'labels': [], 'units': []}
    for r in (
        booked_qs.values('generalSupply__category__name')
        .annotate(s=Sum(Coalesce('count_in_order', 0)))
        .order_by('-s')[:20]
    ):
        lab = (r.get('generalSupply__category__name') or '').strip() or '—'
        categories['labels'].append(lab[:80])
        categories['units'].append(int(r['s'] or 0))

    top_products = {'labels': [], 'units': []}
    for r in (
        booked_qs.values('generalSupply__name')
        .annotate(s=Sum(Coalesce('count_in_order', 0)))
        .order_by('-s')[:25]
    ):
        lab = (r.get('generalSupply__name') or '').strip() or '—'
        top_products['labels'].append(lab[:95])
        top_products['units'].append(int(r['s'] or 0))

    return {
        'total_lines': total_lines,
        'distinct_products': distinct_products,
        'total_units': total_units,
        'total_on_hold': total_on_hold,
        'categories': categories,
        'top_products': top_products,
        'expiry': {
            'labels': ['Прострочено', 'Придатні / без дати'],
            'counts': [expired, good_or_nodate],
        },
        'meta': {},
    }