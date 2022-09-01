import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse

from .decorators import unauthenticated_user, allowed_users
from .models import *
from .serializers import *
from datetime import date
from dateutil.relativedelta import relativedelta
from django.contrib.auth import authenticate, login, logout
from .filters import *
from .forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.core.paginator import Paginator

from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import os
from xlsxwriter.workbook import Workbook
from django_htmx.http import trigger_client_event
from django.contrib import messages
import requests
import pandas

async def httpRequest(request):

        param = {'apiKey': '99f738524ca3320ece4b43b10f4181b1',
                'modelName': 'Counterparty',
             'calledMethod': 'getCounterpartyContactPersons',
             'methodProperties': {'Ref': '3b0e7317-2a6b-11eb-8513-b88303659df5'}}

        getListOfCitiesParams = {
             "apiKey": "99f738524ca3320ece4b43b10f4181b1",
             "modelName": "Address",
             "calledMethod": "getCities",
             "methodProperties": {
             "Page" : "0"
               }
            }

        data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(param)).json()
        cityData = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(getListOfCitiesParams)).json()
        cityDataCount = cityData["data"]
        cities = []
        for city in cityDataCount:
            cityName = city["Description"]
            cities.append(City(name=cityName))
            print(cityName)

        print(len(cities))




        return render(request, "supplies/http_response.html", {'data': data["data"]})

def fetchxmls():

    print('Hello')

    # excel_data_df = pandas.read_excel('/Users/macbook/Documents/DIAMEDIX/centaur_list.xlsx', header=None, index_col=None)
    # wb = excel_data_df
    # vals = wb.values
    # for obj in vals:
    #     ref = obj[0]
    #     smn = str(obj[2]).removesuffix('.0')
    #     name = str(obj[3]).removeprefix('ADVIA Centaur ')
    #     packed = obj[4]
    #     # tests = obj[5]
    #     # tests = obj[5]
    #     if name != 'nan':
    #         print(ref, smn, name, packed)
    #         genSup = GeneralSupply(name=name, ref=ref, SMN_code=smn, package_and_tests=packed, category_id=3)
    #         genSup.save()





def countCartItemsHelper(request):
    try:
        orderInCart = OrderInCart.objects.first()
        cart_items = orderInCart.get_cart_items
    except:
        cart_items = 0
    try:
        precart_items = PreorderInCart.objects.get(userCreated=request.user, isComplete=False).get_cart_items
    except:
        precart_items = 0
    try:
        isClient = request.user.groups.filter(name='client').exists()
        if isClient:
           orders_incomplete = Order.objects.filter(isComplete=False, place__user=request.user).count()
        else:
           orders_incomplete = Order.objects.filter(isComplete=False).count()
    except:
        orders_incomplete = 0
    try:
        isClient = request.user.groups.filter(name='client').exists()
        if isClient:
            preorders_incomplete = PreOrder.objects.filter(isComplete=False, place__user=request.user).count()
        else:
            preorders_incomplete = PreOrder.objects.filter(isComplete=False).count()
    except:
        preorders_incomplete = 0

    return  {'cart_items': cart_items, 'precart_items': precart_items, 'orders_incomplete': orders_incomplete, 'preorders_incomplete': preorders_incomplete}


def countOnHoldMake(request):
    supps = Supply.objects.all()

    for supp in supps:
        if not supp.countOnHold:
            supp.countOnHold = 0
            supp.save(update_fields=['countOnHold'])

    return redirect('/')



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteSupply(request, suppId):
    prodId = suppId

    supp = Supply.objects.get(id=prodId)
    supp.delete()

    next = request.POST.get('nextDelete')
    print(next)
    return HttpResponseRedirect(next)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteSupplyInOrder(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    if action == 'delete':
        suppInOrder = SupplyInOrder.objects.get(id=prodId)
        if suppInOrder.hasSupply():
            supp_for_supp_in_order = suppInOrder.supply
            supp_for_supp_in_order.countOnHold -= suppInOrder.count_in_order
            supp_for_supp_in_order.save(update_fields=['countOnHold'])
        suppInOrder.delete()

    elif action == 'delete-preorder':
        suppInOrder = SupplyInPreorder.objects.get(id=prodId)
        suppInOrder.delete()


    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def preorder_general_supp_buttons(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    print('Action', action)
    print('id', prodId)

    user = request.user

    if action == 'add':
        supply = Supply.objects.get(id=prodId)
        preorder, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)
        suppInCart = SupplyInPreorderInCart(
                supply=supply,
                supply_for_order=preorder,
                lot=supply.supplyLot,
                date_expired=supply.expiredDate,
                date_created=supply.dateCreated)

        suppInCart.count_in_order = (suppInCart.count_in_order + 1)
        suppInCart.save()

    elif action == 'add-general':
        general_supply = GeneralSupply.objects.get(id=prodId)

        preorder, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)
        suppInCart = SupplyInPreorderInCart(id=general_supply.id,
                supply_for_order=preorder,
                general_supply=general_supply)

        suppInCart.count_in_order = (suppInCart.count_in_order + 1)
        suppInCart.save()

    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def preorder_general_supp_buttons(request, prodId):
    user = request.user

    supply = Supply.objects.get(id=prodId)
    preorder, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)
    suppInCart = SupplyInPreorderInCart(
                supply=supply,
                supply_for_order=preorder,
                lot=supply.supplyLot,
                date_expired=supply.expiredDate,
                date_created=supply.dateCreated)

    suppInCart.count_in_order = (suppInCart.count_in_order + 1)
    suppInCart.save()

    # elif action == 'add-general':
    #     general_supply = GeneralSupply.objects.get(id=prodId)
    #
    #     preorder, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)
    #     suppInCart = SupplyInPreorderInCart(id=general_supply.id,
    #             supply_for_order=preorder,
    #             general_supply=general_supply)
    #
    #     suppInCart.count_in_order = (suppInCart.count_in_order + 1)
    #     suppInCart.save()

    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def preorder_supp_buttons(request, supp_id):
    user = request.user
    print(supp_id)

    supply = Supply.objects.get(id=supp_id)
    preorder, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)

    try:
        suppInCart = SupplyInPreorderInCart.objects.get(supply=supply, supply_for_order=preorder, lot=supply.supplyLot)

    except:

        suppInCart = SupplyInPreorderInCart(
            supply=supply,
            supply_for_order=preorder,
            lot=supply.supplyLot,
            date_expired=supply.expiredDate,
            date_created=supply.dateCreated)

    suppInCart.count_in_order = (suppInCart.count_in_order + 1)
    suppInCart.save()

    countInPreCart = suppInCart.count_in_order
    response = render(request, 'partials/add_precart_button.html', {'countInPreCart': countInPreCart, 'supp': supply})
    trigger_client_event(response, 'subscribe_precart', {})
    return response


@login_required(login_url='login')
def updateItem(request, supp_id):

    user = request.user
    supply = Supply.objects.get(id=supp_id)

    order, created = OrderInCart.objects.get_or_create(userCreated=user, isComplete=False)

    try:
        suppInCart = SupplyInOrderInCart.objects.get(id=supp_id,supply=supply, supply_for_order=order, lot=supply.supplyLot,
                                                     date_expired=supply.expiredDate)
    except:
        suppInCart = SupplyInOrderInCart(id=supp_id,
            supply=supply,
            supply_for_order=order,
            lot=supply.supplyLot,
            date_expired=supply.expiredDate,
            date_created=supply.dateCreated)

    suppInCart.count_in_order = (suppInCart.count_in_order + 1)
    suppInCart.save()

    if suppInCart.count_in_order <= 0:
        suppInCart.delete()

    try:
        orderInCart = OrderInCart.objects.first()
        cart_items = orderInCart.get_cart_items
    except:
        cart_items = 0

    cartCountData = {'cart_items': cart_items}
    deltaCountOnHold = supply.count - supply.countOnHold == 0
    countInCart = suppInCart.count_in_order
    deltaCountOnCart = supply.count - supply.countOnHold - countInCart == 0
    response = render(request, 'partials/add_cart_button.html', {'cartCountData': cartCountData, 'supp': supply, 'deltaCount': deltaCountOnHold, 'countInCart': countInCart, 'deltaCountOnCart': deltaCountOnCart})
    trigger_client_event(response, 'subscribe', {})
    return response

def updateCartItemCount(request):
    cartCountData = countCartItemsHelper(request)
    return render(request, 'partials/cart-badge.html', {'cartCountData': cartCountData})

def updatePreCartItemCount(request):
    cartCountData = countCartItemsHelper(request)
    return render(request, 'partials/precart-badge.html', {'cartCountData': cartCountData})


@login_required(login_url='login')
def update_order_count(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    print('Action', action)
    print('id', prodId)

    if action == 'add':
        supply = SupplyInOrder.objects.get(id=prodId)
        supply.count_in_order = (supply.count_in_order + 1)
        supply.supply.countOnHold += 1
        supply.supply.save()
        supply.save()

        if supply.count_in_order <= 0:
            supply.delete()
    elif action == 'remove':
        supply = SupplyInOrder.objects.get(id=prodId)
        supply.count_in_order = (supply.count_in_order - 1)
        supply.supply.countOnHold -= 1
        supply.supply.save()
        supply.save()

        if supply.count_in_order <= 0:
            supply.delete()
    elif action == 'add-preorder':
        supp_preorder = SupplyInPreorder.objects.get(id=prodId)
        supp_preorder.count_in_order = (supp_preorder.count_in_order + 1)
        supp_preorder.save()
        if supp_preorder.count_in_order <= 0:
            supp_preorder.delete()

    elif action == 'remove-preorder':
        supp_preorder = SupplyInPreorder.objects.get(id=prodId)
        supp_preorder.count_in_order = (supp_preorder.count_in_order - 1)
        supp_preorder.save()
        if supp_preorder.count_in_order <= 0:
            supp_preorder.delete()

    return  JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def updateCartItem(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    print('Action', action)
    print('id', prodId)
    user = request.user
    isLastItemInCart = False

    if action == 'delete-precart':
        order = PreorderInCart.objects.get(userCreated=user, isComplete=False)
        suppInCart = SupplyInPreorderInCart.objects.get(id=prodId, supply_for_order=order)
        suppInCart.delete()
        isLastItemInCart = SupplyInPreorderInCart.objects.filter(supply_for_order=order).count() == 0
        if isLastItemInCart:
            order.delete()
    elif action == 'delete':
        order = OrderInCart.objects.first()
        suppInCart = SupplyInOrderInCart.objects.get(id=prodId, supply_for_order=order)
        suppInCart.delete()
        isLastItemInCart = SupplyInOrderInCart.objects.count() == 0
        if isLastItemInCart:
            order.delete()

    return JsonResponse({'isLastItemInCart': isLastItemInCart}, safe=False)


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


    fetchxmls()

    uncompleteOrdersExist = Order.objects.filter(isComplete=False).exists()
    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
       uncompletePreOrdersExist = PreOrder.objects.filter(isComplete=False, place__user=request.user).exists()
    else:
        uncompletePreOrdersExist = PreOrder.objects.filter(isComplete=False).exists()

    suppFilter = SupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    paginator = Paginator(supplies, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':
        supp = supplies.get(id=request.POST.get('supp_id'))
        supp.delete()

    return render(request, 'supplies/home.html', {'title': 'Всі товари',
                                                  'cartCountData': cartCountData,
                                                  'supplies': page_obj,'suppFilter': suppFilter,
                                                  'isHome': True,
                                                  'isAll': True,
                                                  'uncompleteOrdersExist': uncompleteOrdersExist,
                                                  'uncompletePreOrdersExist': uncompletePreOrdersExist})


@login_required(login_url='login')
def cartDetailForClient(request):
    orderInCart = PreorderInCart.objects.get(userCreated=request.user, isComplete=False)
    cartCountData = countCartItemsHelper(request)
    supplies = orderInCart.supplyinpreorderincart_set.all()
    orderForm = OrderInCartForm(request.POST or None)

    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        orderForm.fields['place'].queryset = Place.objects.filter(user=request.user)

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
            order = PreOrder(userCreated=orderInCart.userCreated, place=place, dateSent=dateSent, isComplete=isComplete, comment=comment)
            order.save()

            for index, sup in enumerate(supplies):
                if sup.supply:
                    general_sup = sup.supply.general_supply
                    suppInOrder = SupplyInPreorder(count_in_order=countList[index],
                                                   generalSupply=sup.supply.general_supply,
                                                   supply=sup.supply,
                                                   supply_for_order=order, lot=sup.lot,
                                                   date_created=sup.date_created,
                                                   date_expired=sup.date_expired)
                    suppInOrder.save()
                elif sup.general_supply:
                    general_sup = sup.general_supply
                    suppInOrder = SupplyInPreorder(count_in_order=countList[index],
                                                   generalSupply=general_sup,
                                                   supply_for_order=order, lot=sup.lot,
                                                   date_created=sup.date_created,
                                                   date_expired=sup.date_expired)
                    suppInOrder.save()


        orderInCart.delete()

        return redirect('/preorders')

    return render(request, 'supplies/preorder-cart.html',
                  {'title': 'Корзина передзамовлення', 'order': orderInCart, 'cartCountData': cartCountData, 'supplies': supplies,
                   'orderForm': orderForm
                   })

@login_required(login_url='login')
def carDetailForStaff(request):
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
            order = Order(userCreated=orderInCart.userCreated, place=place, dateSent=dateSent, isComplete=isComplete,
                          comment=comment)
            order.save()

            for index, sup in enumerate(supplies):
                suppInOrder = SupplyInOrder(count_in_order=countList[index],
                                            supply=sup.supply,
                                            generalSupply=sup.supply.general_supply,
                                            supply_for_order=order, lot=sup.lot,
                                            date_created=sup.date_created,
                                            date_expired=sup.date_expired,
                                            internalName=sup.supply.general_supply.name,
                                            internalRef=sup.supply.general_supply.ref)
                suppInOrder.save()
                supply = suppInOrder.supply
                try:
                    countOnHold = int(supply.countOnHold)
                except:
                    countOnHold = 0
                countInOrder = int(suppInOrder.count_in_order)
                if isComplete:
                    supply.count -= countInOrder
                    supply.save(update_fields=['count'])
                else:
                    if supply.countOnHold:
                        supply.countOnHold = countOnHold + countInOrder
                        supply.save(update_fields=['countOnHold'])
                    else:
                        supply.countOnHold = 0
                        supply.save(update_fields=['countOnHold'])
                        supply.countOnHold = countOnHold + countInOrder
                        supply.save(update_fields=['countOnHold'])

        orderInCart.delete()

        return redirect('/orders')

    return render(request, 'supplies/cart.html',
                  {'title': 'Корзина', 'order': orderInCart, 'cart_items': cart_items, 'supplies': supplies,
                   'orderForm': orderForm
                   })


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_np_sender_place(request):
    user = request.user

    if request.method == 'POST':
        cityName = request.POST.get('cityName')
        addressName = request.POST.get('streetName')
        cityRef = request.POST.get('np-cityref')
        addressRef = request.POST.get('np-streetRef')
        streetNumber = request.POST.get('streetNumber')
        flatNumber = request.POST.get('flatNumber')
        comment = request.POST.get('comment')
        recipientType = request.POST.get('recipientType')

        deliveryPlace = SenderNPPlaceInfo(cityName=cityName, addressName=addressName, city_ref_NP=cityRef,
                                      address_ref_NP=addressRef, deliveryType=recipientType, for_user=user)
        deliveryPlace.save()
        return redirect('/')

    return  render(request, 'supplies/add_new_sender_np_place.html', {})




@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def cartDetail(request):

    orderInCart = OrderInCart.objects.first()
    cartCountData = countCartItemsHelper(request)
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
                suppInOrder = SupplyInOrder(count_in_order=countList[index],
                                            supply=sup.supply,
                                            generalSupply=sup.supply.general_supply,
                                            supply_for_order=order, lot=sup.lot,
                                            date_created=sup.date_created,
                                            date_expired=sup.date_expired,
                                            internalName=sup.supply.general_supply.name,
                                            internalRef=sup.supply.general_supply.ref)
                suppInOrder.save()
                supply = suppInOrder.supply
                try:
                 countOnHold = int(supply.countOnHold)
                except:
                 countOnHold = 0
                countInOrder = int(suppInOrder.count_in_order)
                if isComplete:
                    supply.count -= countInOrder
                    supply.save(update_fields=['count'])
                else:
                    if supply.countOnHold:
                         supply.countOnHold = countOnHold + countInOrder
                         supply.save(update_fields=['countOnHold'])
                    else:
                        supply.countOnHold = 0
                        supply.save(update_fields=['countOnHold'])
                        supply.countOnHold = countOnHold + countInOrder
                        supply.save(update_fields=['countOnHold'])


        orderInCart.delete()

        return redirect('/orders')


    return render(request, 'supplies/cart.html',
                  {'title': 'Корзина', 'order': orderInCart, 'cartCountData': cartCountData, 'supplies': supplies, 'orderForm': orderForm
                   })


@login_required(login_url='login')
def childSupply(request):
    supplies = Supply.objects.all().order_by('name')
    suppFilter = ChildSupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    try:
        orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
        cart_items = orderInCart.get_cart_items
    except:
        orderInCart = None
        cart_items = 0

    if request.GET.get('xls_button'):

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f"attachment; filename=Supply_List.xlsx"

        row_num = 3

        wb = Workbook(response, {'in_memory': True})
        ws = wb.add_worksheet('Supply-List')
        format = wb.add_format({'bold': True})
        format.set_font_size(16)

        columns_table = [{'header': '№'},
                         {'header': 'Назва товару'},
                         {'header': 'REF'},
                         {'header': 'LOT'},
                         {'header': 'К-ть'},
                         {'header': 'Тер.прид.'},
                         {'header': 'Категорія'},
                         ]

        ws.write(0, 0,
                 f'Загальний список товарів',
                 format)

        format = wb.add_format({'num_format': 'dd.mm.yyyy'})
        format.set_font_size(12)

        for row in supplies:
            row_num += 1
            name = row.general_supply.name
            ref = ''
            if row.general_supply.ref:
                ref = row.general_supply.ref
            lot = ''
            if row.supplyLot:
                lot = row.supplyLot
            count = row.count
            date_expired = row.expiredDate.strftime("%d.%m.%Y")
            category = row.general_supply.category.name

            val_row = [name, ref, lot, count, date_expired, category]

            for col_num in range(len(val_row)):
                ws.write(row_num, 0, row_num - 3)
                ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 35)
        ws.set_column(2, 3, 15)
        ws.set_column(4, 4, 10)
        ws.set_column(5, 5, 10)
        ws.set_column(6, 6, 12)

        ws.add_table(3, 0, suppFilter.qs.count() + 3, len(columns_table) - 1, {'columns': columns_table})
        wb.close()
        return response

    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/homeChild.html',
                  {'title': 'Дочерні товари', 'supplies': supplies,  'cartCountData': cartCountData, 'suppFilter': suppFilter, 'isHome': True, 'isChild': True})


@login_required(login_url='login')
def orders(request):
    cartCountData = countCartItemsHelper(request)

    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        orders = Order.objects.filter(place__user=request.user).order_by('-id')
        title = f'Всі замовлення для {request.user.first_name} {request.user.last_name} '
    else:
        orders = Order.objects.all().order_by('-id')
        title = 'Всі замовлення'

    if request.method == 'POST':
        selected_orders = request.POST.getlist('flexCheckDefault')
        print("------ ", selected_orders, "-----------")
        selected_ids = map(int, selected_orders)
        fileteredOredrs = Order.objects.filter(pk__in=selected_ids)
        documentsIdFromOrders = fileteredOredrs.values_list('npdeliverycreateddetailinfo__ref', flat=True)
        listToStr = ','.join(map(str, documentsIdFromOrders))
        print(listToStr)

        if 'print_choosed' in request.POST:
            np_link_print = f'https://my.novaposhta.ua/orders/printMarking85x85/orders/{listToStr}/type/pdf8/apiKey/99f738524ca3320ece4b43b10f4181b1'
            return redirect(np_link_print)

        if 'add_to_register_choosed' in request.POST:
            list_of_refs = list(map(str, documentsIdFromOrders))
            params = {
               "apiKey": "99f738524ca3320ece4b43b10f4181b1",
               "modelName": "ScanSheet",
               "calledMethod": "insertDocuments",
               "methodProperties": {
                    "DocumentRefs": list_of_refs
                           }
                         }
            data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
            list_data = data["data"]
            print(list_data)
            register_Ref = ""
            if list_data:
                register_Ref = list_data[0]["Ref"]

            if data["errors"]:
                errors = data["errors"]
                print(errors)
            np_link_print = f'//my.novaposhta.ua/scanSheet/printScanSheet/refs[]/{register_Ref}/type/pdf/apiKey/99f738524ca3320ece4b43b10f4181b1'
            return redirect(np_link_print)



    return render(request, 'supplies/orders_new.html', {'title': title, 'orders': orders, 'cartCountData': cartCountData, 'isOrders': True, 'isOrdersTab': True})


@login_required(login_url='login')
def preorders(request):
    cartCountData = countCartItemsHelper(request)

    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        orders = PreOrder.objects.filter(place__user=request.user).order_by('-id')
        title = f'Всі передзамовлення для {request.user.first_name} {request.user.last_name}'
    else:
        orders = PreOrder.objects.all().order_by('-id')
        title = 'Всі передзамовлення'

    return render(request, 'supplies/preorders.html', {'title': title, 'orders': orders, 'cartCountData': cartCountData, 'isOrders': True, 'isPreordersTab': True})


@login_required(login_url='login')
def orderUpdateStatus(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    if action == 'update' and request.user.groups.filter(name='admin').exists():
      order = Order.objects.get(id=prodId)
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

    elif action == 'delete' and request.user.groups.filter(name='admin').exists():
        order = Order.objects.get(id=prodId)
        if not order.isComplete:
          supps = order.supplyinorder_set.all()
          for el in supps:
             if el.hasSupply():
               countInOrder = el.count_in_order
               supp = el.supply
               supp.countOnHold -= countInOrder
               supp.save(update_fields=['countOnHold'])
        order.delete()

    elif action == 'delete-preorder':
        order = PreOrder.objects.get(id=prodId)
        order.delete()

    elif action == 'update-preorder':
        order = PreOrder.objects.get(id=prodId)
        order.isComplete = True
        order.dateSent = timezone.now().date()
        order.save()

    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def ordersForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    orders = place.order_set.all()
    title = f'Всі замовлення для клієнта: \n {place.name}, {place.city_ref.name}'
    if not orders:
        title = f'В клієнта "{place.name}, {place.city_ref.name}" ще немає замовлень'

    return render(request, 'supplies/orders.html', {'title': title, 'orders': orders, 'isClients': True})


@login_required(login_url='login')
def devicesForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    devices = place.device_set.all()
    title = f'Всі прилади для клієнта: \n {place.name}, {place.city_ref.name}'

    cartCountData = countCartItemsHelper(request)

    if not devices:
        title = f'В клієнта "{place.name}, {place.city_ref.name}" ще немає замовлень'

    return render(request, 'supplies/devices.html', {'title': title, 'devices': devices, 'cartCountData': cartCountData,  'isClients': True})


def devicesList(request):
    devices = Device.objects.all().order_by('general_device__name')
    devFilters = DeviceFilter(request.GET, queryset=devices)
    devices = devFilters.qs
    title = f'Вcі прилади'
    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/devices.html', {'title': title, 'devices': devices, 'cartCountData': cartCountData, 'filter': devFilters, 'isDevices': True})




@login_required(login_url='login')
def serviceNotesForClient(request, client_id):
    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = CustomUser.objects.get(pk=request.user.id)
            obj.save()
            return HttpResponseRedirect(request.path_info)

    place = get_object_or_404(Place, pk=client_id)
    serviceNotes = place.servicenote_set.all()
    cartCountData = countCartItemsHelper(request)
    title = f'Всі сервісні замітки для клієнта: \n {place.name}, {place.city}'
    return render(request, 'supplies/serviceNotes.html',
                  {'title': title, 'serviceNotes': serviceNotes, 'form': form, 'cartCountData': cartCountData, 'isClients': True})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def createNote(request):
    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = CustomUser.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/createNote.html',
                  {'title': f'Створити новий запис', 'form': form, 'cartCountData': cartCountData,
                   'isService': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateNote(request, note_id):
    note = ServiceNote.objects.get(id=note_id)
    form = ServiceNoteForm(instance=note)

    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':
        form = ServiceNoteForm(request.POST, instance=note)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = CustomUser.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    return render(request, 'supplies/createNote.html',
                  {'title': f'Редагувати запис №{note_id}', 'form': form, 'cartCountData': cartCountData,
                    'isService': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateSupply(request, supp_id):
    note = Supply.objects.get(id=supp_id)
    form = SupplyForm(instance=note)

    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':
        next = request.POST.get('next')
        if 'save' in request.POST:
            form = SupplyForm(request.POST, instance=note)
            if form.is_valid():
                # obj = form.save(commit=False)
                # obj.from_user = User.objects.get(pk=request.user.id)
                form.save()
        elif 'delete' in request.POST:
            supp = Supply.objects.get(id=supp_id)
            supp.delete()

        return HttpResponseRedirect(next)

    return render(request, 'supplies/update_supply.html',
                  {'title': f'Редагувати запис №{supp_id}', 'cartCountData': cartCountData, 'form': form, 'suppId': supp_id})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def addSupplyToExistOrder(request, supp_id):
    supp = Supply.objects.get(id=supp_id)
    orderForm = OrderForm(request.POST or None)
    supply = SupplyInOrderInCart(count_in_order=1, supply=supp, lot=supp.supplyLot, date_expired=supp.expiredDate)

    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':

        count = int(request.POST.get('count_list'))
        if orderForm.is_valid():
            order = orderForm.cleaned_data['order']

            try:
                suppInOrder = SupplyInOrder.objects.get(supply=supp, generalSupply=supp.general_supply, supply_for_order=order, lot=supp.supplyLot, date_created=supp.dateCreated, date_expired=supp.expiredDate)
                suppInOrder.count_in_order += count
            except:
                suppInOrder = SupplyInOrder(count_in_order=count, supply=supp,
                                        generalSupply=supp.general_supply, supply_for_order=order, lot=supp.supplyLot,
                                        date_created=supp.dateCreated, date_expired=supp.expiredDate,
                                            internalName=supp.general_supply.name,
                                            internalRef=supp.general_supply.ref)
            suppInOrder.save()
            supp.countOnHold += count
            supp.save(update_fields=['countOnHold'])
            next = request.POST.get('next')
            return HttpResponseRedirect(next)


    return render(request, 'supplies/cart.html',
                  {'title': 'Додати до замовлення',
                   'orderForm': orderForm, 'supplies': [supply], 'cartCountData': cartCountData,
                   })


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl', 'client'])
def addSupplyToExistPreOrder(request, supp_id):
    supp = Supply.objects.get(id=supp_id)
    orderForm = PreOrderForm(request.POST or None)
    supply = SupplyInOrderInCart(count_in_order=1, supply=supp, lot=supp.supplyLot, date_expired=supp.expiredDate)
    cartCountData = countCartItemsHelper(request)

    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        orderForm.fields['order'].queryset = PreOrder.objects.filter(isComplete=False, place__user=request.user)

    if request.method == 'POST':

        count = int(request.POST.get('count_list'))
        if orderForm.is_valid():
            order = orderForm.cleaned_data['order']

            try:
                suppInOrder = SupplyInPreorder.objects.get(supply=supp, generalSupply=supp.general_supply, supply_for_order=order, lot=supp.supplyLot, date_created=supp.dateCreated, date_expired=supp.expiredDate)
                suppInOrder.count_in_order += count
            except:
                suppInOrder = SupplyInPreorder(count_in_order=count, supply=supp,
                                        generalSupply=supp.general_supply, supply_for_order=order, lot=supp.supplyLot,
                                        date_created=supp.dateCreated, date_expired=supp.expiredDate)
            suppInOrder.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)


    return render(request, 'supplies/cart.html',
                  {'title': 'Додати до замовлення',
                   'orderForm': orderForm, 'supplies': [supply], 'cartCountData': cartCountData,
                   })


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl', 'client'])
def addSupplyToExistPreOrderGeneral(request, supp_id):
    general_supp = GeneralSupply.objects.get(id=supp_id)
    orderForm = PreOrderForm(request.POST or None)
    supply = SupplyInPreorderInCart(count_in_order=1, supply_for_order=None, general_supply=general_supp)
    cartCountData = countCartItemsHelper(request)

    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        orderForm.fields['order'].queryset = PreOrder.objects.filter(isComplete=False, place__user=request.user)

    if request.method == 'POST':

        count = int(request.POST.get('count_list'))
        if orderForm.is_valid():
            order = orderForm.cleaned_data['order']

            try:
                suppInOrder = SupplyInPreorder.objects.get(generalSupply=general_supp, supply_for_order=order, date_expired=None)
                suppInOrder.count_in_order += count
            except:
                suppInOrder = SupplyInPreorder(generalSupply=general_supp, supply_for_order=order, date_expired=None, count_in_order=count)

            suppInOrder.save()
            next = request.POST.get('next')
            return redirect(f"/preorders/{order.id}")


    return render(request, 'supplies/cart.html',
                  {'title': 'Додати до замовлення',
                   'orderForm': orderForm, 'supplies': [supply], 'cartCountData': cartCountData,
                   })



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateGeneralSupply(request, supp_id):
    supp = GeneralSupply.objects.get(id=supp_id)
    form = GeneralSupplyForm(instance=supp)
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        next = request.POST.get('next')
        if 'save' in request.POST:
           form = GeneralSupplyForm(request.POST, instance=supp)
           if form.is_valid():
            # obj = form.save(commit=False)
            # obj.from_user = User.objects.get(pk=request.user.id)
              form.save()
              next = request.POST.get('next')

        elif 'delete' in request.POST:
           supp.delete()

        return HttpResponseRedirect(next)
    return render(request, 'supplies/update_supply.html',
                  {'title': f'Редагувати запис №{supp_id}', 'form': form, 'cartCountData': cartCountData})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def addNewLotforSupply(request, supp_id):
    generalSupp = GeneralSupply.objects.get(id=supp_id)
    form = SupplyForm()
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        form = SupplyForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.general_supply = generalSupp
            obj.category = generalSupp.category
            obj.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати новий LOT для {generalSupp.name}', 'form': form,  'cartCountData': cartCountData})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def addgeneralSupply(request):
    form = NewSupplyForm()
    cartCountData = countCartItemsHelper(request)
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
                  {'title': f'Додати новий товар', 'form': form,  'cartCountData': cartCountData})

@login_required(login_url='login')
def addgeneralSupplyOnly(request):
    form = NewGeneralSupplyForm()
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        form = NewGeneralSupplyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати нову назву товару', 'form': form,  'cartCountData': cartCountData})


@login_required(login_url='login')
def addNewClient(request):
    form = CreateClientForm()
    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':
        form = CreateClientForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            city_ref = form.cleaned_data['city_ref']
            address = form.cleaned_data['address']
            link = form.cleaned_data['link']
            organization_code = form.cleaned_data['organization_code']

            org = Place(name=name, city_ref=city_ref, address=address, link=link)

            if organization_code is not None:
                params = {
                    "apiKey": "99f738524ca3320ece4b43b10f4181b1",
                    "modelName": "Counterparty",
                    "calledMethod": "save",
                    "methodProperties": {
                        "CounterpartyType": "Organization",
                        "EDRPOU": f'{organization_code}',
                        "CounterpartyProperty": "Recipient"
                    }
                }
                data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
                print(data["data"])
                if data["data"]:
                    orgData = data["data"][0]
                    org.organization_code = int(orgData["EDRPOU"])
                    org.ref_NP = orgData["Ref"]
                    org.isAddedToNP = data["success"]
                    org.name_in_NP = orgData["Description"]

                if data["errors"]:
                    errors = data["errors"]
                    print(errors)
                    for error in errors:
                        messages.error(request, error)
                    return render(request, 'supplies/create_np_order_doucment.html',
                                  {'title': f'Додати нового клієнта', 'inputForm': form, 'cartCountData': cartCountData})

            org.save()
            return redirect('/clientsInfo')
    return render(request, 'supplies/create_np_order_doucment.html',
                  {'title': f'Додати нового клієнта', 'inputForm': form, 'cartCountData': cartCountData})



@login_required(login_url='login')
def addNewDeviceForClient(request, client_id):
    client = Place.objects.get(id=client_id)
    form = DeviceForm(request.POST or None)
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        if form.is_valid():
            device = Device(general_device=form.cleaned_data['general_device'],
                            serial_number=form.cleaned_data['serial_number'],
                            date_installed=form.cleaned_data['date_installed'],
                            in_city=client.city_ref,
                            in_place=client)
            device.save()
            return redirect('/clientsInfo')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати прилад для: \n {client.name}, {client.city_ref.name}', 'form': form, 'cartCountData': cartCountData})


@login_required(login_url='login')
def editClientInfo(request, client_id):
    client = Place.objects.get(id=client_id)
    form = ClientForm(request.POST or None, instance=client)
    workersSet = client.workers.filter(ref_NP__isnull=False, ref_counterparty_NP__isnull=False)
    adressesSet = client.delivery_places
    workersSetExist = workersSet.exists()
    adressSetExist = adressesSet.exists()
    form.fields['worker_NP'].queryset = workersSet
    form.fields['address_NP'].queryset = adressesSet
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        if 'add_address_NP' in request.POST:
            cityName = request.POST.get('cityName')
            addressName = request.POST.get('streetName')
            cityRef = request.POST.get('np-cityref')
            addressRef = request.POST.get('np-streetRef')
            streetNumber = request.POST.get('streetNumber')
            flatNumber = request.POST.get('flatNumber')
            comment = request.POST.get('comment')
            recipientType = request.POST.get('recipientType')

            if recipientType == 'Doors':
                params = {
                    "apiKey": "99f738524ca3320ece4b43b10f4181b1",
                    "modelName": "Address",
                    "calledMethod": "save",
                    "methodProperties": {
                        "CounterpartyRef": "3b0e7317-2a6b-11eb-8513-b88303659df5",
                        "StreetRef": addressRef,
                        "BuildingNumber": streetNumber,
                        "Flat": flatNumber,
                        "Note": comment
                    }
                }
                data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
                list = data["data"]
                print('------------------ add_address_NP ---------------')
                print(list)
                if list:
                    addressRef = list[0]["Ref"]
                    addressName = list[0]["Description"]
                if data["errors"]:
                    errors = data["errors"]
                    print(errors)
                    for error in errors:
                        messages.info(request, error)
                        return render(request, 'supplies/editClientDetail.html',
                                      {'title': f'Редагувати клієнта: {client.name}, {client.city}', 'form': form,
                                       'cartCountData': cartCountData})

            deliveryPlace = DeliveryPlace(cityName=cityName, addressName=addressName, city_ref_NP=cityRef,
                                          address_ref_NP=addressRef, deliveryType=recipientType, for_place=client)
            deliveryPlace.save()
            return redirect(f'/clientsInfo/{client_id}/editInfo')

        if 'generalSave' in request.POST:
            if form.is_valid():
                try:
                    organization_code = form.cleaned_data['organization_code']
                except:
                    organization_code = None

                if organization_code is not None:
                    params = {
                        "apiKey": "99f738524ca3320ece4b43b10f4181b1",
                        "modelName": "Counterparty",
                        "calledMethod": "save",
                        "methodProperties": {
                            "CounterpartyType": "Organization",
                            "EDRPOU": f'{organization_code}',
                            "CounterpartyProperty": "Recipient"
                        }
                    }
                    data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
                    list = data["data"]
                    print('------------------ generalSave ---------------')
                    print(list)
                    if list:
                        print(data["data"])
                        client.organization_code = data["data"][0]["EDRPOU"]
                        client.isAddedToNP = True
                        client.name_in_NP = data["data"][0]["Description"]
                        client.ref_NP = data["data"][0]["Ref"]
                        client.save()
                    if data["errors"]:
                        errors = data["errors"]
                        print(errors)
                        for error in errors:
                            messages.info(request, error)
                            return redirect(f'/clientsInfo/{client_id}/editInfo')

                form.save()
                return redirect('/clientsInfo')


    return render(request, 'supplies/editClientDetail.html',
                  {'title': f'Редагувати клієнта: {client.name}, {client.city}', 'place': client, 'form': form, 'cartCountData': cartCountData, 'workersSetExist': workersSetExist, 'adressSetExist': adressSetExist, 'clientId': client_id})

@login_required(login_url='login')
def addNewWorkerForClient(request, place_id):
    form = WorkerForm()
    place = Place.objects.get(id=place_id)
    cartCountData = countCartItemsHelper(request)
    orgRefExist = place.ref_NP is not None

    if request.method == 'POST':
        form = WorkerForm(request.POST)
        radioButton = request.POST.get('flexRadioDefault')
        if form.is_valid():
            refNP = ""
            if radioButton == 'asOrganization':
                refNP = place.ref_NP
            if radioButton == 'asPrivateUser':
                refNP = "3b13350b-2a6b-11eb-8513-b88303659df5"

            params = {
                "apiKey": "99f738524ca3320ece4b43b10f4181b1",
                "modelName": "ContactPerson",
                "calledMethod": "save",
                "methodProperties": {
                    "CounterpartyRef": refNP,
                    "FirstName": form.cleaned_data['name'],
                    "LastName": form.cleaned_data['secondName'],
                    "MiddleName": form.cleaned_data['middleName'],
                    "Phone": form.cleaned_data['telNumber']
                }
            }
            obj = form.save(commit=False)

            if radioButton is not None:
                data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
                if data["data"]:
                    userData = data["data"][0]
                    print(userData)
                    obj.ref_NP = userData['Ref']
                if data["errors"]:
                    errors = data["errors"]
                    print(errors)
                    for error in errors:
                        messages.info(request, error)
                    return render(request, 'supplies/addNewWorkerForClient.html',
                                  {'title': f'Додати нового працівника для {place.name}, {place.city}',
                                   'form': form,
                                   'cartCountData': cartCountData, 'orgRefExist': orgRefExist})





            obj.ref_counterparty_NP = refNP
            obj.for_place = place
            obj.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)
    return render(request, 'supplies/addNewWorkerForClient.html',
                  {'title': f'Додати нового працівника для {place.name}, {place.city}', 'form': form, 'cartCountData': cartCountData, 'orgRefExist': orgRefExist})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteServiceNote(request, note_id):
    note = ServiceNote.objects.get(id=note_id)
    if request.method == 'POST':
        note.delete()
    return redirect('/serviceNotes')


def orderDetail_pdf(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=orderDetail' + \
        str(order.id) + str(order.place.name) + str(order.place.city) + '.pdf'
    template = get_template('supplies/orderdetail-pdf.html')
    pisa_status = render_to_pdf(supplies_in_order)
    return HttpResponse(pisa_status, content_type='application/pdf')


def fetch_resources(uri, rel):
    path = os.path.join(uri.replace(settings.STATIC_URL, ""))
    return path

def render_to_pdf(supplies_in_order):
    template = get_template('supplies/orderdetail-pdf.html')
    html = template.render({'supps': supplies_in_order})
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result, link_callback=fetch_resources, encoding='utf-8')
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


def render_to_csv(request, order_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=venues.csv'

    # Create a csv writer
    writer = csv.writer(response)

    # Designate The Model
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

    # Add column headings to the csv file
    writer.writerow(['Назва товару', 'Категорія', 'REF', 'LOT', 'Кількість', 'Строк придатності'])

    # Loop Thu and output
    for supp in supplies_in_order:
        writer.writerow([supp.generalSupply.name, supp.generalSupply.category.name, supp.generalSupply.ref, supp.lot, supp.date_expired])

    return response

def render_to_xls(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Order-{order_id}.xlsx"

    row_num = 3

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet(f'№{order_id}, {order.place.name}, {order.place.city}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)


    columns_table = [ {'header': '№'},
        {'header': 'Назва товару'},
     {'header': 'REF'},
     {'header': 'LOT'},
     {'header': 'К-ть'},
     {'header': 'Тер.прид.'},
     ]

    ws.write(0, 0, f'Замов. №{order_id} для {order.place.name}, {order.place.city} від {order.dateCreated.strftime("%d-%m-%Y")}', format)
    if order.comment:
        format = wb.add_format()
        format.set_font_size(14)
        ws.write(1, 0, f'Коммент.: {order.comment}', format)
        ws.write(2, 0, f'Всього: {supplies_in_order.count()} шт.', format)

    format = wb.add_format()
    format.set_font_size(14)

    for row in supplies_in_order:
        row_num += 1
        name = row.generalSupply.name
        ref = ''
        if row.generalSupply.ref:
           ref = row.generalSupply.ref
        lot = ''
        if row.lot:
            lot = row.lot
        count = row.count_in_order
        date_expired = row.date_expired.strftime("%d-%m-%Y")

        val_row = [name, ref, lot, count, date_expired]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 35)
    ws.set_column(2, 3, 20)
    ws.set_column(4, 4, 10)
    ws.set_column(5, 5, 15)

    ws.add_table(3, 0, supplies_in_order.count() + 3, len(columns_table) - 1, {'columns': columns_table})
    wb.close()

    return response


def preorder_render_to_xls(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all()

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Preorder_{order_id}.xlsx"

    row_num = 9

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet(f'№{order_id}, {order.place.name}, {order.place.city_ref.name}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)


    columns_table = [ {'header': '№'},
        {'header': 'Назва товару'},
     {'header': 'REF'},
     {'header': 'LOT'},
     {'header': 'К-ть'},
     {'header': 'Тер.прид.'},
    {'header': 'Index'}
     ]

    ws.write(0, 0, f'Замов. №{order_id} для {order.place.name[:30]}, {order.place.city_ref.name} від {order.dateCreated.strftime("%d-%m-%Y")}', format)
    if order.comment:
        format = wb.add_format()
        format.set_font_size(14)
        ws.write(1, 0, f'Коммент.: {order.comment}', format)
        ws.write(2, 0, f'Всього: {supplies_in_order.count()} шт.', format)

    format = wb.add_format({'text_wrap': True})
    format.set_font_size(14)

    supplyNotExistColor = '#fcd9d9'
    onlyGoodColor = '#fffcad'
    onlyGoodSixMonthColor = '#e3fad4'
    onlyExpiredColor = '#ffe1ad'

    supplyNotExistColorIndex = 1
    onlyGoodColorIndex = 2
    onlyGoodSixMonthColorIndex = 3
    onlyExpiredColorIndex = 4


    six_months = timezone.now().date() + relativedelta(months=+6)

    format = wb.add_format({'bg_color': supplyNotExistColor})
    format.set_font_size(14)
    ws.write(4, 0, 'Немає на складі', format)
    ws.write(4, 1, '', format)
    ws.write(4, 2, '', format)
    ws.write(4, 3, supplyNotExistColorIndex, format)

    format = wb.add_format({'bg_color': onlyGoodColor})
    format.set_font_size(14)
    ws.write(5, 0, 'Товар є на складі з терміном до 6-ти місяців', format)
    ws.write(5, 1, '', format)
    ws.write(5, 2, '', format)
    ws.write(5, 3, onlyGoodColorIndex, format)

    format = wb.add_format({'bg_color': onlyGoodSixMonthColor})
    format.set_font_size(14)
    ws.write(6, 0, 'Товар є на складі з терміном більше 6-ти місяців', format)
    ws.write(6, 1, '', format)
    ws.write(6, 2, '', format)
    ws.write(6, 3, onlyGoodSixMonthColorIndex, format)

    format = wb.add_format({'bg_color': onlyExpiredColor})
    format.set_font_size(14)
    ws.write(7, 0, 'Товар є на складі тільки прострочений', format)
    ws.write(7, 1, '', format)
    ws.write(7, 2, '', format)
    ws.write(7, 3, onlyExpiredColorIndex, format)

    for row in supplies_in_order:

        supplyNotExist = row.generalSupply.general.count() == 0
        onlyExpired = row.generalSupply.general.filter(expiredDate__lte=timezone.now().date()).count() > 0
        onlyGood = row.generalSupply.general.filter(expiredDate__range=[timezone.now().date(), six_months]).count() > 0

        onlyGoodSixMonth = row.generalSupply.general.filter(expiredDate__gte=six_months).count() > 0
        suppd = row.generalSupply.general.filter(expiredDate__gte=six_months)
        good_and_expired = onlyGood and onlyExpired

        format = wb.add_format({'text_wrap': True})
        format.set_font_size(14)
        colorIndex = 0

        if supplyNotExist:
            format = wb.add_format({'text_wrap': True, 'bg_color': supplyNotExistColor})
            format.set_font_size(14)
            colorIndex = supplyNotExistColorIndex
        elif onlyGood:
            format = wb.add_format({'text_wrap': True, 'bg_color': onlyGoodColor})
            format.set_font_size(14)
            colorIndex = onlyGoodColorIndex
        elif onlyGoodSixMonth:
            format = wb.add_format({'text_wrap': True, 'bg_color': onlyGoodSixMonthColor})
            format.set_font_size(14)
            colorIndex = onlyGoodSixMonthColorIndex
        elif onlyExpired:
            format = wb.add_format({'text_wrap': True, 'bg_color': onlyExpiredColor})
            format.set_font_size(14)
            colorIndex = onlyExpiredColorIndex

        row_num += 1
        name = row.generalSupply.name
        ref = ''
        if row.generalSupply.ref:
           ref = row.generalSupply.ref
        lot = ''
        if row.lot:
            lot = row.lot
        count = row.count_in_order
        date_expired = ''
        if row.date_expired:
            date_expired = row.date_expired.strftime("%d-%m-%Y")

        val_row = [name, ref, lot, count, date_expired, colorIndex]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 35)
    ws.set_column(2, 3, 15)
    ws.set_column(4, 4, 6)
    ws.set_column(5, 5, 12)
    ws.set_column(6, 6, 5)

    ws.add_table(9, 0, supplies_in_order.count() + 9, len(columns_table) - 1, {'columns': columns_table})
    wb.close()

    return response


@login_required(login_url='login')
def devices_render_to_xls(request):
    devices = Device.objects.all()

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Devices-List.xlsx"

    row_num = 3

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet('Devices-List')
    format = wb.add_format({'bold': True})
    format.set_font_size(24)

    columns_table = [{'header': '№'},
                     {'header': 'Name'},
                     {'header': 'S/N'},
                     {'header': 'Customer City'},
                     {'header': 'Customer Name'},
                     {'header': 'Date Installed'}
                     ]

    ws.write(0, 0,
             'Devices List DIAMEDIX Ukraine',
             format)

    format = wb.add_format({'text_wrap': True})
    format.set_font_size(22)
    for row in devices:
        row_num += 1
        name = row.general_device.name
        customer = row.in_place.name
        customer_city = row.in_place.city
        serial_number = ''
        if row.serial_number:
            serial_number = row.serial_number
        date_installed = ''
        if row.date_installed:
            date_installed = row.date_installed.strftime("%d-%m-%Y")

        val_row = [name, serial_number, customer_city, customer, date_installed]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3, format)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 30)
    ws.set_column(2, 2, 20)
    ws.set_column(3, 3, 25)
    ws.set_column(4, 4, 65)
    ws.set_column(5, 5, 20)

    ws.add_table(3, 0, devices.count() + 3, len(columns_table) - 1, {'columns': columns_table})
    wb.close()

    return response






@login_required(login_url='login')
def orderDetail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all().order_by('id')
    cartCountData = countCartItemsHelper(request)

    print(supplies_in_order.first())
    return render(request, 'supplies/orderDetail.html', {'title': f'Замовлення № {order_id}', 'order': order, 'supplies': supplies_in_order, 'cartCountData': cartCountData,  'isOrders': True})



@login_required(login_url='login')
def preorderDetail(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all().order_by('id')
    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/preorderDetail.html', {'title': f'Передзамовлення № {order_id}', 'order': order, 'supplies': supplies_in_order, 'cartCountData': cartCountData, 'isOrders': True})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def preorderDetail_generateOrder(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all().order_by('id')
    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':
        checkBoxSuppIdList = request.POST.getlist('flexCheckDefault')
        print("POST ---")
        print(checkBoxSuppIdList)


    return render(request, 'supplies/preorderDetail-generate-order.html',
                  {'title': f'Передзамовлення № {order_id}', 'order': order, 'supplies': supplies_in_order,
                   'cartCountData': cartCountData, 'isOrders': True})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def clientsInfo(request):
    place = Place.objects.all().order_by('-id')
    placeFilter = PlaceFilter(request.GET, queryset=place)
    place = placeFilter.qs
    cartCountData = countCartItemsHelper(request)
    return render(request, 'supplies/clientsList.html',
                  {'title': f'Клієнти', 'clients': place, 'placeFilter': placeFilter, 'cartCountData': cartCountData, 'isClients': True})


@login_required(login_url='login')
def serviceNotes(request):
    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = CustomUser.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    serviceNotes = ServiceNote.objects.all().order_by('-id')
    serviceFilters = ServiceNotesFilter(request.GET, queryset=serviceNotes)
    serviceNotes = serviceFilters.qs
    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/serviceNotes.html',
                   {'title': f'Сервiсні записи', 'serviceNotes': serviceNotes, 'cartCountData': cartCountData, 'form': form, 'serviceFilters': serviceFilters, 'isService': True})

