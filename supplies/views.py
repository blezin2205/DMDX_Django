from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from .decorators import unauthenticated_user, allowed_users
from .models import *
from .serializers import *
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from django.contrib.auth import authenticate, login, logout
from rest_framework import renderers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime
from .filters import *
from django.urls import reverse_lazy
from django.http import Http404
from .forms import *
from django.contrib.auth.decorators import login_required
from bootstrap_modal_forms.generic import BSModalCreateView
import requests

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def registerPage(request):
    if request.user.is_authenticated:
        return redirect('/')
    else:
        form = CreateUserForm()
        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                form.save()

        context = {'form': form}
    return render(request, 'auth/register.html', context)

@unauthenticated_user
def loginPage(request):
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
             login(request, user)
             return redirect('/')

        return render(request, 'auth/login.html')

@login_required(login_url='login')
def logoutUser(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def home(request):
    # supplies = []
    # docs = db.collection(u'supplies').stream()
    # for index, doc in enumerate(docs):
    #     name = doc.to_dict()['name']
    #     device = doc.to_dict()['device']
    #     supply_lot = doc.to_dict()['supplyLot']
    #     count = doc.to_dict()['count']
    #     date_created = doc.to_dict()['dateCreated']
    #     expired_date = doc.to_dict()['expiredDate']
    #
    #     try:
    #         cat = Category.objects.get(name=device)
    #     except Category.DoesNotExist:
    #         cat = None
    #     if not supply_lot:
    #      supply_lot = None
    #
    #     if count < 0:
    #        count = 0
    #
    #     supp = Supply(firebase_id=doc.id, name=name, category=cat, supplyLot=supply_lot, count=count, dateCreated=date_created, expiredDate=expired_date)
    #     supp.save()


    supplies = Supply.objects.exclude(count__exact=0).order_by('name')

    suppFilter = SupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    return render(request, 'supplies/home.html', {'title': 'Всі товари', 'supplies': supplies,'suppFilter': suppFilter, 'isHome': True, 'isAll': True})


@login_required(login_url='login')
def orders(request):
    orders = Order.objects.all().order_by('-id')
    return render(request, 'supplies/orders.html', {'title': 'Всі замовлення', 'orders': orders, 'isOrders': True})


@login_required(login_url='login')
def ordersForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    orders = place.order_set.all()
    title = f'Всі замовлення для клієнта: \n {place.name}, {place.city}'
    if not orders:
        title = f'В клієнта "{place.name}, {place.city}" ще немає замовлень'

    return render(request, 'supplies/orders.html', {'title': title, 'orders': orders, 'isClients': True})


@login_required(login_url='login')
def serviceNotesForClient(request, client_id):
    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = User.objects.get(pk=request.user.id)
            obj.save()
            return HttpResponseRedirect(request.path_info)

    place = get_object_or_404(Place, pk=client_id)
    serviceNotes = place.servicenote_set.all()
    title = f'Всі сервісні замітки для клієнта: \n {place.name}, {place.city}'
    return render(request, 'supplies/serviceNotes.html',
                  {'title': title, 'serviceNotes': serviceNotes, 'form': form, 'isClients': True})



def createNote(request):
    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = User.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    return render(request, 'supplies/createNote.html',
                  {'title': f'Створити новий запис', 'form': form,
                   'isService': True})


def updateNote(request, note_id):
    note = ServiceNote.objects.get(id=note_id)
    form = ServiceNoteForm(instance=note)
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST, instance=note)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = User.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    return render(request, 'supplies/createNote.html',
                  {'title': f'Редагувати запис №{note_id}', 'form': form,
                    'isService': True})


def deleteServiceNote(request, note_id):
    note = ServiceNote.objects.get(id=note_id)
    if request.method == 'POST':
        note.delete()
    return redirect('/serviceNotes')




@login_required(login_url='login')
def orderDetail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplies.all()

    print(supplies_in_order.first())
    return render(request, 'supplies/orderDetail.html', {'title': f'Замовлення № {order_id}', 'order': order, 'supplies': supplies_in_order, 'isOrders': True})


@login_required(login_url='login')
def clientsInfo(request):
    place = Place.objects.all().order_by('-id')
    return render(request, 'supplies/clientsList.html',
                  {'title': f'Клієнти', 'clients': place, 'isClients': True})


@login_required(login_url='login')
def serviceNotes(request):

    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = User.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    serviceNotes = ServiceNote.objects.all().order_by('-id')
    serviceFilters = ServiceNotesFilter(request.GET, queryset=serviceNotes)
    serviceNotes = serviceFilters.qs

    return render(request, 'supplies/serviceNotes.html',
                   {'title': f'Сервiсні записи', 'serviceNotes': serviceNotes, 'form': form, 'serviceFilters': serviceFilters, 'isService': True})



class NoteCreateView(BSModalCreateView):
    template_name = 'supplies/createNote.html'
    form_class = ServiceNoteForm
    success_message = 'Success: Book was created.'
    success_url = reverse_lazy('supplies/serviceNotes.html')


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