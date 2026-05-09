from .serializers import *

from rest_framework import renderers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Sum, Min, Prefetch, Value, IntegerField, F
from django.db.models.functions import Coalesce
from django.http import Http404
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
from .NPViews import get_np_delivery_details
from .views import update_order_status_core
from .tasks import makeDataUpload_nonCelery
from math import ceil
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync

from .dmdx_telegram_bot import process_telegram_webhook


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


class GeneralSuppliesApiView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        supplies = GeneralSupply.objects.all()
        paginator = self.pagination_class()
        paginated_supplies = paginator.paginate_queryset(supplies, request)
        if paginated_supplies is None:
            return Response({'error': 'Invalid page'}, status=status.HTTP_404_NOT_FOUND)
        suppliesSerializer = GeneralSupplySerializer(instance=paginated_supplies, many=True)
        return paginator.get_paginated_response(suppliesSerializer.data)


class SuppliesApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supplies = Supply.objects.all()
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
        if expired_only:
            queryset = queryset.filter(general__expiredDate__lt=timezone.now().date())

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
        page_queryset = queryset[start:end].prefetch_related(
            Prefetch('general', queryset=Supply.objects.select_related('general_supply').order_by('expiredDate', 'id'))
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
            return Response({'items': [], 'total_items': 0, 'total_rows': 0}, status=status.HTTP_200_OK)

        items = cart.supplyinorderincart_set.select_related('supply__general_supply').all()
        payload = []
        total_items = 0

        for item in items:
            supply = item.supply
            if not supply:
                continue
            count = int(item.count_in_order or 0)
            total_items += count
            payload.append({
                'id': item.id,
                'supply_id': supply.id,
                'general_supply_id': supply.general_supply_id,
                'name': supply.general_supply.name if supply.general_supply else supply.name,
                'lot': item.lot,
                'count': count,
                'expiredDate': item.date_expired,
                'available': supply.count,
                'on_hold': supply.countOnHold,
            })

        return Response({
            'items': payload,
            'total_items': total_items,
            'total_rows': len(payload),
        }, status=status.HTTP_200_OK)


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


class DesktopCartCheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]

    @transaction.atomic
    def post(self, request):
        cart = OrderInCart.objects.filter(userCreated=request.user, isComplete=False).first()
        if not cart:
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        items = cart.supplyinorderincart_set.select_related('supply__general_supply').all()
        if not items.exists():
            return Response({'error': 'Cart has no items'}, status=status.HTTP_400_BAD_REQUEST)

        place_id = request.data.get('place_id')
        comment = request.data.get('comment')
        is_complete = _as_bool(request.data.get('isComplete', False))
        is_pinned = _as_bool(request.data.get('isPinned', False))
        date_to_send = request.data.get('dateToSend')

        place = None
        if place_id:
            place = Place.objects.filter(id=place_id).first()
        if not place:
            place = Place.objects.filter(user=request.user).first()
        if not place:
            return Response({'error': 'Place is required for checkout'}, status=status.HTTP_400_BAD_REQUEST)

        date_sent = timezone.now().date() if is_complete else None

        order = Order.objects.create(
            userCreated=request.user,
            place=place,
            dateSent=date_sent,
            isComplete=is_complete,
            isPinned=is_pinned,
            comment=comment,
            dateToSend=date_to_send or None,
        )

        for item in items:
            if not item.supply:
                continue

            count_in_order = int(item.count_in_order or 0)
            supp_in_order = SupplyInOrder.objects.create(
                count_in_order=count_in_order,
                supply=item.supply,
                generalSupply=item.supply.general_supply,
                supply_for_order=order,
                lot=item.lot,
                date_created=item.date_created,
                date_expired=item.date_expired,
                internalName=item.supply.general_supply.name if item.supply.general_supply else item.supply.name,
                internalRef=item.supply.general_supply.ref if item.supply.general_supply else item.supply.ref,
            )

            supply = supp_in_order.supply
            if not supply:
                continue

            if is_complete:
                supply.count = max(int(supply.count or 0) - count_in_order, 0)
                if supply.count == 0:
                    supply.delete()
                else:
                    supply.save(update_fields=['count'])
            else:
                supply.countOnHold = int(supply.countOnHold or 0) + count_in_order
                supply.save(update_fields=['countOnHold'])

        cart.delete()

        return Response({
            'success': True,
            'order_id': order.id,
            'isComplete': is_complete,
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
            .select_related('supply_for_order__place')
            .order_by('-id')[:60]
        )
        in_preorders = (
            general_supply.supplyinpreorder_set.all()
            .select_related('supply_for_order__place')
            .order_by('-id')[:60]
        )
        in_deliveries = general_supply.deliverysupplyincart_set.all().order_by('-id')[:60]
        in_booked = (
            general_supply.supplyinbookedorder_set.all()
            .select_related('supply_for_place')
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
            },
            'orders': [
                {
                    'id': item.id,
                    'order_id': item.supply_for_order.id if item.supply_for_order else None,
                    'place': item.supply_for_order.place.name if item.supply_for_order and item.supply_for_order.place else None,
                    'count': item.count_in_order,
                    'lot': item.lot,
                    'date_expired': to_date(item.date_expired),
                    'date_created': to_date(item.date_created),
                }
                for item in in_orders
            ],
            'preorders': [
                {
                    'id': item.id,
                    'preorder_id': item.supply_for_order.id if item.supply_for_order else None,
                    'place': item.supply_for_order.place.name if item.supply_for_order and item.supply_for_order.place else None,
                    'count': item.count_in_order,
                    'state': item.state_of_delivery,
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
                    'count': item.count_in_order,
                    'lot': item.lot,
                    'date_expired': to_date(item.date_expired),
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
            genSup = GeneralSupply.objects.filter(general__isnull=False).filter(Q(name__icontains=searchtext) | Q(ref__icontains=searchtext) | Q(SMN_code__icontains=searchtext)).distinct()
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


class SuppliesInOrderView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    
    def get(self, request, order_id):
        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        items = (
            SupplyInOrder.objects.filter(supply_for_order=order)
            .select_related('supply', 'generalSupply')
            .order_by('id')
        )

        payload = []
        for item in items:
            fallback_name = item.internalName
            if not fallback_name and item.generalSupply:
                fallback_name = item.generalSupply.name
            if not fallback_name and item.supply and item.supply.general_supply:
                fallback_name = item.supply.general_supply.name

            fallback_ref = item.internalRef
            if not fallback_ref and item.generalSupply:
                fallback_ref = item.generalSupply.ref
            if not fallback_ref and item.supply and item.supply.general_supply:
                fallback_ref = item.supply.general_supply.ref

            payload.append(
                {
                    'name': fallback_name,
                    'ref': fallback_ref,
                    'lot': item.lot,
                    'dateCreated': item.date_created.strftime('%d-%m-%Y') if item.date_created else None,
                    'expiredDate': item.date_expired.strftime('%d-%m-%Y') if item.date_expired else None,
                    'countInOrder': item.count_in_order,
                }
            )

        return Response(payload)


class OrdersApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    
    def get(self, request):
        orders = (
            Order.objects.select_related('place', 'place__city_ref', 'userCreated', 'userSent')
            .prefetch_related('statusnpparselfromdoucmentid_set', 'npdeliverycreateddetailinfo_set')
            .order_by('-isPinned', '-id')
        )

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

        payload = []
        for order in page_orders:
            np_statuses = order.statusnpparselfromdoucmentid_set.all()
            top_status = np_statuses.first()
            payload.append({
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
                    'has_documents': order.npdeliverycreateddetailinfo_set.exists(),
                    'documents_count': order.npdeliverycreateddetailinfo_set.count(),
                    'status_code': top_status.status_code if top_status else None,
                    'status_desc': top_status.status_desc if top_status else None,
                    'statuses_count': np_statuses.count(),
                },
            })

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
            .select_related('place', 'place__city_ref')
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
                'dateCreated': order.dateCreated.strftime('%d-%m-%Y') if order.dateCreated else None,
                'dateSent': order.dateSent.strftime('%d-%m-%Y') if order.dateSent else None,
                'dateToSend': order.dateToSend.strftime('%d-%m-%Y') if order.dateToSend else None,
                'comment': order.comment,
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

    def post(self, request, order_id):
        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        parsels_status_data, no_more_update = get_np_delivery_details(order)
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
        
        # Create JWT token for the new user
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
            orders_with_supply = supply.inSupply.filter(supply_for_order__isComplete=False)
            
            # Add regular orders info
            for order in orders_with_supply:
                hold_info.append({
                    'type': 'order',
                    'order_id': order.supply_for_order.id,
                    'sup_in_order_id': order.id,
                    'place_name': order.supply_for_order.place.name,
                    'count': order.count_in_order,
                    'date_created': order.supply_for_order.dateCreated.strftime('%d.%m.%Y') if order.supply_for_order.dateCreated else None
                })
            
            # Get booked orders that have this supply on hold
            booked_orders_with_supply = supply.supplyinbookedorder_set.all()
            print("booked_orders_with_supply", booked_orders_with_supply)
            
            # Add booked orders info
            for booked_order in booked_orders_with_supply:
                hold_info.append({
                    'type': 'booked',
                    'place_name': booked_order.supply_for_place.name,
                    'order_id': booked_order.supply_for_place.id,
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