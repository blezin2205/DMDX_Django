from .serializers import *

from rest_framework import renderers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Sum, Min, Prefetch, Value, IntegerField, F, Case, When, Exists, OuterRef
from django.db.models.functions import Coalesce
from django.http import Http404, QueryDict
from .forms import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.db import transaction
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from .backends import JWTAuthentication
from .NPViews import (
    get_np_delivery_details,
    get_order_status,
    get_parsels_status_data,
    refresh_np_tracking_for_orders_batch,
    threading_create_np_document_async,
)
from .topbar_cart_counts import queryset_orders_with_uncompleted_np_tracking
from .views import update_order_status_core, _orders_list_queryset, _orders_default_ordering, _place_list_for_client_cards
from .filters import PlaceFilter
from .query_utils import devices_list_queryset, servicenotes_list_queryset
from .tasks import makeDataUpload_nonCelery
from math import ceil
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

from .dmdx_telegram_bot import process_telegram_webhook
from .excel_sheets.excel_views import _group_order_supplies_for_display
from .models import RegisterNPInfo
from .view_upload import _delivery_cart_line_queryset, _group_delivery_supplies_for_display
from .tasks import merge_identifiers_for_delivery_line, scan_expiry_for_delivery_line


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


class GeneralSuppliesApiView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        supplies = GeneralSupply.objects.select_related('category').prefetch_related(
            Prefetch(
                'general',
                queryset=Supply.objects.select_related('category', 'general_supply'),
            )
        ).all()
        paginator = self.pagination_class()
        paginated_supplies = paginator.paginate_queryset(supplies, request)
        if paginated_supplies is None:
            return Response({'error': 'Invalid page'}, status=status.HTTP_404_NOT_FOUND)
        suppliesSerializer = GeneralSupplySerializer(instance=paginated_supplies, many=True)
        return paginator.get_paginated_response(suppliesSerializer.data)


class SuppliesApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supplies = Supply.objects.select_related('category', 'general_supply').all()
        suppliesSerializer = SupplySerializer(instance=supplies, many=True)
        return Response(suppliesSerializer.data)

    def post(self, request):
        serializer = SupplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DesktopSuppliesApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        queryset = GeneralSupply.objects.select_related('category').all()

        is_client = (
            hasattr(request.user, 'isClient')
            and callable(request.user.isClient)
            and request.user.isClient()
            and not request.user.is_staff
        )
        if is_client:
            user_places = request.user.place_set.all()
            allowed_category_ids = set()
            for place in user_places:
                for category_id in place.allowed_categories.values_list('id', flat=True):
                    allowed_category_ids.add(category_id)
            queryset = queryset.filter(category_id__in=allowed_category_ids)

        query = (request.query_params.get('q') or '').strip()
        if query:
            query_filter = (
                Q(name__icontains=query)
                | Q(ref__icontains=query)
                | Q(SMN_code__icontains=query)
                | Q(general__supplyLot__icontains=query)
            )
            queryset = queryset.filter(query_filter)

        category = (request.query_params.get('category') or '').strip()
        if category and category != 'all':
            queryset = queryset.filter(category__name=category)

        availability = (request.query_params.get('availability') or 'all').strip()
        if availability == 'with_children':
            queryset = queryset.filter(general__isnull=False)
        elif availability == 'without_children':
            queryset = queryset.filter(general__isnull=True)

        expired_only = _as_bool(request.query_params.get('expired_only'))
        valid_only = _as_bool(request.query_params.get('valid_only'))
        today = timezone.now().date()
        if valid_only:
            valid_lots = Supply.objects.filter(
                general_supply_id=OuterRef('pk'),
                expiredDate__gte=today,
            )
            queryset = queryset.filter(Exists(valid_lots))
        elif expired_only:
            queryset = queryset.filter(general__expiredDate__lt=today)

        queryset = queryset.annotate(
            child_count=Count('general', distinct=True),
            total_count=Coalesce(Sum('general__count'), Value(0), output_field=IntegerField()),
            total_on_hold=Coalesce(Sum('general__countOnHold'), Value(0), output_field=IntegerField()),
            nearest_expiry=Min('general__expiredDate'),
        ).distinct()

        sort = (request.query_params.get('sort') or 'name_asc').strip()
        if sort == 'name_desc':
            queryset = queryset.order_by('-name', '-id')
        elif sort == 'count_desc':
            queryset = queryset.order_by('-total_count', 'name', 'id')
        elif sort == 'count_asc':
            queryset = queryset.order_by('total_count', 'name', 'id')
        elif sort == 'expiry_asc':
            queryset = queryset.order_by(F('nearest_expiry').asc(nulls_last=True), 'name', 'id')
        elif sort == 'expiry_desc':
            queryset = queryset.order_by(F('nearest_expiry').desc(nulls_last=True), 'name', 'id')
        else:
            queryset = queryset.order_by('name', 'id')

        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (TypeError, ValueError):
            page_size = 20
        page_size = max(1, min(page_size, 200))

        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        total_count = queryset.count()
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        lots_qs = Supply.objects.select_related('general_supply').order_by('expiredDate', 'id')
        if valid_only:
            lots_qs = lots_qs.filter(expiredDate__gte=today)
        elif expired_only:
            lots_qs = lots_qs.filter(expiredDate__lt=today)
        page_queryset = queryset[start:end].prefetch_related(
            Prefetch('general', queryset=lots_qs)
        )

        results = []
        for item in page_queryset:
            lots_payload = []
            lots = list(item.general.all())
            for lot in lots:
                lots_payload.append(
                    {
                        'id': lot.id,
                        'general_supply_id': item.id,
                        'name': item.name,
                        'package_and_tests': item.package_and_tests,
                        'category': item.category.name if item.category else None,
                        'ref': item.ref,
                        'smn_code': item.SMN_code,
                        'supplyLot': lot.supplyLot,
                        'count': lot.count,
                        'countOnHold': lot.countOnHold,
                        'expiredDate': lot.expiredDate.strftime('%d-%m-%Y') if lot.expiredDate else None,
                        'dateCreated': lot.dateCreated.strftime('%d-%m-%Y') if lot.dateCreated else None,
                    }
                )

            nearest_expiry = item.nearest_expiry.strftime('%d-%m-%Y') if item.nearest_expiry else None
            results.append(
                {
                    'id': item.id,
                    'key': f'g-{item.id}',
                    'name': item.name or '-',
                    'packageAndTests': item.package_and_tests or '-',
                    'category': item.category.name if item.category else '-',
                    'ref': item.ref or '-',
                    'smn': item.SMN_code or '-',
                    'lots': lots_payload,
                    'totalCount': item.total_count or 0,
                    'totalOnHold': item.total_on_hold or 0,
                    'nearestExpiry': nearest_expiry,
                }
            )

        category_options = list(
            queryset.exclude(category__name__isnull=True)
            .values_list('category__name', flat=True)
            .distinct()
            .order_by('category__name')
        )

        return Response(
            {
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'results': results,
                'category_options': category_options,
            },
            status=status.HTTP_200_OK,
        )


def _is_admin_user(user):
    return user.is_superuser or user.is_staff or user.groups.filter(name='admin').exists()


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in {'1', 'true', 'yes', 'on'}


class DesktopCartAddAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def post(self, request):
        supply_id = request.data.get('supply_id')
        quantity = int(request.data.get('quantity', 1))
        quantity = max(1, quantity)

        if not supply_id:
            return Response({'error': 'supply_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            supply = Supply.objects.get(id=supply_id)
        except Supply.DoesNotExist:
            return Response({'error': 'Supply not found'}, status=status.HTTP_404_NOT_FOUND)

        order, _ = OrderInCart.objects.get_or_create(userCreated=request.user, isComplete=False)

        supp_in_cart, _ = SupplyInOrderInCart.objects.get_or_create(
            supply=supply,
            supply_for_order=order,
            lot=supply.supplyLot,
            date_expired=supply.expiredDate,
            defaults={'date_created': supply.dateCreated, 'count_in_order': 0},
        )
        supp_in_cart.count_in_order = (supp_in_cart.count_in_order or 0) + quantity
        supp_in_cart.save(update_fields=['count_in_order'])

        return Response({
            'success': True,
            'in_cart_count': supp_in_cart.count_in_order,
        }, status=status.HTTP_200_OK)


class DesktopPrecartAddGeneralAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def post(self, request):
        general_supply_id = request.data.get('general_supply_id')
        quantity = int(request.data.get('quantity', 1))
        quantity = max(1, quantity)
        place_id = request.data.get('place_id')

        if not general_supply_id:
            return Response({'error': 'general_supply_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            general_supply = GeneralSupply.objects.get(id=general_supply_id)
        except GeneralSupply.DoesNotExist:
            return Response({'error': 'General supply not found'}, status=status.HTTP_404_NOT_FOUND)

        if place_id:
            place = Place.objects.filter(id=place_id).first()
            preorder_in_cart, _ = PreorderInCart.objects.get_or_create(
                userCreated=request.user,
                isComplete=False,
                defaults={'place': place},
            )
            if preorder_in_cart.place and place and preorder_in_cart.place != place:
                return Response(
                    {'error': 'Неможливо додати до іншої організації, поки існує активний кошик.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            preorder_in_cart, _ = PreorderInCart.objects.get_or_create(
                userCreated=request.user,
                isComplete=False,
            )

        supp_in_cart, _ = SupplyInPreorderInCart.objects.get_or_create(
            supply_for_order=preorder_in_cart,
            general_supply=general_supply,
            defaults={'count_in_order': 0},
        )
        supp_in_cart.count_in_order = (supp_in_cart.count_in_order or 0) + quantity
        supp_in_cart.save(update_fields=['count_in_order'])

        return Response({
            'success': True,
            'in_precart_count': supp_in_cart.count_in_order,
        }, status=status.HTTP_200_OK)


class DesktopAddLotAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def post(self, request):
        if not _is_admin_user(request.user):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        general_supply_id = request.data.get('general_supply_id')
        lot = request.data.get('supplyLot')
        count = request.data.get('count')
        expired_date = request.data.get('expiredDate')

        if not general_supply_id or not lot or count is None:
            return Response(
                {'error': 'general_supply_id, supplyLot, count are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            count = int(count)
            if count < 0:
                raise ValueError()
        except ValueError:
            return Response({'error': 'count must be non-negative integer'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            general_supply = GeneralSupply.objects.get(id=general_supply_id)
        except GeneralSupply.DoesNotExist:
            return Response({'error': 'General supply not found'}, status=status.HTTP_404_NOT_FOUND)

        supply_obj, created = Supply.objects.get_or_create(
            general_supply=general_supply,
            supplyLot=lot,
            expiredDate=expired_date,
            defaults={
                'category': general_supply.category,
                'name': general_supply.name,
                'ref': general_supply.ref,
                'count': 0,
            },
        )
        supply_obj.count = (supply_obj.count or 0) + count
        supply_obj.category = general_supply.category
        supply_obj.name = general_supply.name
        supply_obj.ref = general_supply.ref
        supply_obj.save()

        return Response({
            'success': True,
            'created': created,
            'supply': SupplySerializer(supply_obj).data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DesktopLotDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def patch(self, request, supply_id):
        if not _is_admin_user(request.user):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        try:
            supply_obj = Supply.objects.get(id=supply_id)
        except Supply.DoesNotExist:
            return Response({'error': 'Supply not found'}, status=status.HTTP_404_NOT_FOUND)

        payload = request.data
        if 'supplyLot' in payload:
            supply_obj.supplyLot = payload.get('supplyLot')
        if 'count' in payload:
            try:
                value = int(payload.get('count'))
                if value < 0:
                    raise ValueError()
                supply_obj.count = value
            except ValueError:
                return Response({'error': 'count must be non-negative integer'}, status=status.HTTP_400_BAD_REQUEST)
        if 'expiredDate' in payload:
            supply_obj.expiredDate = payload.get('expiredDate')

        supply_obj.save()
        return Response({'success': True, 'supply': SupplySerializer(supply_obj).data}, status=status.HTTP_200_OK)

    def delete(self, request, supply_id):
        if not _is_admin_user(request.user):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        try:
            supply_obj = Supply.objects.get(id=supply_id)
        except Supply.DoesNotExist:
            return Response({'error': 'Supply not found'}, status=status.HTTP_404_NOT_FOUND)

        supply_obj.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


class DesktopGeneralSupplyDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def patch(self, request, general_supply_id):
        if not _is_admin_user(request.user):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        try:
            general_supply = GeneralSupply.objects.get(id=general_supply_id)
        except GeneralSupply.DoesNotExist:
            return Response({'error': 'General supply not found'}, status=status.HTTP_404_NOT_FOUND)

        payload = request.data
        if 'name' in payload:
            general_supply.name = payload.get('name')
        if 'ref' in payload:
            general_supply.ref = payload.get('ref')
        if 'smn_code' in payload:
            general_supply.SMN_code = payload.get('smn_code')
        if 'package_and_tests' in payload:
            general_supply.package_and_tests = payload.get('package_and_tests')
        general_supply.save()

        # Keep denormalized fields in lots in sync
        general_supply.general.all().update(
            name=general_supply.name,
            ref=general_supply.ref,
            category=general_supply.category,
        )

        return Response({'success': True}, status=status.HTTP_200_OK)


class DesktopCartAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        cart = OrderInCart.objects.filter(userCreated=request.user, isComplete=False).first()
        if not cart:
            return Response({
                'items': [],
                'total_items': 0,
                'total_rows': 0,
                'user_created': None,
            }, status=status.HTTP_200_OK)

        items = cart.supplyinorderincart_set.select_related(
            'supply__general_supply',
            'supply__general_supply__category',
        ).all()
        payload = []
        total_items = 0

        for item in items:
            supply = item.supply
            if not supply:
                continue
            count = int(item.count_in_order or 0)
            total_items += count
            gs = supply.general_supply
            on_hold = int(supply.countOnHold or 0)
            stock = int(supply.count or 0)
            payload.append({
                'id': item.id,
                'supply_id': supply.id,
                'general_supply_id': supply.general_supply_id,
                'name': gs.name if gs else supply.name,
                'ref': gs.ref if gs else supply.ref,
                'smn_code': gs.SMN_code if gs else None,
                'category': gs.category.name if gs and gs.category else None,
                'package_and_tests': gs.package_and_tests if gs else supply.package_and_tests,
                'lot': item.lot,
                'count': count,
                'expiredDate': item.date_expired,
                'stock': stock,
                'available': max(stock - on_hold, 0),
                'on_hold': on_hold,
                'has_supply': True,
            })

        user = cart.userCreated
        user_created = f'{user.first_name} {user.last_name}'.strip() if user else None

        return Response({
            'items': payload,
            'total_items': total_items,
            'total_rows': len(payload),
            'user_created': user_created,
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        cart = OrderInCart.objects.filter(userCreated=request.user, isComplete=False).first()
        if cart:
            cart.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


class DesktopCartItemDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def patch(self, request, item_id):
        cart_item = SupplyInOrderInCart.objects.filter(
            id=item_id,
            supply_for_order__userCreated=request.user,
            supply_for_order__isComplete=False,
        ).first()
        if not cart_item:
            return Response({'error': 'Cart item not found'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action', 'set')
        value = int(request.data.get('value', 1))

        if action == 'plus':
            cart_item.count_in_order = int(cart_item.count_in_order or 0) + 1
        elif action == 'minus':
            cart_item.count_in_order = int(cart_item.count_in_order or 0) - 1
        elif action == 'set':
            cart_item.count_in_order = value
        else:
            return Response({'error': 'Unsupported action'}, status=status.HTTP_400_BAD_REQUEST)

        if cart_item.count_in_order <= 0:
            cart_item.delete()
            return Response({'success': True, 'deleted': True}, status=status.HTTP_200_OK)

        cart_item.save(update_fields=['count_in_order'])
        return Response({
            'success': True,
            'deleted': False,
            'count': cart_item.count_in_order,
        }, status=status.HTTP_200_OK)

    def delete(self, request, item_id):
        cart_item = SupplyInOrderInCart.objects.filter(
            id=item_id,
            supply_for_order__userCreated=request.user,
            supply_for_order__isComplete=False,
        ).first()
        if not cart_item:
            return Response({'error': 'Cart item not found'}, status=status.HTTP_404_NOT_FOUND)
        cart_item.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


def _cart_item_counts_map(request_data, cart_items):
    """Повертає dict item_id -> count з тіла запиту або з кошика."""
    overrides = {}
    for entry in request_data.get('items') or []:
        if isinstance(entry, dict) and entry.get('id') is not None:
            overrides[int(entry['id'])] = int(entry.get('count') or 0)
    result = {}
    for item in cart_items:
        result[item.id] = overrides.get(item.id, int(item.count_in_order or 0))
    return result


def _adjust_supply_on_hold(supply, count_in_order, is_complete):
    if not supply:
        return
    count_on_hold = int(supply.countOnHold or 0)
    if is_complete:
        supply.count = max(int(supply.count or 0) - count_in_order, 0)
        if supply.count == 0:
            supply.delete()
        else:
            supply.save(update_fields=['count'])
    else:
        supply.countOnHold = count_on_hold + count_in_order
        supply.save(update_fields=['countOnHold'])


class DesktopCartCheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    @transaction.atomic
    def post(self, request):
        cart = OrderInCart.objects.filter(userCreated=request.user, isComplete=False).first()
        if not cart:
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        items = list(cart.supplyinorderincart_set.select_related('supply__general_supply').all())
        if not items:
            return Response({'error': 'Cart has no items'}, status=status.HTTP_400_BAD_REQUEST)

        place_id = request.data.get('place_id')
        place = Place.objects.filter(id=place_id).first() if place_id else None
        if not place:
            return Response({'error': 'Place is required for checkout'}, status=status.HTTP_400_BAD_REQUEST)

        counts_map = _cart_item_counts_map(request.data, items)
        comment = request.data.get('comment')
        is_complete = _as_bool(request.data.get('isComplete', False))
        is_pinned = _as_bool(request.data.get('isPinned', False))
        date_to_send = request.data.get('dateToSend')
        order_type = request.data.get('orderType') or 'new_order'
        save_as_booked = _as_bool(request.data.get('saveAsBookedOrder', False))
        date_sent = timezone.now().date() if is_complete else None

        if save_as_booked:
            for item in items:
                if not item.supply:
                    continue
                count = counts_map.get(item.id, 0)
                if count <= 0:
                    continue
                try:
                    sup_in_order = SupplyInBookedOrder.objects.get(
                        supply=item.supply, supply_for_place=place
                    )
                    sup_in_order.count_in_order += count
                except SupplyInBookedOrder.DoesNotExist:
                    gs = item.supply.general_supply
                    sup_in_order = SupplyInBookedOrder(
                        count_in_order=count,
                        generalSupply=gs,
                        supply=item.supply,
                        supply_for_place=place,
                        lot=item.supply.supplyLot,
                        date_expired=item.supply.expiredDate,
                        date_created=item.supply.dateCreated,
                        internalName=gs.name if gs else item.supply.name,
                        internalRef=gs.ref if gs else item.supply.ref,
                    )
                sup_in_order.save()
                item.supply.countOnHold = int(item.supply.countOnHold or 0) + count
                item.supply.save(update_fields=['countOnHold'])
            cart.delete()
            return Response({
                'success': True,
                'booked': True,
                'place_id': place.id,
            }, status=status.HTTP_201_CREATED)

        if order_type == 'add_to_Exist_order':
            selected_order_id = request.data.get('selected_non_completed_order')
            selected_order = Order.objects.filter(
                id=selected_order_id, place=place, isComplete=False
            ).first()
            if not selected_order:
                return Response({'error': 'Selected order not found'}, status=status.HTTP_400_BAD_REQUEST)

            if selected_order.comment and comment:
                selected_order.comment += f' / {comment}'
            elif comment:
                selected_order.comment = comment
            selected_order.dateSent = date_sent
            selected_order.isComplete = is_complete
            selected_order.isPinned = is_pinned
            selected_order.save()

            sups_in_order = list(selected_order.supplyinorder_set.all())
            for item in items:
                if not item.supply:
                    continue
                count = counts_map.get(item.id, 0)
                if count <= 0:
                    continue
                general_sup = item.supply.general_supply
                try:
                    exist_sup = selected_order.supplyinorder_set.get(supply=item.supply)
                    exist_sup.count_in_order += count
                    exist_sup.save()
                    if exist_sup in sups_in_order:
                        sups_in_order.remove(exist_sup)
                    _adjust_supply_on_hold(exist_sup.supply, count, is_complete)
                except SupplyInOrder.DoesNotExist:
                    sup_in_preorder = None
                    if selected_order.for_preorder:
                        try:
                            sup_in_preorder = selected_order.for_preorder.supplyinpreorder_set.get(
                                generalSupply=general_sup
                            )
                        except SupplyInPreorder.DoesNotExist:
                            sup_in_preorder = None
                    SupplyInOrder.objects.create(
                        count_in_order=count,
                        supply=item.supply,
                        generalSupply=general_sup,
                        supply_for_order=selected_order,
                        supply_in_preorder=sup_in_preorder,
                        lot=item.lot,
                        date_created=item.date_created,
                        date_expired=item.date_expired,
                        internalName=general_sup.name if general_sup else item.supply.name,
                        internalRef=general_sup.ref if general_sup else item.supply.ref,
                    )
                    _adjust_supply_on_hold(item.supply, count, is_complete)

            cart.delete()
            return Response({
                'success': True,
                'order_id': selected_order.id,
                'isComplete': is_complete,
                'added_to_existing': True,
            }, status=status.HTTP_200_OK)

        selected_preorder_id = request.data.get('selectedPreorder')
        selected_preorder = None
        if selected_preorder_id:
            selected_preorder = PreOrder.objects.filter(id=selected_preorder_id, place=place).first()

        order = Order.objects.create(
            userCreated=cart.userCreated,
            place=place,
            dateSent=date_sent,
            for_preorder=selected_preorder,
            isComplete=is_complete,
            isPinned=is_pinned,
            comment=comment,
            dateToSend=date_to_send or None,
        )

        for item in items:
            if not item.supply:
                continue
            count = counts_map.get(item.id, 0)
            if count <= 0:
                continue
            supp_in_preorder = None
            if selected_preorder:
                try:
                    supp_in_preorder = selected_preorder.supplyinpreorder_set.get(
                        generalSupply=item.supply.general_supply
                    )
                except SupplyInPreorder.DoesNotExist:
                    supp_in_preorder = None
            gs = item.supply.general_supply
            SupplyInOrder.objects.create(
                count_in_order=count,
                supply=item.supply,
                generalSupply=gs,
                supply_for_order=order,
                supply_in_preorder=supp_in_preorder,
                lot=item.lot,
                date_created=item.date_created,
                date_expired=item.date_expired,
                internalName=gs.name if gs else item.supply.name,
                internalRef=gs.ref if gs else item.supply.ref,
            )
            _adjust_supply_on_hold(item.supply, count, is_complete)

        cart.delete()
        from .push_notifications import send_push_new_order
        send_push_new_order(order)
        return Response({
            'success': True,
            'order_id': order.id,
            'isComplete': is_complete,
        }, status=status.HTTP_201_CREATED)


class DesktopFcmDeviceAPIView(APIView):
    """Реєстрація FCM-токена мобільного пристрою для push-сповіщень."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def post(self, request):
        token = (request.data.get('token') or '').strip()
        platform = (request.data.get('platform') or 'android').strip()
        if not token:
            return Response({'error': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)

        FcmDevice.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'platform': platform,
                'is_active': True,
            },
        )
        return Response({'success': True}, status=status.HTTP_200_OK)

    def delete(self, request):
        token = (request.data.get('token') or '').strip()
        if token:
            FcmDevice.objects.filter(user=request.user, token=token).update(is_active=False)
        return Response({'success': True}, status=status.HTTP_200_OK)


class DesktopAppSettingsAPIView(APIView):
    """Налаштування користувача для мобільного додатку (автозбереження тоглів)."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        from .app_settings_fields import MOBILE_APP_SETTINGS_FIELDS, serialize_app_settings

        app_settings = request.user.get_app_settings()
        payload = serialize_app_settings(app_settings)
        return Response({'settings': payload}, status=status.HTTP_200_OK)

    def patch(self, request):
        from .app_settings_fields import MOBILE_APP_SETTINGS_FIELDS, serialize_app_settings

        field = (request.data.get('field') or '').strip()
        if field not in MOBILE_APP_SETTINGS_FIELDS:
            return Response({'error': 'Invalid field'}, status=status.HTTP_400_BAD_REQUEST)

        raw = request.data.get('value')
        if isinstance(raw, bool):
            value = raw
        else:
            value = str(raw).lower() in ('true', '1', 'on', 'yes')

        app_settings = request.user.get_app_settings()
        setattr(app_settings, field, value)
        app_settings.save(update_fields=[field])
        return Response({'settings': serialize_app_settings(app_settings)}, status=status.HTTP_200_OK)


class DesktopTopbarCountsAPIView(APIView):
    """Лічильники для мобільного сайдбару (аналог cartCountData у header)."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        from .topbar_cart_counts import build_topbar_cart_count_data

        data = build_topbar_cart_count_data(request)
        booked = data.pop('booked_cart_first', None)
        payload = dict(data)
        payload['booked_cart_first_id'] = booked.id if booked else None
        return Response(payload, status=status.HTTP_200_OK)


class DesktopPrecartAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        cart = PreorderInCart.objects.filter(userCreated=request.user, isComplete=False).first()
        if not cart:
            return Response({
                'items': [],
                'total_items': 0,
                'total_rows': 0,
                'place_id': None,
                'place_name': None,
                'place_city': None,
                'user_created': None,
            }, status=status.HTTP_200_OK)

        items = cart.supplyinpreorderincart_set.select_related(
            'general_supply', 'general_supply__category', 'supply'
        ).all()
        payload = []
        total_items = 0

        for item in items:
            gs = item.general_supply
            count = int(item.count_in_order or 0)
            total_items += count
            payload.append({
                'id': item.id,
                'general_supply_id': gs.id if gs else None,
                'supply_id': item.supply_id,
                'name': gs.name if gs else None,
                'ref': gs.ref if gs else None,
                'smn_code': gs.SMN_code if gs else None,
                'category': gs.category.name if gs and gs.category else None,
                'package_and_tests': gs.package_and_tests if gs else None,
                'lot': item.lot,
                'count': count,
            })

        place = cart.place
        user = cart.userCreated
        user_created = f'{user.first_name} {user.last_name}'.strip() if user else None
        place_city = None
        if place:
            city_name = place.city_ref.name if place.city_ref else place.city
            place_city = f'{place.name}, {city_name}' if city_name else place.name

        return Response({
            'items': payload,
            'total_items': total_items,
            'total_rows': len(payload),
            'place_id': place.id if place else None,
            'place_name': place.name if place else None,
            'place_city': place_city,
            'user_created': user_created,
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        cart = PreorderInCart.objects.filter(userCreated=request.user, isComplete=False).first()
        if cart:
            cart.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


class DesktopPrecartItemDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def patch(self, request, item_id):
        cart_item = SupplyInPreorderInCart.objects.filter(
            id=item_id,
            supply_for_order__userCreated=request.user,
            supply_for_order__isComplete=False,
        ).first()
        if not cart_item:
            return Response({'error': 'Precart item not found'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action', 'set')
        value = int(request.data.get('value', 1))

        if action == 'plus':
            cart_item.count_in_order = int(cart_item.count_in_order or 0) + 1
        elif action == 'minus':
            cart_item.count_in_order = int(cart_item.count_in_order or 0) - 1
        elif action == 'set':
            cart_item.count_in_order = value
        else:
            return Response({'error': 'Unsupported action'}, status=status.HTTP_400_BAD_REQUEST)

        if cart_item.count_in_order <= 0:
            cart_item.delete()
            return Response({'success': True, 'deleted': True}, status=status.HTTP_200_OK)

        cart_item.save(update_fields=['count_in_order'])
        return Response({
            'success': True,
            'deleted': False,
            'count': cart_item.count_in_order,
        }, status=status.HTTP_200_OK)

    def delete(self, request, item_id):
        cart_item = SupplyInPreorderInCart.objects.filter(
            id=item_id,
            supply_for_order__userCreated=request.user,
            supply_for_order__isComplete=False,
        ).first()
        if not cart_item:
            return Response({'error': 'Precart item not found'}, status=status.HTTP_404_NOT_FOUND)
        cart_item.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


class DesktopCitiesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        cities = City.objects.all().order_by('name')
        return Response([
            {'id': c.id, 'name': c.name}
            for c in cities
        ], status=status.HTTP_200_OK)


class DesktopPlacesByCityAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        city_id = request.query_params.get('city_id')
        if not city_id:
            return Response({'error': 'city_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        places = Place.objects.filter(city_ref_id=city_id).select_related('city_ref').order_by('name')
        return Response([
            {
                'id': p.id,
                'name': p.name,
                'city': p.city_ref.name if p.city_ref else p.city,
            }
            for p in places
        ], status=status.HTTP_200_OK)


class DesktopCartCheckoutOptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        place_id = request.query_params.get('place_id')
        if not place_id:
            return Response({'error': 'place_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        place = Place.objects.filter(id=place_id).select_related('city_ref').first()
        if not place:
            return Response({'error': 'Place not found'}, status=status.HTTP_404_NOT_FOUND)

        orders = place.order_set.filter(isComplete=False).order_by('-id')
        preorders = place.getUcompletePreorderSet().order_by('-id')
        cart = OrderInCart.objects.filter(userCreated=request.user, isComplete=False).first()
        cart_gs_ids = set()
        if cart:
            for item in cart.supplyinorderincart_set.select_related('supply__general_supply'):
                if item.supply and item.supply.general_supply_id:
                    cart_gs_ids.add(item.supply.general_supply_id)

        return Response({
            'place': {
                'id': place.id,
                'name': place.name,
                'city': place.city_ref.name if place.city_ref else place.city,
            },
            'has_incomplete_orders': orders.exists(),
            'has_linkable_preorders': place.isHaveUncompletedPreorders(),
            'incomplete_orders': [
                {
                    'id': o.id,
                    'label': f'Замовлення №{o.id}, для: {place.name}, {place.city_ref.name if place.city_ref else ""}, від {o.dateCreated.strftime("%d.%m.%Y") if o.dateCreated else ""}',
                }
                for o in orders
            ],
            'linkable_preorders': [
                {
                    'id': p.id,
                    'is_preorder': p.isPreorder,
                    'comment': p.comment,
                    'has_cart_overlap': any(
                        sp.generalSupply_id in cart_gs_ids
                        for sp in p.supplyinpreorder_set.all()
                    ) if cart_gs_ids else False,
                }
                for p in preorders
            ],
        }, status=status.HTTP_200_OK)


class DesktopPrecartCheckoutOptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        place_id = request.query_params.get('place_id')
        if not place_id:
            return Response({'error': 'place_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        place = Place.objects.filter(id=place_id).select_related('city_ref').first()
        if not place:
            return Response({'error': 'Place not found'}, status=status.HTTP_404_NOT_FOUND)

        user_settings = request.user.get_app_settings()
        if user_settings.enable_preorder_editing_awaiting_state:
            preorders = place.preorder_set.filter(
                Q(state_of_delivery='awaiting_from_customer')
                | Q(state_of_delivery='accepted_by_customer')
                | Q(state_of_delivery='Awaiting')
                | Q(state_of_delivery='Partial')
            ).order_by('-id')
        else:
            preorders = place.preorder_set.filter(
                Q(state_of_delivery='awaiting_from_customer')
                | Q(state_of_delivery='accepted_by_customer')
            ).order_by('-id')

        return Response({
            'place': {
                'id': place.id,
                'name': place.name,
                'city': place.city_ref.name if place.city_ref else place.city,
            },
            'incomplete_preorders': [
                {
                    'id': p.id,
                    'is_preorder': p.isPreorder,
                    'comment': p.comment,
                    'state_of_delivery': p.state_of_delivery,
                    'state_display': p.get_state_of_delivery_display(),
                    'label': (
                        f'{"Передзамовлення" if p.isPreorder else "Договір"} №{p.id}'
                        f'{f" | {p.comment}" if p.comment else ""}'
                        f' ({p.get_state_of_delivery_display()})'
                    ),
                }
                for p in preorders
            ],
        }, status=status.HTTP_200_OK)


class DesktopPrecartCheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    @transaction.atomic
    def post(self, request):
        cart = PreorderInCart.objects.filter(userCreated=request.user, isComplete=False).first()
        if not cart:
            return Response({'error': 'Precart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        items = list(cart.supplyinpreorderincart_set.select_related('general_supply').all())
        if not items:
            return Response({'error': 'Precart has no items'}, status=status.HTTP_400_BAD_REQUEST)

        existing_place = cart.place
        place_id = request.data.get('place_id')
        place = existing_place or (Place.objects.filter(id=place_id).first() if place_id else None)
        if not place:
            return Response({'error': 'Place is required for checkout'}, status=status.HTTP_400_BAD_REQUEST)

        counts_map = _cart_item_counts_map(request.data, items)
        comment = request.data.get('comment')
        is_complete = _as_bool(request.data.get('isComplete', False))
        is_pinned = _as_bool(request.data.get('isPinned', False))
        preorder_type = request.data.get('preorderType') or 'new_preorder'
        is_preorder = preorder_type == 'new_preorder'
        selected_preorder_id = request.data.get('selected_non_completed_preorder')
        selected_preorder = None
        if selected_preorder_id:
            selected_preorder = PreOrder.objects.filter(id=selected_preorder_id, place=place).first()

        if selected_preorder is None:
            state_of_delivery = 'awaiting_from_customer'
            if is_complete:
                date_sent = timezone.now().date()
                state_of_delivery = 'accepted_by_customer'
            else:
                date_sent = None
            order = PreOrder(
                userCreated=cart.userCreated,
                place=place,
                dateSent=date_sent,
                isComplete=is_complete,
                isPreorder=is_preorder,
                isPinned=is_pinned,
                comment=comment,
                state_of_delivery=state_of_delivery,
            )
            order.save()
            for item in items:
                count = counts_map.get(item.id, 0)
                if count <= 0:
                    continue
                SupplyInPreorder.objects.create(
                    count_in_order=count,
                    generalSupply=item.general_supply,
                    supply_for_order=order,
                )
            preorder_id = order.id
        else:
            if selected_preorder.comment and comment:
                selected_preorder.comment += f' / {comment}'
            elif comment:
                selected_preorder.comment = comment
            selected_preorder.save()
            sups_in_preorder = selected_preorder.supplyinpreorder_set.all()
            for item in items:
                count = counts_map.get(item.id, 0)
                if count <= 0:
                    continue
                general_sup = item.general_supply
                try:
                    exist_sup = sups_in_preorder.get(generalSupply=general_sup)
                    exist_sup.count_in_order += count
                    exist_sup.save()
                except SupplyInPreorder.DoesNotExist:
                    SupplyInPreorder.objects.create(
                        count_in_order=count,
                        generalSupply=general_sup,
                        supply_for_order=selected_preorder,
                    )
            preorder_id = selected_preorder.id

        cart.delete()
        return Response({
            'success': True,
            'preorder_id': preorder_id,
            'added_to_existing': selected_preorder is not None,
        }, status=status.HTTP_201_CREATED)


class DesktopSupplyHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, general_supply_id):
        general_supply = GeneralSupply.objects.filter(id=general_supply_id).first()
        if not general_supply:
            return Response({'error': 'General supply not found'}, status=status.HTTP_404_NOT_FOUND)

        in_orders = (
            general_supply.inGeneralSupp.all()
            .select_related('supply_for_order__place__city_ref')
            .order_by('-id')[:60]
        )
        in_preorders = (
            general_supply.supplyinpreorder_set.all()
            .select_related('supply_for_order__place__city_ref')
            .order_by('-id')[:60]
        )
        in_deliveries = general_supply.deliverysupplyincart_set.all().order_by('-id')[:60]
        in_booked = (
            general_supply.supplyinbookedorder_set.all()
            .select_related('supply_for_place__city_ref', 'supply')
            .order_by('-id')[:60]
        )

        def to_date(value):
            if not value:
                return None
            return value.strftime('%Y-%m-%d')

        payload = {
            'general_supply': {
                'id': general_supply.id,
                'name': general_supply.name,
                'ref': general_supply.ref,
                'smn_code': general_supply.SMN_code,
                'package_and_tests': general_supply.package_and_tests,
                'category': general_supply.category.name if general_supply.category else None,
            },
            'orders': [
                {
                    'id': item.id,
                    'order_id': item.supply_for_order.id if item.supply_for_order else None,
                    'place': item.supply_for_order.place.name if item.supply_for_order and item.supply_for_order.place else None,
                    'city': item.supply_for_order.place.city_ref.name if item.supply_for_order and item.supply_for_order.place and item.supply_for_order.place.city_ref else None,
                    'count': item.count_in_order,
                    'lot': item.lot,
                    'date_expired': to_date(item.date_expired),
                    'date_created': to_date(item.date_created),
                    'order_date': to_date(item.supply_for_order.dateCreated) if item.supply_for_order else None,
                    'is_complete': item.supply_for_order.isComplete if item.supply_for_order else None,
                }
                for item in in_orders
            ],
            'preorders': [
                {
                    'id': item.id,
                    'preorder_id': item.supply_for_order.id if item.supply_for_order else None,
                    'place': item.supply_for_order.place.name if item.supply_for_order and item.supply_for_order.place else None,
                    'city': item.supply_for_order.place.city_ref.name if item.supply_for_order and item.supply_for_order.place and item.supply_for_order.place.city_ref else None,
                    'count': item.count_in_order,
                    'count_delivered': item.count_in_order_current,
                    'count_debt': (item.count_in_order or 0) - (item.count_in_order_current or 0),
                    'state': item.state_of_delivery,
                    'date_created': to_date(item.supply_for_order.dateCreated) if item.supply_for_order else None,
                }
                for item in in_preorders
            ],
            'deliveries': [
                {
                    'id': item.id,
                    'delivery_id': item.delivery_order_id,
                    'count': item.count,
                    'lot': item.supplyLot,
                    'date_expired': to_date(item.expiredDate),
                    'date_created': to_date(item.delivery_order.date_created) if item.delivery_order else None,
                }
                for item in in_deliveries
            ],
            'booked': [
                {
                    'id': item.id,
                    'place': item.supply_for_place.name if item.supply_for_place else None,
                    'city': item.supply_for_place.city_ref.name if item.supply_for_place and item.supply_for_place.city_ref else None,
                    'count': item.count_in_order,
                    'lot': item.lot,
                    'date_expired': to_date(item.date_expired or (item.supply.expiredDate if item.supply else None)),
                    'date_created': to_date(item.date_created),
                }
                for item in in_booked
            ],
            'totals': {
                'orders_count': sum(item.count_in_order or 0 for item in in_orders),
                'preorders_count': sum(item.count_in_order or 0 for item in in_preorders),
                'deliveries_count': sum(item.count or 0 for item in in_deliveries),
                'booked_count': sum(item.count_in_order or 0 for item in in_booked),
            },
        }

        return Response(payload, status=status.HTTP_200_OK)


class SuppliesFromScanSaveApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        searchtext = str(request.data['searchText'])
        try:
            genSup = (
                GeneralSupply.objects.filter(general__isnull=False)
                .filter(
                    Q(name__icontains=searchtext)
                    | Q(ref__icontains=searchtext)
                    | Q(SMN_code__icontains=searchtext)
                )
                .select_related('category')
                .prefetch_related(
                    Prefetch(
                        'general',
                        queryset=Supply.objects.select_related('category', 'general_supply'),
                    )
                )
                .distinct()
            )
            gensupSerializer = GeneralSupplySerializer(instance=genSup, many=True)
            return Response(gensupSerializer.data, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        serializer = SupplySaveFromScanSerializer(data=request.data)
        if serializer.is_valid():
            print(serializer.validated_data)
            smn = serializer.validated_data['smn']
            lot = serializer.validated_data['supplyLot']
            expDate = serializer.validated_data['expiredDate']
            count = serializer.validated_data['count']
            print(f'SMN -- {smn}')
            try:
                genSup = GeneralSupply.objects.get(Q(SMN_code=smn) | Q(ref=smn))
                try:
                    sup = genSup.general.all().get(supplyLot=lot, expiredDate=expDate)
                    sup.count += count
                except:
                    sup = Supply(name=genSup.name, general_supply=genSup, category=genSup.category, ref=genSup.ref,
                                 supplyLot=lot, count=count, expiredDate=expDate)


                supHistory = sup.get_supp_for_history()
                supHistory.count = count

                try:
                    supForHistory = SupplyForHistory.objects.get(supplyLot=supHistory.supplyLot, dateCreated=supHistory.dateCreated, expiredDate=supHistory.expiredDate)
                    supForHistory.count += supHistory.count
                    supForHistory.action_type = 'added-scan'
                    supForHistory.save()

                except:
                    supHistory.action_type = 'added-scan'
                    supHistory.save()

                sup.save()


                supSerializer = SupplySerializer(sup)
                return Response(supSerializer.data, status=status.HTTP_201_CREATED)
            except:
                return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)


class SupplyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Supply.objects.get(pk=pk)
        except Supply.DoesNotExist:
            raise Http404

    def put(self, request, pk, format=None):
        supply = self.get_object(pk)
        serializer = SupplySerializer(supply, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _order_supply_line_name(item):
    fallback_name = item.internalName
    if not fallback_name and item.generalSupply:
        fallback_name = item.generalSupply.name
    if not fallback_name and item.supply and item.supply.general_supply:
        fallback_name = item.supply.general_supply.name
    return fallback_name


def _order_supply_line_ref(item):
    fallback_ref = item.internalRef
    if not fallback_ref and item.generalSupply:
        fallback_ref = item.generalSupply.ref
    if not fallback_ref and item.supply and item.supply.general_supply:
        fallback_ref = item.supply.general_supply.ref
    return fallback_ref


def _order_supply_line_updated_date(item):
    if item.date_created:
        return item.date_created
    if item.supply and item.supply.dateCreated:
        return item.supply.dateCreated
    return None


def _serialize_order_supply_line(item):
    updated = _order_supply_line_updated_date(item)
    preorder_order_id = None
    if item.supply_in_preorder and item.supply_in_preorder.supply_for_order_id:
        preorder_order_id = item.supply_in_preorder.supply_for_order_id

    return {
        'id': item.id,
        'lot': item.lot,
        'dateCreated': item.date_created.strftime('%d-%m-%Y') if item.date_created else None,
        'dateUpdated': updated.strftime('%d-%m-%Y') if updated else None,
        'expiredDate': item.date_expired.strftime('%d-%m-%Y') if item.date_expired else None,
        'countInOrder': item.count_in_order or 0,
        'preorderOrderId': preorder_order_id,
    }


def _serialize_order_supply_groups(order):
    supplies_qs = (
        SupplyInOrder.objects.filter(supply_for_order=order)
        .select_related(
            'supply',
            'supply__general_supply',
            'generalSupply',
            'generalSupply__category',
            'supply_in_preorder',
            'supply_in_preorder__supply_for_order',
        )
    )
    groups = []
    for group in _group_order_supplies_for_display(supplies_qs):
        first = group['items'][0]
        general_supply = first.generalSupply
        groups.append(
            {
                'counter': group['counter'],
                'generalSupplyId': general_supply.id if general_supply else None,
                'name': _order_supply_line_name(first),
                'ref': _order_supply_line_ref(first),
                'category': (
                    general_supply.category.name
                    if general_supply and general_supply.category
                    else None
                ),
                'package_and_tests': general_supply.package_and_tests if general_supply else None,
                'smn_code': general_supply.SMN_code if general_supply else None,
                'lines': [_serialize_order_supply_line(item) for item in group['items']],
                'totalCount': sum(item.count_in_order or 0 for item in group['items']),
            }
        )
    return groups


class SuppliesInOrderView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    
    def get(self, request, order_id):
        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(_serialize_order_supply_groups(order))


def _serialize_preorder_brief(preorder):
    if not preorder:
        return None
    return {
        'id': preorder.id,
        'isPreorder': preorder.isPreorder,
        'comment': preorder.comment,
    }


def _serialize_preorder_list_item(order):
    return {
        'id': order.id,
        'dateCreated': order.dateCreated.strftime('%d-%m-%Y') if order.dateCreated else None,
        'dateSent': order.dateSent.strftime('%d-%m-%Y') if order.dateSent else None,
        'isComplete': order.isComplete,
        'isPinned': order.isPinned,
        'isPreorder': order.isPreorder,
        'isClosed': order.isClosed,
        'comment': order.comment,
        'state_of_delivery': order.state_of_delivery,
        'state_of_delivery_display': order.get_state_of_delivery_display(),
        'userCreated': {
            'id': order.userCreated.id if order.userCreated else None,
            'full_name': (
                f'{order.userCreated.first_name} {order.userCreated.last_name}'.strip()
                if order.userCreated
                else None
            ),
        },
        'place': {
            'id': order.place.id if order.place else None,
            'name': order.place.name if order.place else None,
            'city': order.place.city_ref.name if order.place and order.place.city_ref else (
                order.place.city if order.place else None
            ),
        },
    }


def _serialize_order_for_api(order):
    np_statuses = list(order.statusnpparselfromdoucmentid_set.all())
    top_status = np_statuses[0] if np_statuses else None
    has_status_np = bool(np_statuses)
    parsel_delivery_status = None
    if top_status and top_status.status_code is not None:
        try:
            parsel_delivery_status = int(top_status.status_code)
        except (TypeError, ValueError):
            parsel_delivery_status = None

    place = order.place
    has_np_setup = bool(place and place.address_NP and place.worker_NP)
    show_np_create = False
    if has_np_setup and not order.isComplete:
        if parsel_delivery_status in (1, 2) or not has_status_np:
            show_np_create = True

    related_preorders = [
        _serialize_preorder_brief(preorder)
        for preorder in order.related_preorders.all()
    ]

    return {
        'id': order.id,
        'dateCreated': order.dateCreated.strftime('%d-%m-%Y') if order.dateCreated else None,
        'dateSent': order.dateSent.strftime('%d-%m-%Y') if order.dateSent else None,
        'isComplete': order.isComplete,
        'isPinned': order.isPinned,
        'isMerged': order.isMerged,
        'dateToSend': order.dateToSend.strftime('%d-%m-%Y') if order.dateToSend else None,
        'comment': order.comment,
        'date_send_is_today': order.date_send_is_today() if order.dateToSend and not order.isComplete else False,
        'date_send_is_expired': order.date_send_is_expired() if order.dateToSend and not order.isComplete else False,
        'is_client_created': order.isClientCreated() if order.userCreated else False,
        'for_preorder': _serialize_preorder_brief(order.for_preorder),
        'related_preorders': related_preorders,
        'related_preorders_count': getattr(order, 'card_related_preorders_count', len(related_preorders)),
        'userCreated': {
            'id': order.userCreated.id if order.userCreated else None,
            'full_name': (
                f'{order.userCreated.first_name} {order.userCreated.last_name}'.strip()
                if order.userCreated
                else None
            ),
        },
        'userSent': {
            'id': order.userSent.id if order.userSent else None,
            'full_name': (
                f'{order.userSent.first_name} {order.userSent.last_name}'.strip()
                if order.userSent
                else None
            ),
        },
        'place': {
            'id': place.id if place else None,
            'name': place.name if place else None,
            'city': place.city_ref.name if place and place.city_ref else None,
            'has_np_setup': has_np_setup,
        },
        'np': {
            'has_documents': order.npdeliverycreateddetailinfo_set.exists(),
            'documents_count': order.npdeliverycreateddetailinfo_set.count(),
            'has_status': has_status_np,
            'status_code': top_status.status_code if top_status else None,
            'status_desc': top_status.status_desc if top_status else None,
            'statuses_count': len(np_statuses),
            'parsel_delivery_status': parsel_delivery_status,
            'show_create_button': show_np_create,
            'statuses': [
                {
                    'status_code': status_item.status_code,
                    'status_desc': status_item.status_desc,
                }
                for status_item in np_statuses
            ],
        },
    }


class OrdersApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    
    def get(self, request):
        is_client = request.user.groups.filter(name='client').exists()
        ordering = _orders_default_ordering()
        if is_client:
            base_qs = Order.objects.filter(place__user=request.user)
        else:
            base_qs = Order.objects.all()
        orders = _orders_list_queryset(base_qs.order_by(*ordering))

        status_filter = request.query_params.get('status')
        if status_filter == 'open':
            orders = orders.filter(isComplete=False)
        elif status_filter == 'completed':
            orders = orders.filter(isComplete=True)

        query = (request.query_params.get('q') or '').strip()
        if query:
            search_q = Q(place__name__icontains=query) | Q(comment__icontains=query)
            if query.isdigit():
                search_q = search_q | Q(id=int(query))
            orders = orders.filter(search_q)

        place_id = request.query_params.get('place_id')
        if place_id:
            try:
                orders = orders.filter(place_id=int(place_id))
            except (TypeError, ValueError):
                pass

        try:
            page_size = int(request.query_params.get('page_size', 12))
        except (TypeError, ValueError):
            page_size = 12
        page_size = max(1, min(page_size, 200))

        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        total_count = orders.count()
        open_count = orders.filter(isComplete=False).count()
        completed_count = orders.filter(isComplete=True).count()
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_orders = orders[start:end]

        payload = [_serialize_order_for_api(order) for order in page_orders]

        return Response(
            {
                'count': total_count,
                'open_count': open_count,
                'completed_count': completed_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'results': payload,
            }
        )


class DesktopPreordersApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        preorders = (
            PreOrder.objects.select_related('place', 'place__city_ref', 'userCreated')
            .order_by('-isPinned', '-id')
        )

        if request.query_params.get('include_closed') != '1':
            preorders = preorders.filter(isClosed=False)

        place_id = request.query_params.get('place_id')
        if place_id:
            try:
                preorders = preorders.filter(place_id=int(place_id))
            except (TypeError, ValueError):
                pass

        status_filter = request.query_params.get('status')
        if status_filter == 'open':
            preorders = preorders.filter(isComplete=False)
        elif status_filter == 'completed':
            preorders = preorders.filter(isComplete=True)

        delivery_states_raw = (request.query_params.get('state_of_delivery') or '').strip()
        if delivery_states_raw:
            delivery_states = [s.strip() for s in delivery_states_raw.split(',') if s.strip()]
            if delivery_states:
                preorders = preorders.filter(state_of_delivery__in=delivery_states)

        cities_raw = (request.query_params.get('cities') or '').strip()
        if cities_raw:
            city_names = [c.strip() for c in cities_raw.split(',') if c.strip()]
            if city_names:
                preorders = preorders.filter(
                    Q(place__city_ref__name__in=city_names) | Q(place__city__in=city_names)
                )

        date_from_raw = (request.query_params.get('date_from') or '').strip()
        if date_from_raw:
            try:
                date_from = datetime.strptime(date_from_raw, '%Y-%m-%d').date()
                preorders = preorders.filter(dateCreated__gte=date_from)
            except ValueError:
                pass

        date_to_raw = (request.query_params.get('date_to') or '').strip()
        if date_to_raw:
            try:
                date_to = datetime.strptime(date_to_raw, '%Y-%m-%d').date()
                preorders = preorders.filter(dateCreated__lte=date_to)
            except ValueError:
                pass

        is_preorder = request.query_params.get('is_preorder')
        if is_preorder == '1':
            preorders = preorders.filter(isPreorder=True)
        elif is_preorder == '0':
            preorders = preorders.filter(isPreorder=False)

        place_type = request.query_params.get('place_type')
        if place_type == '1':
            preorders = preorders.filter(place__isPrivatePlace=True)
        elif place_type == '0':
            preorders = preorders.filter(place__isPrivatePlace=False)

        query = (request.query_params.get('q') or '').strip()
        if query:
            search_q = (
                Q(place__name__icontains=query)
                | Q(comment__icontains=query)
                | Q(place__city_ref__name__icontains=query)
                | Q(place__city__icontains=query)
            )
            if query.isdigit():
                search_q = search_q | Q(id=int(query))
            preorders = preorders.filter(search_q)

        try:
            page_size = int(request.query_params.get('page_size', 12))
        except (TypeError, ValueError):
            page_size = 12
        page_size = max(1, min(page_size, 200))

        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        total_count = preorders.count()
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_preorders = preorders[start:end]

        payload = [_serialize_preorder_list_item(order) for order in page_preorders]

        return Response(
            {
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'results': payload,
            }
        )


class SuppliesInPreorderView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, preorder_id):
        preorder = (
            PreOrder.objects.filter(id=preorder_id)
            .select_related('place', 'place__city_ref', 'userCreated')
            .first()
        )
        if not preorder:
            return Response({'error': 'Preorder not found'}, status=status.HTTP_404_NOT_FOUND)

        items = (
            SupplyInPreorder.objects.filter(supply_for_order=preorder)
            .select_related('generalSupply', 'generalSupply__category')
            .prefetch_related(
                Prefetch(
                    'supplyinorder_set',
                    queryset=SupplyInOrder.objects.select_related('supply_for_order').order_by('id'),
                )
            )
            .order_by('id')
        )

        payload_items = []
        for item in items:
            gs = item.generalSupply
            ordered = item.count_in_order or 0
            delivered = item.count_in_order_current or 0
            booked = item.get_booked_count() or 0
            lines = []
            for line in item.supplyinorder_set.all():
                order_ref = line.supply_for_order
                lines.append(
                    {
                        'lot': line.lot,
                        'countInOrder': line.count_in_order or 0,
                        'expiredDate': line.date_expired.strftime('%Y-%m-%d') if line.date_expired else None,
                        'preorderOrderId': order_ref.id if order_ref else None,
                    }
                )

            payload_items.append(
                {
                    'id': item.id,
                    'name': gs.name if gs else "Unknown",
                    'ref': gs.ref if gs else None,
                    'category': gs.category.name if gs and gs.category else None,
                    'smn_code': gs.SMN_code if gs else None,
                    'package_and_tests': gs.package_and_tests if gs else None,
                    'countInOrder': ordered,
                    'countDelivered': delivered,
                    'countDebt': max(ordered - delivered, 0),
                    'bookedCount': booked,
                    'state_of_delivery': item.state_of_delivery,
                    'lines': lines,
                }
            )

        return Response(
            {
                'isComplete': preorder.isComplete,
                'preorder': _serialize_preorder_list_item(preorder),
                'items': payload_items,
            }
        )


class DesktopDeliveryUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def post(self, request):
        barcode_type = (request.data.get('barcode_type') or 'Data Matrix').strip()
        scans = request.data.get('scans') or []
        if not isinstance(scans, list):
            return Response({'error': 'scans must be an array'}, status=status.HTTP_400_BAD_REQUEST)

        prepared_scans = [str(item).strip() for item in scans if str(item).strip()]
        if not prepared_scans:
            return Response({'error': 'No scans provided'}, status=status.HTTP_400_BAD_REQUEST)

        delivery_order = DeliveryOrder.objects.create(from_user=request.user)
        string_data = ' '.join(prepared_scans)
        delivered_items, total_requests = makeDataUpload_nonCelery(
            string_data,
            delivery_order,
            barcode_type,
        )
        recognized_count = len([item for item in delivered_items if item.general_supply_id is not None])
        unrecognized_count = len(delivered_items) - recognized_count

        return Response(
            {
                'success': True,
                'delivery_order_id': delivery_order.id,
                'total_requests': total_requests,
                'recognized_count': recognized_count,
                'unrecognized_count': unrecognized_count,
            },
            status=status.HTTP_201_CREATED,
        )


class DesktopOrderMetaAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, order_id):
        order = (
            Order.objects.filter(id=order_id)
            .select_related('place', 'place__city_ref', 'userCreated', 'userSent', 'for_preorder')
            .prefetch_related('statusnpparselfromdoucmentid_set', 'npdeliverycreateddetailinfo_set')
            .first()
        )
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        np_statuses = [
            {
                'id': status_item.id,
                'status_code': status_item.status_code,
                'status_desc': status_item.status_desc,
                'doc_number': status_item.docNumber,
                'recipient': status_item.counterpartyRecipientDescription,
                'scheduled_delivery': status_item.scheduledDeliveryDate,
                'actual_delivery': status_item.actualDeliveryDate,
                'recipient_datetime': status_item.recipientDateTime,
            }
            for status_item in order.statusnpparselfromdoucmentid_set.all().order_by('-id')
        ]
        documents = [
            {
                'id': item.id,
                'document_id': item.document_id,
                'estimated_time_delivery': item.estimated_time_delivery,
                'cost_on_site': item.cost_on_site,
            }
            for item in order.npdeliverycreateddetailinfo_set.all().order_by('-id')
        ]

        return Response(
            {
                'id': order.id,
                'isComplete': order.isComplete,
                'isPinned': order.isPinned,
                'isMerged': order.isMerged,
                'dateCreated': order.dateCreated.strftime('%d-%m-%Y') if order.dateCreated else None,
                'dateSent': order.dateSent.strftime('%d-%m-%Y') if order.dateSent else None,
                'dateToSend': order.dateToSend.strftime('%d-%m-%Y') if order.dateToSend else None,
                'comment': order.comment,
                'date_send_is_today': order.date_send_is_today() if order.dateToSend and not order.isComplete else False,
                'date_send_is_expired': order.date_send_is_expired() if order.dateToSend and not order.isComplete else False,
                'is_client_created': order.isClientCreated() if order.userCreated else False,
                'for_preorder': _serialize_preorder_brief(order.for_preorder),
                'userCreated': {
                    'id': order.userCreated.id if order.userCreated else None,
                    'full_name': (
                        f'{order.userCreated.first_name} {order.userCreated.last_name}'.strip()
                        if order.userCreated
                        else None
                    ),
                },
                'userSent': {
                    'id': order.userSent.id if order.userSent else None,
                    'full_name': (
                        f'{order.userSent.first_name} {order.userSent.last_name}'.strip()
                        if order.userSent
                        else None
                    ),
                },
                'place': {
                    'id': order.place.id if order.place else None,
                    'name': order.place.name if order.place else None,
                    'city': order.place.city_ref.name if order.place and order.place.city_ref else None,
                },
                'np': {
                    'documents': documents,
                    'statuses': np_statuses,
                },
            }
        )


class DesktopOrderPinnedAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def post(self, request, order_id):
        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        is_pinned = _as_bool(request.data.get('isPinned', False))
        order.isPinned = is_pinned
        order.save(update_fields=['isPinned'])
        return Response({'success': True, 'isPinned': order.isPinned})


class DesktopOrderCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def post(self, request, order_id):
        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        if order.isComplete:
            return Response({'error': 'Order already completed'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = update_order_status_core(order, request.user)
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'success': True,
                'id': order.id,
                'isComplete': order.isComplete,
                'dateSent': order.dateSent.strftime('%d-%m-%Y') if order.dateSent else None,
            }
        )


class DesktopOrderNPRefreshAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, order_id):
        return self._refresh(request, order_id)

    def post(self, request, order_id):
        return self._refresh(request, order_id)

    def _refresh(self, request, order_id):
        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        force = _as_bool(request.query_params.get('force'))
        parsels_status_data, no_more_update = get_np_delivery_details(
            order,
            respect_refresh_cooldown=not force,
        )
        statuses = [
            {
                'id': item.id,
                'status_code': item.status_code,
                'status_desc': item.status_desc,
                'doc_number': item.docNumber,
                'recipient': item.counterpartyRecipientDescription,
                'scheduled_delivery': item.scheduledDeliveryDate,
                'actual_delivery': item.actualDeliveryDate,
                'recipient_datetime': item.recipientDateTime,
            }
            for item in parsels_status_data
        ]
        return Response(
            {
                'success': True,
                'no_more_update': no_more_update,
                'statuses': statuses,
            }
        )


def _user_can_np_uncompleted_modal(user):
    return user.is_authenticated and (
        getattr(user, 'is_staff', False)
        or user.groups.filter(name='empl').exists()
    )


def _serialize_np_uncompleted_rows(orders_list):
    rows = []
    for order in orders_list:
        parsels_status_data = get_parsels_status_data(order)
        has_status, status_code = get_order_status(order)
        no_more_update = bool(has_status and status_code in (2, 9))
        place = order.place
        rows.append(
            {
                'orderId': order.id,
                'placeName': place.name if place else None,
                'placeCity': (
                    place.city_ref.name if place and place.city_ref
                    else (place.city if place else None)
                ),
                'parsels': [
                    {
                        'docNumber': item.docNumber,
                        'statusCode': item.status_code,
                        'statusDesc': item.status_desc,
                    }
                    for item in parsels_status_data
                ],
                'noMoreUpdate': no_more_update,
            }
        )
    return rows


class DesktopNpUncompletedOrdersApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        if not _user_can_np_uncompleted_modal(request.user):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        orders_list = list(
            queryset_orders_with_uncompleted_np_tracking().select_related(
                'place',
                'place__city_ref',
            )
        )

        do_refresh = request.query_params.get('refresh') in ('1', 'true', 'yes')
        refresh_failed = False
        if do_refresh:
            try:
                refresh_np_tracking_for_orders_batch(orders_list)
            except Exception:
                logger.exception('DesktopNpUncompletedOrdersApiView: batch NP refresh failed')
                refresh_failed = True

        return Response(
            {
                'refreshPending': not do_refresh,
                'refreshFailed': refresh_failed if do_refresh else False,
                'rows': _serialize_np_uncompleted_rows(orders_list),
            }
        )


def _np_choice_options(choices):
    return [{'value': value, 'label': label} for value, label in choices]


def _serialize_np_form(order, user):
    for_place = order.place
    if not for_place or not for_place.address_NP or not for_place.worker_NP:
        return None

    sender_places = SenderNPPlaceInfo.objects.filter(for_user=user)
    input_form = CreateNPParselForm(instance=order)
    place_form = ClientFormForParcel(instance=for_place)
    place_form.fields['worker_NP'].queryset = for_place.workers.all()
    place_form.fields['address_NP'].queryset = for_place.delivery_places.all()
    input_form.fields['sender_np_place'].queryset = sender_places

    try:
        sendplace = sender_places.get(id=user.np_last_choosed_delivery_place_id)
    except (SenderNPPlaceInfo.DoesNotExist, TypeError, ValueError):
        sendplace = None

    today = timezone.localdate()
    initial_date = input_form.fields['dateDelivery'].initial or today

    return {
        'order': {
            'id': order.id,
            'comment': order.comment,
            'place': {
                'name': for_place.name,
                'city': for_place.city_ref.name if for_place.city_ref else None,
            },
        },
        'title': (
            f'Сформувати інтернет-документ для:\n'
            f'- Замовлення №{order.id}\n'
            f'- {for_place.name}, {for_place.city_ref.name if for_place.city_ref else ""}'
        ),
        'initial': {
            'address_NP': for_place.address_NP_id,
            'worker_NP': for_place.worker_NP_id,
            'sender_np_place': sendplace.id if sendplace else None,
            'payment_user_type': (
                input_form.fields['payment_user_type'].initial
                or CreateParselModel.PaymentUserType.ВІДПРАВНИК.value
            ),
            'payment_money_type': (
                input_form.fields['payment_money_type'].initial
                or CreateParselModel.PaymentMoneyType.БЕЗГОТІВКОВИЙ.value
            ),
            'cargo_type': input_form.fields['cargo_type'].initial or CargoType.PARCEL.value,
            'weight': '',
            'width': '',
            'length': '',
            'height': '',
            'description': input_form.fields['description'].initial or 'Товари медичного призначення',
            'cost': input_form.fields['cost'].initial or 300,
            'dateDelivery': initial_date.isoformat() if hasattr(initial_date, 'isoformat') else str(initial_date),
        },
        'min_date_delivery': today.isoformat(),
        'choices': {
            'address_NP': [
                {
                    'id': address.id,
                    'label': f'{address.cityName}, {address.addressName}',
                }
                for address in for_place.delivery_places.all()
            ],
            'worker_NP': [
                {
                    'id': worker.id,
                    'label': str(worker),
                }
                for worker in for_place.workers.all()
            ],
            'sender_np_place': [
                {
                    'id': sender_place.id,
                    'label': f'{sender_place.cityName}, {sender_place.addressName}',
                }
                for sender_place in sender_places
            ],
            'payment_user_type': _np_choice_options(CreateParselModel.PaymentUserType.choices),
            'payment_money_type': _np_choice_options(CreateParselModel.PaymentMoneyType.choices),
            'cargo_type': _np_choice_options(CargoType.choices()),
        },
        'labels': {
            'address_NP': place_form.fields['address_NP'].label,
            'worker_NP': place_form.fields['worker_NP'].label,
            'sender_np_place': input_form.fields['sender_np_place'].label,
            'payment_user_type': input_form.fields['payment_user_type'].label,
            'payment_money_type': input_form.fields['payment_money_type'].label,
            'cargo_type': input_form.fields['cargo_type'].label,
            'weight': input_form.fields['weight'].label,
            'width': input_form.fields['width'].label,
            'length': input_form.fields['length'].label,
            'height': input_form.fields['height'].label,
            'description': input_form.fields['description'].label,
            'cost': input_form.fields['cost'].label,
            'dateDelivery': input_form.fields['dateDelivery'].label,
        },
    }


def _np_payload_to_querydict(payload):
    qd = QueryDict(mutable=True)
    scalar_fields = [
        'address_NP',
        'worker_NP',
        'sender_np_place',
        'payment_user_type',
        'payment_money_type',
        'cargo_type',
        'weight',
        'width',
        'length',
        'height',
        'description',
        'cost',
        'dateDelivery',
        'order_id',
    ]
    for field in scalar_fields:
        value = payload.get(field)
        if value is not None and value != '':
            qd[field] = str(value)

    extra_places = payload.get('extra_places') or []
    for place in extra_places:
        for key in ('weight_input_field', 'width_input_field', 'length_input_field', 'height_input_field'):
            source_key = key.replace('_input_field', '')
            value = place.get(source_key)
            if value is not None and value != '':
                qd.appendlist(key, str(value))

    if _as_bool(payload.get('save_and_print')):
        qd['save_and_print'] = '1'
    elif _as_bool(payload.get('save_and_exit', True)):
        qd['save_and_exit'] = '1'

    return qd


def _prepare_np_forms(order, user, data):
    for_place = order.place
    sender_places = SenderNPPlaceInfo.objects.filter(for_user=user)
    input_form = CreateNPParselForm(data, instance=order)
    place_form = ClientFormForParcel(data, instance=for_place)
    input_form.fields['sender_np_place'].queryset = sender_places
    place_form.fields['worker_NP'].queryset = for_place.workers.all()
    place_form.fields['address_NP'].queryset = for_place.delivery_places.all()
    return input_form, place_form


def _format_np_form_errors(input_form, place_form):
    parts = []
    if not input_form.is_valid():
        parts.append('Параметри відправлення: ' + '; '.join(
            f'{field}: {", ".join(errors)}' for field, errors in input_form.errors.items()
        ))
    if not place_form.is_valid():
        parts.append('Отримувач: ' + '; '.join(
            f'{field}: {", ".join(errors)}' for field, errors in place_form.errors.items()
        ))
    return ' '.join(parts) if parts else 'Помилка валідації форми'


class DesktopOrderNPFormAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, order_id):
        if not (request.user.is_staff or request.user.groups.filter(name='empl').exists()):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        order = (
            Order.objects.filter(id=order_id)
            .select_related('place', 'place__city_ref', 'place__address_NP', 'place__worker_NP')
            .first()
        )
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        if order.isComplete:
            return Response({'error': 'Order already completed'}, status=status.HTTP_400_BAD_REQUEST)

        form_payload = _serialize_np_form(order, request.user)
        if not form_payload:
            return Response({'error': 'NP is not configured for this place'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(form_payload)


class DesktopOrderNPCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def post(self, request, order_id):
        if not (request.user.is_staff or request.user.groups.filter(name='empl').exists()):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        order = Order.objects.filter(id=order_id).select_related('place').first()
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        if order.isComplete:
            return Response({'error': 'Order already completed'}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data if isinstance(request.data, dict) else {}
        post_data = _np_payload_to_querydict(payload)
        post_data['order_id'] = str(order_id)

        input_form, place_form = _prepare_np_forms(order, request.user, post_data)
        if not input_form.is_valid() or not place_form.is_valid():
            return Response(
                {
                    'success': False,
                    'error': _format_np_form_errors(input_form, place_form),
                    'form_errors': {
                        'input': input_form.errors,
                        'place': place_form.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        redirect_url = _as_bool(payload.get('save_and_print'))
        try:
            threading_create_np_document_async(request, post_data, order_id, redirect_url)
        except Exception as exc:
            return Response({'success': False, 'error': str(exc).strip()}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'success': True,
                'message': 'Накладна успішно створена',
                'order_id': order_id,
            }
        )


class PlacesApiView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        places = Place.objects.all()
        placesSerializer = PlaceSerializer(instance=places, many=True)
        return Response(placesSerializer.data)

    def post(self, request):
        serializer = PlaceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _clients_filtered_queryset(request):
    qs = Place.objects.all().order_by('-id')
    q = (request.query_params.get('q') or request.query_params.get('name') or '').strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(city__icontains=q)
            | Q(city_ref__name__icontains=q)
        )
    place_filter = PlaceFilter(request.query_params, queryset=qs)
    return _place_list_for_client_cards(place_filter.qs)


def _serialize_client_worker(worker, np_worker_id):
    full_name = ' '.join(
        part for part in [worker.secondName, worker.name, worker.middleName] if part
    ).strip()
    return {
        'id': worker.id,
        'fullName': full_name or None,
        'telNumber': worker.telNumber,
        'position': worker.position,
        'isNpWorker': bool(np_worker_id and worker.id == np_worker_id),
    }


def _serialize_client_card(place):
    city_name = place.city_ref.name if place.city_ref else place.city
    np_worker_id = place.worker_NP_id
    return {
        'id': place.id,
        'name': place.name,
        'city': city_name,
        'address': place.address,
        'link': place.link,
        'isPrivatePlace': place.isPrivatePlace,
        'counts': {
            'orders': getattr(place, 'card_order_count', 0) or 0,
            'preorders': getattr(place, 'card_preorder_count', 0) or 0,
            'devices': getattr(place, 'card_device_count', 0) or 0,
            'serviceNotes': getattr(place, 'card_servicenote_count', 0) or 0,
            'booked': getattr(place, 'card_booked_count', 0) or 0,
            'workers': getattr(place, 'card_workers_count', 0) or 0,
        },
        'workers': [
            _serialize_client_worker(worker, np_worker_id)
            for worker in place.workers.all()
        ],
    }


class DesktopClientsApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        queryset = _clients_filtered_queryset(request)

        try:
            page_size = int(request.query_params.get('page_size', 10))
        except (TypeError, ValueError):
            page_size = 10
        page_size = max(1, min(page_size, 50))

        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        total_count = queryset.count()
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_places = list(queryset[start:end])

        return Response(
            {
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'results': [_serialize_client_card(place) for place in page_places],
            }
        )


class DesktopClientDevicesApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, place_id):
        place = Place.objects.filter(id=place_id).select_related('city_ref').first()
        if not place:
            return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        devices = devices_list_queryset(Device.objects.filter(in_place_id=place.id))
        payload = []
        for device in devices:
            payload.append(
                {
                    'id': device.id,
                    'name': device.general_device.name if device.general_device else None,
                    'serialNumber': device.serial_number,
                    'dateInstalled': device.date_installed.strftime('%d-%m-%Y') if device.date_installed else None,
                    'imageUrl': device.image.url if device.image else None,
                }
            )

        return Response(
            {
                'place': {
                    'id': place.id,
                    'name': place.name,
                    'city': place.city_ref.name if place.city_ref else place.city,
                },
                'results': payload,
            }
        )


class DesktopClientServiceNotesApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, place_id):
        place = Place.objects.filter(id=place_id).select_related('city_ref').first()
        if not place:
            return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        notes = servicenotes_list_queryset(ServiceNote.objects.filter(for_place_id=place.id).order_by('-id'))
        payload = []
        for note in notes:
            engineer = note.from_user
            payload.append(
                {
                    'id': note.id,
                    'description': note.description,
                    'dateCreated': note.dateCreated.strftime('%d-%m-%Y') if note.dateCreated else None,
                    'engineerName': (
                        f'{engineer.last_name} {engineer.first_name}'.strip() if engineer else None
                    ),
                }
            )

        return Response(
            {
                'place': {
                    'id': place.id,
                    'name': place.name,
                    'city': place.city_ref.name if place.city_ref else place.city,
                },
                'results': payload,
            }
        )


class DesktopClientBookedSuppliesApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, place_id):
        place = Place.objects.filter(id=place_id).select_related('city_ref').first()
        if not place:
            return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        booked_qs = (
            SupplyInBookedOrder.objects.filter(supply_for_place_id=place.id)
            .select_related('generalSupply', 'generalSupply__category', 'supply')
            .order_by('generalSupply__name', 'id')
        )
        payload = []
        for item in booked_qs:
            gs = item.generalSupply
            payload.append(
                {
                    'id': item.id,
                    'name': gs.name if gs else item.internalName,
                    'ref': gs.ref if gs else item.internalRef,
                    'category': gs.category.name if gs and gs.category else None,
                    'smnCode': gs.SMN_code if gs else None,
                    'packageAndTests': gs.package_and_tests if gs else None,
                    'lot': item.lot or (item.supply.supplyLot if item.supply else None),
                    'count': item.count_in_order or 0,
                    'countOnHold': item.countOnHold or 0,
                    'expiredDate': item.date_expired.strftime('%d-%m-%Y') if item.date_expired else None,
                }
            )

        return Response(
            {
                'place': {
                    'id': place.id,
                    'name': place.name,
                    'city': place.city_ref.name if place.city_ref else place.city,
                },
                'results': payload,
            }
        )


def _delivery_line_expiry_status(line, delivery_date):
    expiry = line.expiredDate
    if not line.general_supply_id:
        expiry, _expiry_iso = scan_expiry_for_delivery_line(line)
    if not expiry or not delivery_date:
        return None
    if expiry > delivery_date:
        return 'good'
    if expiry == delivery_date:
        return 'today'
    return 'bad'


def _serialize_delivery_line(line, delivery_date):
    if line.general_supply_id:
        expiry = line.expiredDate
        expiry_label = expiry.strftime('%d.%m.%Y') if expiry else None
    else:
        expiry, _expiry_iso = scan_expiry_for_delivery_line(line)
        expiry_label = (
            expiry.strftime('%d.%m.%Y') if expiry else (line.expiredDate_desc or None)
        )
    return {
        'id': line.id,
        'lot': line.supplyLot or None,
        'count': line.count or 0,
        'expiredDate': expiry_label,
        'isHandleAdded': line.isHandleAdded,
        'expiryStatus': _delivery_line_expiry_status(line, delivery_date),
    }


def _serialize_delivery_group(group, delivery_date):
    items = group.get('items') or []
    if not items:
        return None
    first = items[0]
    if first.general_supply_id:
        gs = first.general_supply
        return {
            'counter': group['counter'],
            'generalSupplyId': gs.id,
            'name': gs.name,
            'ref': gs.ref,
            'category': gs.category.name if gs.category else None,
            'packageAndTests': gs.package_and_tests,
            'smnCode': gs.SMN_code,
            'lines': [
                _serialize_delivery_line(item, delivery_date)
                for item in items
            ],
        }
    smn, ref = merge_identifiers_for_delivery_line(first)
    return {
        'counter': group['counter'],
        'generalSupplyId': None,
        'name': first.barcode or None,
        'ref': ref or None,
        'category': None,
        'packageAndTests': None,
        'smnCode': smn or None,
        'lines': [
            _serialize_delivery_line(item, delivery_date)
            for item in items
        ],
    }


def _serialize_delivery_list_item(delivery):
    user_name = ''
    if delivery.from_user:
        user_name = (
            f'{delivery.from_user.first_name or ""} '
            f'{delivery.from_user.last_name or ""}'
        ).strip()
    return {
        'id': delivery.id,
        'dateCreated': (
            delivery.date_created.strftime('%d.%m.%Y')
            if delivery.date_created else None
        ),
        'comment': delivery.comment or None,
        'isHasBeenSaved': delivery.isHasBeenSaved,
        'fromUser': (
            {'id': delivery.from_user_id, 'fullName': user_name}
            if delivery.from_user else None
        ),
    }


def _serialize_delivery_detail(delivery):
    supplies = list(_delivery_cart_line_queryset(delivery.id))
    total_count = sum((item.count or 0) for item in supplies)
    recognized = [item for item in supplies if item.isRecognized]
    unrecognized = [item for item in supplies if not item.isRecognized]
    recognized_groups = [
        g for g in (
            _serialize_delivery_group(group, delivery.date_created)
            for group in _group_delivery_supplies_for_display(recognized)
        )
        if g
    ]
    unrecognized_groups = [
        g for g in (
            _serialize_delivery_group(group, delivery.date_created)
            for group in _group_delivery_supplies_for_display(unrecognized)
        )
        if g
    ]
    user_name = ''
    if delivery.from_user:
        user_name = (
            f'{delivery.from_user.first_name or ""} '
            f'{delivery.from_user.last_name or ""}'
        ).strip()
    subtitle_parts = []
    if user_name:
        subtitle_parts.append(user_name)
    if delivery.date_created:
        subtitle_parts.append(delivery.date_created.strftime('%d.%m.%Y'))
    return {
        'id': delivery.id,
        'dateCreated': (
            delivery.date_created.strftime('%d.%m.%Y')
            if delivery.date_created else None
        ),
        'comment': delivery.comment or None,
        'isHasBeenSaved': delivery.isHasBeenSaved,
        'fromUser': (
            {'id': delivery.from_user_id, 'fullName': user_name}
            if delivery.from_user else None
        ),
        'subtitle': ' · '.join(subtitle_parts) or None,
        'totalCount': total_count,
        'totalGroupCount': len(recognized_groups) + len(unrecognized_groups),
        'recognizedGroups': recognized_groups,
        'unrecognizedGroups': unrecognized_groups,
    }


class DesktopDeliveriesApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        queryset = (
            DeliveryOrder.objects.select_related('from_user')
            .order_by('-id')
        )

        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (TypeError, ValueError):
            page_size = 20
        page_size = max(1, min(page_size, 50))

        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        total_count = queryset.count()
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_deliveries = list(queryset[start:end])

        return Response(
            {
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'results': [
                    _serialize_delivery_list_item(delivery)
                    for delivery in page_deliveries
                ],
            }
        )


class DesktopDeliveryDetailApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request, delivery_id):
        delivery = (
            DeliveryOrder.objects.select_related('from_user')
            .filter(pk=delivery_id)
            .first()
        )
        if not delivery:
            raise Http404
        return Response(_serialize_delivery_detail(delivery))


def _serialize_device_list_item(device):
    place = device.in_place
    city_name = None
    if place:
        city_name = place.city_ref.name if place.city_ref else place.city
    return {
        'id': device.id,
        'name': device.general_device.name if device.general_device else None,
        'serialNumber': device.serial_number or None,
        'dateInstalled': (
            device.date_installed.strftime('%d.%m.%Y')
            if device.date_installed else None
        ),
        'imageUrl': device.image.url if device.image else None,
        'place': (
            {
                'id': place.id,
                'name': place.name,
                'city': city_name,
            }
            if place else None
        ),
    }


class DesktopDevicesApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        queryset = devices_list_queryset(Device.objects.all().order_by('-id'))

        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (TypeError, ValueError):
            page_size = 20
        page_size = max(1, min(page_size, 50))

        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        total_count = queryset.count()
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_devices = list(queryset[start:end])

        return Response(
            {
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'results': [
                    _serialize_device_list_item(device)
                    for device in page_devices
                ],
            }
        )


def _serialize_np_register(register, request=None):
    barcode_url = (register.barcode_url or '').strip()
    if not barcode_url and register.barcode:
        barcode_url = request.build_absolute_uri(register.barcode.url) if request else register.barcode.url
    register_url = (register.register_url or '').strip()
    return {
        'id': register.id,
        'barcodeString': register.barcode_string,
        'barcodeUrl': barcode_url or None,
        'registerUrl': register_url or None,
        'date': register.date,
        'forOrders': list(register.for_orders or []),
    }


class DesktopNpRegistersApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    def get(self, request):
        queryset = RegisterNPInfo.objects.all().order_by('-id')

        try:
            page_size = int(request.query_params.get('page_size', 10))
        except (TypeError, ValueError):
            page_size = 10
        page_size = max(1, min(page_size, 50))

        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        total_count = queryset.count()
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_registers = list(queryset[start:end])

        return Response(
            {
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'results': [
                    _serialize_np_register(register, request)
                    for register in page_registers
                ],
            }
        )


class RegistrationAPIView(APIView):
    """
    Registers a new user.
    """
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    def post(self, request):
        """
        Creates a new User object.
        Username, email, and password are required.
        Returns a JSON web token.
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        jwt_token = create_jwt_token(user)

        return Response(
            {
                'token': serializer.data.get('token', None),
                'jwt_token': jwt_token,
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


def create_jwt_token(user):
    """
    Create JWT token for user
    """
    payload = {
        'id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(days=7),  # Token expires in 7 days
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(request, username=username, password=password)

            if user:
                login(request, user)
                # Create both Token and JWT token
                token, created = Token.objects.get_or_create(user=user)
                jwt_token = create_jwt_token(user)
                
                # Serialize the User object
                user_serializer = UserSerializer(user)

                # Include the serialized User data in the response
                response_data = {
                    'token': token.key,
                    'jwt_token': jwt_token,
                    'user': user_serializer.data,
                }

                return Response(response_data, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        try:
            # Delete the token
            request.user.auth_token.delete()
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SupplyHoldInfoView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, supply_id):
        try:
            supply = Supply.objects.get(id=supply_id)
            hold_info = []
            
            # Get regular orders that have this supply on hold
            orders_with_supply = supply.inSupply.filter(
                supply_for_order__isComplete=False
            ).select_related('supply_for_order__place__city_ref')
            
            # Add regular orders info
            for order in orders_with_supply:
                place = order.supply_for_order.place
                hold_info.append({
                    'type': 'order',
                    'order_id': order.supply_for_order.id,
                    'sup_in_order_id': order.id,
                    'place_name': place.name,
                    'place': place.name,
                    'city': place.city_ref.name if place.city_ref else None,
                    'count': order.count_in_order,
                    'date_created': order.supply_for_order.dateCreated.strftime('%d.%m.%Y') if order.supply_for_order.dateCreated else None
                })
            
            # Get booked orders that have this supply on hold
            booked_orders_with_supply = supply.supplyinbookedorder_set.select_related(
                'supply_for_place__city_ref'
            ).all()
            
            # Add booked orders info
            for booked_order in booked_orders_with_supply:
                place = booked_order.supply_for_place
                hold_info.append({
                    'type': 'booked',
                    'place_name': place.name,
                    'place': place.name,
                    'city': place.city_ref.name if place.city_ref else None,
                    'order_id': place.id,
                    'count': booked_order.count_in_order,
                    'date_created': booked_order.date_created.strftime('%d.%m.%Y') if booked_order.date_created else None
                })
            
            # Sort all holds by date
            hold_info.sort(key=lambda x: x['date_created'] if x['date_created'] else '9999-12-31', reverse=True)
            
            response_data = {
                'total_on_hold': supply.countOnHold,
                'total_pre_hold': supply.preCountOnHold,
                'holds': hold_info,
                'last_updated': timezone.now().strftime('%d.%m.%Y %H:%M')
            }
            
            return Response(response_data)
            
        except Supply.DoesNotExist:
            return Response(
                {'error': 'Supply not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefreshTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        try:
            # Create new JWT token
            jwt_token = create_jwt_token(request.user)
            return Response({
                'jwt_token': jwt_token,
                'message': 'Token refreshed successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user_serializer = UserSerializer(request.user)
        return Response(user_serializer.data)


@csrf_exempt
def telegram_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    webhook_secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
    if webhook_secret:
        header_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if header_secret != webhook_secret:
            return JsonResponse({'detail': 'Forbidden'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    try:
        async_to_sync(process_telegram_webhook)(payload)
    except Exception:
        return JsonResponse({'detail': 'Webhook processing failed'}, status=500)

    return JsonResponse({'ok': True}, status=200)