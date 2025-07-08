from .serializers import *

from rest_framework import renderers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.http import Http404
from .forms import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login
from django.utils import timezone
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.pagination import PageNumberPagination


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
    
    def get(self, request, order_id):
        order = Order.objects.get(id=order_id)
        suppInOrder = order.supplies
        suppInOrderSerializer = SupplyInOrderSerializer(instance=suppInOrder, many=True)
        return Response(suppInOrderSerializer.data)


class OrdersApiView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        orders = Order.objects.all()
        ordersSerializer = OrderSerializer(instance=orders, many=True)
        return Response(ordersSerializer.data)


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