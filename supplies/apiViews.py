
from .serializers import *

from rest_framework import renderers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.http import Http404
from .forms import *



class GeneralSuppliesApiView(APIView):

    def get(self, request):
        supplies = GeneralSupply.objects.all()
        suppliesSerializer = GeneralSupplySerializer(instance=supplies, many=True)
        return Response(suppliesSerializer.data)


class SuppliesApiView(APIView):

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
    def get(self, request, order_id):
        order = Order.objects.get(id=order_id)
        suppInOrder = order.supplies
        suppInOrderSerializer = SupplyInOrderSerializer(instance=suppInOrder, many=True)
        return Response(suppInOrderSerializer.data)


class OrdersApiView(APIView):
    def get(self, request):
        orders = Order.objects.all()
        ordersSerializer = OrderSerializer(instance=orders, many=True)
        return Response(ordersSerializer.data)


class PlacesApiView(APIView):
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
        serializer.save()

        return Response(
            {
                'token': serializer.data.get('token', None),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    """
    Logs in an existing user.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        """
        Checks is user exists.
        Email and password are required.
        Returns a JSON web token.
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)