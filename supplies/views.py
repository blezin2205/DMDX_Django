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
from django.utils import timezone
from .filters import *
from django.urls import reverse_lazy
from django.http import Http404
from .forms import *
from django.contrib.auth.decorators import login_required
from bootstrap_modal_forms.generic import BSModalCreateView
from django.http import JsonResponse
import json
from django.forms import formset_factory, modelformset_factory, inlineformset_factory

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def deleteSupply(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    if action == 'delete':
      supp = Supply.objects.get(id=prodId)
      supp.delete()
    return JsonResponse('Item was added', safe=False)


def updateItem(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    print('Action', action)
    print('id', prodId)

    user = request.user
    supply = Supply.objects.get(id=prodId)
    order, created = OrderInCart.objects.get_or_create(userCreated=user, isComplete=False)

    try:
      suppInCart = SupplyInOrderInCart.objects.get(supply=supply, supply_for_order=order, lot=supply.supplyLot, date_expired=supply.expiredDate)
    except:
      suppInCart = SupplyInOrderInCart(
                                        supply=supply,
                                        supply_for_order=order,
                                        lot=supply.supplyLot,
                                        date_expired=supply.expiredDate,
                                        date_created=supply.dateCreated)

    if action == 'add':
        suppInCart.count_in_order = (suppInCart.count_in_order + 1)
    elif action == 'remove':
        suppInCart.count_in_order = (suppInCart.count_in_order - 1)

    suppInCart.save()

    if suppInCart.count_in_order <= 0:
        suppInCart.delete()


    return  JsonResponse('Item was added', safe=False)


def updateCartItem(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    print('Action', action)
    print('id', prodId)

    user = request.user
    suppInCart = SupplyInOrderInCart.objects.get(id=prodId)
    order, created = OrderInCart.objects.get_or_create(userCreated=user, isComplete=False)

    if action == 'add':
        suppInCart.count_in_order = (suppInCart.count_in_order + 1)
        suppInCart.save()
    elif action == 'remove':
        suppInCart.count_in_order = (suppInCart.count_in_order - 1)
        suppInCart.save()
    elif action == 'delete':
        suppInCart.delete()
        if SupplyInOrderInCart.objects.all().count() == 0:
            redirect('/')

    if suppInCart.count_in_order <= 0:
        suppInCart.delete()


    return  JsonResponse('Item was added', safe=False)


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

    supplies = GeneralSupply.objects.all().order_by('name')
    #
    # for gen in supplies:
    #    for sup in gen.general.all():
    #        sup.name = gen.name
    #        sup.ref = gen.ref
    #        sup.save(update_fields=['name', 'ref'])


    suppFilter = SupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    try:
        orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
        cart_items = orderInCart.get_cart_items
    except:
        orderInCart = None
        cart_items = 0

    if request.method == 'POST':
        supp = supplies.get(id=request.POST.get('supp_id'))
        supp.delete()


    return render(request, 'supplies/home.html', {'title': 'Всі товари', 'cart_items': cart_items, 'supplies': supplies,'suppFilter': suppFilter, 'isHome': True, 'isAll': True})


@login_required(login_url='login')
def cartDetail(request):

    orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
    cart_items = orderInCart.get_cart_items
    supplies = orderInCart.supplyinorderincart_set.all()
    orderForm = OrderInCartForm(request.POST or None)




    if request.method == 'POST':

        countList = request.POST.getlist('count_list')
        countListId = request.POST.getlist('count_list_id')

        if orderForm.is_valid():
            place = orderForm.cleaned_data['place']
            comment = orderForm.cleaned_data['comment']
            isComplete = orderForm.cleaned_data['isComplete']
            if isComplete:
                dateSent = timezone.now().date()
            else:
                dateSent = None
            order = Order(userCreated=orderInCart.userCreated, place=place, dateSent=dateSent, isComplete=isComplete, comment=comment)
            order.save()

            for index, sup in enumerate(supplies):
                suppInOrder = SupplyInOrder(count_in_order=countList[index], supply=sup.supply, generalSupply=sup.supply.general_supply, supply_for_order=order, lot=sup.lot, date_created=sup.date_created, date_expired=sup.date_expired)
                suppInOrder.save()
                supply = suppInOrder.supply
                try:
                 countOnHold = int(supply.countOnHold)
                except:
                 countOnHold = 0
                countInOrder = int(suppInOrder.count_in_order)
                supply.countOnHold = countOnHold + countInOrder
                supply.save(update_fields=['countOnHold'])
        orderInCart.delete()

        return redirect('/orders')


    return render(request, 'supplies/cart.html',
                  {'title': 'Корзина', 'order': orderInCart, 'cart_items': cart_items, 'supplies': supplies, 'orderForm': orderForm
                   })



@login_required(login_url='login')
def onlyGood(request):
    supplies = Supply.objects.filter(expiredDate__gte=timezone.now().date()).order_by('expiredDate')
    suppFilter = ChildSupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    try:
        orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
        cart_items = orderInCart.get_cart_items
    except:
        orderInCart = None
        cart_items = 0

    return render(request, 'supplies/homeChild.html',
                  {'title': 'Тільки придатні', 'supplies': supplies,  'cart_items': cart_items, 'suppFilter': suppFilter, 'isHome': True, 'isGood': True})


@login_required(login_url='login')
def onlyExpired(request):

    try:
        orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
        cart_items = orderInCart.get_cart_items
    except:
        orderInCart = None
        cart_items = 0

    supplies = Supply.objects.filter(expiredDate__lt=timezone.now().date()).order_by('-expiredDate')
    suppFilter = ChildSupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    return render(request, 'supplies/homeChild.html',
                  {'title': 'Тільки придатні', 'supplies': supplies,  'cart_items': cart_items, 'suppFilter': suppFilter, 'isHome': True, 'isExpired': True})



@login_required(login_url='login')
def orders(request):

    try:
        orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
        cart_items = orderInCart.get_cart_items
    except:
        orderInCart = None
        cart_items = 0

    orders = Order.objects.all().order_by('-id')
    return render(request, 'supplies/orders.html', {'title': 'Всі замовлення', 'orders': orders, 'cart_items': cart_items, 'isOrders': True})

@login_required(login_url='login')
def orderUpdateStatus(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']
    order = Order.objects.get(id=prodId)
    if action == 'update':
      supps = order.supplyinorder_set.all()
      for el in supps:
          countInOrder = el.count_in_order
          supp = el.supply
          supp.countOnHold -= countInOrder
          supp.count -= countInOrder
          supp.save(update_fields=['countOnHold', 'count'])
          if supp.count == 0:
              supp.delete()

      order.isComplete = True
      order.dateSent = timezone.now().date()
      order.save()

    elif action == 'delete':
        if not order.isComplete:
          supps = order.supplyinorder_set.all()
          for el in supps:
             countInOrder = el.count_in_order
             supp = el.supply
             supp.countOnHold -= countInOrder
             supp.save(update_fields=['countOnHold'])
        order.delete()

    return JsonResponse('Item was added', safe=False)


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


def updateSupply(request, supp_id):
    note = Supply.objects.get(id=supp_id)
    form = SupplyForm(instance=note)
    if request.method == 'POST':
        form = SupplyForm(request.POST, instance=note)
        if form.is_valid():
            # obj = form.save(commit=False)
            # obj.from_user = User.objects.get(pk=request.user.id)
            form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Редагувати запис №{supp_id}', 'form': form})


def updateGeneralSupply(request, supp_id):
    supp = GeneralSupply.objects.get(id=supp_id)
    form = GeneralSupplyForm(instance=supp)
    if request.method == 'POST':
        form = GeneralSupplyForm(request.POST, instance=supp)
        if form.is_valid():
            # obj = form.save(commit=False)
            # obj.from_user = User.objects.get(pk=request.user.id)
            form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Редагувати запис №{supp_id}', 'form': form})



def addNewLotforSupply(request, supp_id):
    generalSupp = GeneralSupply.objects.get(id=supp_id)
    form = SupplyForm()
    if request.method == 'POST':
        form = SupplyForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.general_supply = generalSupp
            obj.category = generalSupp.category
            obj.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати новий LOT для {generalSupp.name}', 'form': form})



def addgeneralSupply(request):
    form = NewSupplyForm()
    if request.method == 'POST':
        form = NewSupplyForm(request.POST)
        if form.is_valid():
            try:
                genSupp = GeneralSupply.objects.get(name=form.cleaned_data['name'].strip())
            except:
                genSupp = GeneralSupply(name=form.cleaned_data['name'].strip(), ref=form.cleaned_data['ref'].strip(), category=form.cleaned_data['category'])
            genSupp.save()
            obj = form.save(commit=False)
            obj.general_supply = genSupp
            obj.save()
            # form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати новий товар (назву)', 'form': form})



def addNewClient(request):
    form = ClientForm()
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/clientsInfo')
    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати нового клієнта', 'form': form})


def addNewWorkerForClient(request, place_id):
    form = WorkerForm()
    place = Place.objects.get(id=place_id)
    if request.method == 'POST':
        form = WorkerForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.for_place = place
            obj.save()
            return redirect('/clientsInfo')
    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати нового працівника для {place.name}, {place.city}', 'form': form})




def deleteServiceNote(request, note_id):
    note = ServiceNote.objects.get(id=note_id)
    if request.method == 'POST':
        note.delete()
    return redirect('/serviceNotes')




@login_required(login_url='login')
def orderDetail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

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

