from datetime import datetime, timedelta
from django.db.models import Count, Avg, F, Q, Sum, Max, Min
from django.utils import timezone
from .models import Place, PreOrder, SupplyInPreorder, GeneralSupply

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