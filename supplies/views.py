import asyncio

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from django.urls import reverse
from django.db.models import Prefetch, prefetch_related_objects
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
from django.db.models import Count, Sum, F
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
import csv
import pymsteams


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
            "Page": "0"
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



    # reader = pandas.read_csv('/Users/macbook/Documents/DIAMEDIX/supp_workers.csv')
    # vals = reader.values
    # for row in vals:
    #     id_place = int(row[4])
    #     name = row[1]
    #     tel = None
    #     if row[2] != 'nan':
    #         tel = row[2]
    #     pos = None
    #     if row[3] != 'nan':
    #         pos = row[3]
    #
    #     telnm = str(tel).removeprefix('+').replace('-', '').replace(' ', '').strip()
    #     if telnm[0] != '3':
    #         telnm = '38' + telnm
    #     print(telnm)

        # workr = Workers(name=name, telNumber=telnm, position=pos, for_place_id=id_place)
        # workr.save()

        # city_ref = int(row[0])
        # place = Place(id=id, name=name, city=city, address=address)
        # place.save()

    #
    # excel_data_df = pandas.read_excel('/Users/macbook/Documents/DIAMEDIX/OfertaDiasys.xlsx', header=None, index_col=None, sheet_name='cons')
    # wb = excel_data_df
    # vals = wb.values
    # for obj in vals:
    #     ref = obj[0]
    #     # smn = str(obj[2]).removesuffix('.0')
    #     name = str(obj[1])
    #     packed = obj[2]
    #     # tests = obj[5]
    #     # tests = obj[5]
    #     if name != 'nan':
    #         print(name, ref, packed)
    #         genSup = GeneralSupply(name=name, ref=ref, package_and_tests=packed, category_id=5)
    #         genSup.save()

@login_required(login_url='login')
def countCartItemsHelper(request):
    isClient = request.user.groups.filter(name='client').exists()
    preorders_await = 0
    preorders_partial = 0

    try:
        orderInCart = OrderInCart.objects.first()
        orderitems = orderInCart.supplyinorderincart_set.all()
        cart_items = sum([item.count_in_order for item in orderitems])
    except:
        cart_items = 0
    try:
        precart_order = PreorderInCart.objects.get(userCreated=request.user, isComplete=False)
        orderitems = precart_order.supplyinpreorderincart_set.all()
        precart_items = sum([item.count_in_order for item in orderitems])
    except:
        precart_items = 0
    try:
        if isClient:
            orders_incomplete = Order.objects.filter(isComplete=False, place__user=request.user).count()
        else:
            orders_incomplete = Order.objects.filter(isComplete=False).count()
    except:
        orders_incomplete = 0
    try:
        if isClient:
            preorders_incomplete = PreOrder.objects.filter(isComplete=False, place__user=request.user).count()
        else:
            preorders_incomplete = PreOrder.objects.filter(isComplete=False).count()
    except:
        preorders_incomplete = 0


    if not isClient:
        preorders_await = PreOrder.objects.filter(state_of_delivery='Awaiting').count()
        preorders_partial = PreOrder.objects.filter(state_of_delivery='Partial').count()




    return {'cart_items': cart_items, 'precart_items': precart_items, 'orders_incomplete': orders_incomplete,
            'preorders_incomplete': preorders_incomplete, 'preorders_await': preorders_await, 'preorders_partial': preorders_partial}

@login_required(login_url='login')
def full_image_view_for_device_image(request, device_id):
    device = Device.objects.get(pk=device_id)
    return render(request, 'supplies/full_image_view_for_device_image.html', {'device': device})


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

        for_preorder = suppInOrder.supply_for_order.for_preorder or None

        if for_preorder:
           sup_in_preorder = for_preorder.supplyinpreorder_set.get(generalSupply=suppInOrder.generalSupply)
           sup_in_preorder.count_in_order_current -= suppInOrder.count_in_order
           if sup_in_preorder.count_in_order_current >= sup_in_preorder.count_in_order:
               sup_in_preorder.state_of_delivery = 'Complete'
           elif sup_in_preorder.count_in_order_current != 0 and sup_in_preorder.count_in_order_current < sup_in_preorder.count_in_order:
               sup_in_preorder.state_of_delivery = 'Partial'
           else:
               sup_in_preorder.state_of_delivery = 'Awaiting'

           sup_in_preorder.save(update_fields=['count_in_order_current', 'state_of_delivery'])




    elif action == 'delete-preorder':
        suppInOrder = SupplyInPreorder.objects.get(id=prodId)
        suppInOrder.delete()

    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def add_preorder_general_to_preorder(request, prodId):
    user = request.user
    general_supply = GeneralSupply.objects.get(id=prodId)
    print('preorder_general_supp_buttons', prodId)

    preorder, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)

    try:
        suppInCart = SupplyInPreorderInCart.objects.get(
                                        supply_for_order=preorder,
                                        general_supply=general_supply)
        suppInCart.count_in_order += 1
        suppInCart.save(update_fields=['count_in_order'])
    except:
        suppInCart = SupplyInPreorderInCart(count_in_order=1,
                                            supply_for_order=preorder,
                                            general_supply=general_supply)
        suppInCart.save()

    countInPreorder = suppInCart.count_in_order
    response = render(request, 'partials/add_precart_button_general.html',
                      {'el': general_supply, 'countInPreCart': countInPreorder})
    trigger_client_event(response, 'subscribe_precart', {})
    return response

# @login_required(login_url='login')
# def preorder_general_supp_buttons(request, prodId):
#     user = request.user
#
#     supply = Supply.objects.get(id=prodId)
#     preorder, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)
#     suppInCart = SupplyInPreorderInCart(
#         supply=supply,
#         supply_for_order=preorder,
#         lot=supply.supplyLot,
#         date_expired=supply.expiredDate,
#         date_created=supply.dateCreated)
#
#     suppInCart.count_in_order = (suppInCart.count_in_order + 1)
#     suppInCart.save()
#
#     # elif action == 'add-general':
#     #     general_supply = GeneralSupply.objects.get(id=prodId)
#     #
#     #     preorder, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)
#     #     suppInCart = SupplyInPreorderInCart(id=general_supply.id,
#     #             supply_for_order=preorder,
#     #             general_supply=general_supply)
#     #
#     #     suppInCart.count_in_order = (suppInCart.count_in_order + 1)
#     #     suppInCart.save()
#
#     return JsonResponse('Item was added', safe=False)


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
    deltaCountOnHold = supply.count - (supply.countOnHold + supply.preCountOnHold) == 0
    deltaCountOnCart = supply.count - (supply.countOnHold + supply.preCountOnHold) - countInPreCart == 0

    response = render(request, 'partials/add_precart_button.html', {'countInPreCart': countInPreCart, 'supp': supply, 'deltaCountOnHold': deltaCountOnHold, 'deltaCountOnCart': deltaCountOnCart})
    trigger_client_event(response, 'subscribe_precart', {})
    return response


@login_required(login_url='login')
def updateItem(request, supp_id):
    user = request.user
    supply = Supply.objects.get(id=supp_id)

    order, created = OrderInCart.objects.get_or_create(userCreated=user, isComplete=False)

    try:
        suppInCart = SupplyInOrderInCart.objects.get(id=supp_id, supply=supply, supply_for_order=order,
                                                     lot=supply.supplyLot,
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
    response = render(request, 'partials/add_cart_button.html',
                      {'cartCountData': cartCountData, 'supp': supply, 'deltaCount': deltaCountOnHold,
                       'countInCart': countInCart, 'deltaCountOnCart': deltaCountOnCart})
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

    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def orderTypeDescriptionField(request):
    orderType = request.POST.get('orderType')
    isAgreement = orderType == 'Agreement'
    return render(request, 'partials/orderTypeDescriptionField.html', {'isAgreement': isAgreement})@login_required(login_url='login')


def add_to_exist_order_from_cart(request):
    orderType = request.POST.get('orderType')
    isAdd_to_exist_order = orderType == 'add_to_Exist_order'
    orders = []
    if isAdd_to_exist_order:
        place_id = request.POST.get('place_id')
        place = Place.objects.get(pk=place_id)
        orders = place.order_set.filter(isComplete=False)
    return render(request, 'partials/add_to_exist_order_from_cart.html', {'isAdd_to_exist_order': isAdd_to_exist_order, 'orders': orders})


@login_required(login_url='login')
def orderTypeDescriptionField_for_client(request):
    orderType = request.POST.get('orderType')
    place_id_Selected = request.POST.get('place_id')
    isAddedToExistPreorder = orderType == 'add_to_Exist_preorder'
    preorders = PreOrder.objects.filter(isComplete=False, place_id=place_id_Selected)

    return render(request, 'partials/orderTypeDescriptionField_for_client.html', {'isAddedToExistPreorder': isAddedToExistPreorder, 'preorders': preorders})



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
                user = form.save(commit=False)
                user.save()
                user_group = Group.objects.get(name='client')
                user.groups.add(user_group)
                return redirect('login')

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
    suppFilter = SupplyFilter(request.GET, queryset=supplies)

    # fetchxmls()
    uncompleteOrdersExist = Order.objects.filter(isComplete=False).exists()
    isClient = request.user.groups.filter(name='client').exists() and not request.user.is_staff
    if isClient:
        uncompletePreOrdersExist = PreOrder.objects.filter(isComplete=False, place__user=request.user).exists()
        html_page = 'supplies/home_for_client.html'
    else:
        uncompletePreOrdersExist = PreOrder.objects.filter(isComplete=False).exists()
        html_page = 'supplies/home.html'
        if not suppFilter.data:
            suppFilter.data['ordering'] = SupplyFilter.EXIST_CHOICES.В_наявності

    supplies = suppFilter.qs

    # if suppFilter.data['ordering'] == "onlyGood":
    #     print("onlyGood")

    paginator = Paginator(supplies, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':
        supp = supplies.get(id=request.POST.get('supp_id'))
        supp.delete()

    return render(request, html_page, {'title': 'Всі товари',
                                                  'cartCountData': cartCountData,
                                                  'supplies': page_obj, 'suppFilter': suppFilter,
                                                  'isHome': True,
                                                  'isAll': True,
                                                  'uncompleteOrdersExist': uncompleteOrdersExist,
                                                  'uncompletePreOrdersExist': uncompletePreOrdersExist})




def update_count_in_preorder_cart(request, itemId):


    if request.method == 'POST':
        count = request.POST.get(f'count_{itemId}')
        countId = request.POST.get(f'count_id_{itemId}')

        supsInPreorderInCart = SupplyInPreorderInCart.objects.get(id=itemId)
        print(f'NAME:  {supsInPreorderInCart.general_supply.name} = {count}')

        supsInPreorderInCart.count_in_order = count
        supsInPreorderInCart.save(update_fields=['count_in_order'])

        return updatePreCartItemCount(request)


import threading
def sendTeamsMsg(order):
    myTeamsMessage = pymsteams.connectorcard(
        "https://ddxi.webhook.office.com/webhookb2/e9d80572-d9a1-424e-adb4-e6e2840e8c34@d4f5ac22-fa4d-4156-b0e0-9c62234c6b45/IncomingWebhook/3a448e3eaf974db19d8940ba81e9bcad/3894266e-3403-44b0-a8e4-5a568f2b70a4")
    myTeamsMessage.title(f'Передамовлення №{order.id},\n\n{order.place.name}, {order.place.city_ref.name}')

    myTeamsMessage.addLinkButton("Деталі замовлення",
                                 f'https://dmdxstorage.herokuapp.com/preorders/{order.id}')
    myTeamsMessage.addLinkButton("Excel",
                                 f'https://dmdxstorage.herokuapp.com/preorder-detail-csv/{order.id}')
    created = f'*створив:*  **{order.userCreated.first_name} {order.userCreated.last_name}**'
    if order.comment:
        comment = f'*коментар:*  **{order.comment}**'
        myTeamsMessage.text(f'{created}\n\n{comment};')
        myTeamsMessage.send()
    else:
        myTeamsMessage.text(f'{created}')
        myTeamsMessage.send()


@login_required(login_url='login')
def cartDetailForClient(request):
    orderInCart = PreorderInCart.objects.get(userCreated=request.user, isComplete=False)
    cartCountData = countCartItemsHelper(request)
    supplies = orderInCart.supplyinpreorderincart_set.all()
    cities = City.objects.all()
    orderForm = OrderInCartForm(request.POST or None)
    places = []
    placeChoosed = False
    preorders = None



    isClient = request.user.groups.filter(name='client').exists()

    supDict = {}
    for d in supplies:
        t = supDict.setdefault(d.general_supply.category, [])
        t.append(d)
    print(supDict)


    if isClient:
        places = Place.objects.filter(user=request.user)
        # places.fields['place'].queryset = places
        preorders = PreOrder.objects.filter(isComplete=False, userCreated=request.user)

        if places.count() == 1:
            print(places.count())
            placeChoosed = True
            # places.fields['place'].initial = places.first()
    else:
        isPendingPreorderExist = PreOrder.objects.filter(isComplete=False).exists()

    if request.method == 'POST':

        if orderForm.is_valid():
            comment = orderForm.cleaned_data['comment']
            isComplete = orderForm.cleaned_data['isComplete']
            orderType = request.POST.get('orderType')
            place_id = request.POST.get('place_id')
            place = Place.objects.get(id=place_id)

            if orderType == 'Agreement':
                agreement_description = request.POST.get('agreement_description')
                if isComplete:
                    dateSent = timezone.now().date()
                else:
                    dateSent = None
                agreement = Agreement(userCreated=orderInCart.userCreated, description=agreement_description, for_place=place, isComplete=isComplete, comment=comment)
                agreement.save()

                for index, sup in enumerate(supplies):
                    count = request.POST.get(f'count_{sup.id}')
                    general_sup = sup.general_supply
                    suppInOrder = SupplyInAgreement(count_in_agreement=count,
                                                    generalSupply=general_sup,
                                                    supply_for_agreement=agreement, lot=sup.lot,
                                                    date_created=sup.date_created,
                                                    date_expired=sup.date_expired)
                    suppInOrder.save()

                teams_channel = "https://ddxi.webhook.office.com/webhookb2/e9d80572-d9a1-424e-adb4-e6e2840e8c34@d4f5ac22-fa4d-4156-b0e0-9c62234c6b45/IncomingWebhook/23dc86985db643f6a50d4bbf45719d3d/3894266e-3403-44b0-a8e4-5a568f2b70a4"

                myTeamsMessage = pymsteams.connectorcard(teams_channel)
                myTeamsMessage.title(
                    f'Договір №{agreement_description},\n\n{place.name}, {place.city_ref.name}')

                myTeamsMessage.addLinkButton("Деталі договору",
                                             f'https://dmdxstorage.herokuapp.com/agreements/{agreement.id}')
                created = f'*створив:*  **{agreement.userCreated.first_name} {agreement.userCreated.last_name}**'
                if comment:
                    comment = f'*коментар:*  **{comment}**'
                    myTeamsMessage.text(f'{created}\n\n{comment};')
                    myTeamsMessage.send()
                else:
                    myTeamsMessage.text(f'{created}')
                    myTeamsMessage.send()


            elif orderType == 'Preorder':
                if isComplete:
                    dateSent = timezone.now().date()
                else:
                    dateSent = None
                order = PreOrder(userCreated=orderInCart.userCreated, place=place, dateSent=dateSent,
                                 isComplete=isComplete,
                                 comment=comment)
                order.save()

                for index, sup in enumerate(supplies):
                    count = request.POST.get(f'count_{sup.id}')
                    general_sup = sup.general_supply
                    suppInOrder = SupplyInPreorder(count_in_order=count,
                                                   generalSupply=general_sup,
                                                   supply_for_order=order)

                    suppInOrder.save()

                t = threading.Thread(target=sendTeamsMsg, args=[order], daemon=True)
                t.start()

            elif orderType == 'add_to_Exist_preorder':
                selected_non_completed_preorder = request.POST.get('selected_non_completed_preorder')
                selectedPreorder = PreOrder.objects.get(id=selected_non_completed_preorder)
                if isComplete:
                    dateSent = timezone.now().date()
                else:
                    dateSent = None
                selectedPreorder.dateSent = dateSent
                selectedPreorder.isComplete = isComplete
                if selectedPreorder.comment and comment:
                    selectedPreorder.comment += f' / {comment}'
                elif comment:
                    selectedPreorder.comment = comment
                selectedPreorder.save()

                sups_in_preorder = selectedPreorder.supplyinpreorder_set.all()
                print("----||||||||---------")
                print(sups_in_preorder)

                for index, sup in enumerate(supplies):
                    count = request.POST.get(f'count_{sup.id}')
                    general_sup = sup.general_supply


                    try:
                        exist_sup = sups_in_preorder.get(generalSupply=general_sup)
                        print("-------------------")
                        print(exist_sup)
                        exist_sup.count_in_order += int(count)
                        exist_sup.save()
                        print("--------/////////----")
                    except:
                        suppInOrder = SupplyInPreorder(count_in_order=count,
                                                       generalSupply=general_sup,
                                                       supply_for_order=selectedPreorder)
                        suppInOrder.save()


        orderInCart.delete()

        return redirect('/preorders')

    return render(request, 'supplies/preorder-cart.html',
                  {'title': 'Корзина передзамовлення', 'order': orderInCart, 'cartCountData': cartCountData,
                   'supplies': supplies, 'cities': cities,
                   'orderForm': orderForm, 'places': places, 'placeChoosed': placeChoosed, 'preorders': preorders, 'isClient': isClient, 'supDict': supDict})


@login_required(login_url='login')
def carDetailForStaff(request):
    orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
    cart_items = orderInCart.get_cart_items
    supplies = orderInCart.supplyinorderincart_set.all()
    cities = City.objects.all()
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
                   'cities': cities,
                   'orderForm': orderForm
                   })


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_np_sender_place(request):
    user = request.user
    places = user.sender_np_places.all()


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
        return redirect('/add_np_sender_place')

    return render(request, 'supplies/add_new_sender_np_place.html', {'places': places})




@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl', 'client'])
def choose_preorder_in_cart_for_client(request):
    try:
        place = request.GET.get('place_id')
        preorders = Place.objects.get(id=place).preorder_set.filter(isComplete=False)
    except:
        place = None
        preorders = None

    return render(request, 'partials/choose_preorder_in_cart_for_client.html',
                  {'preorders': preorders, 'placeChoosed': place != None})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def get_place_for_city_in_precart(request):
    city_id = request.GET.get('city')
    try:
        places = Place.objects.filter(city_ref_id=city_id)
    except:
        places = None

    return render(request, 'partials/choose_place_in_cart_not_precart.html', {'places': places, 'cityChoosed': places != None, 'placeChoosed': False})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def get_place_for_city_in_cart(request):
    city_id = request.GET.get('city')
    try:
        places = Place.objects.filter(city_ref_id=city_id)
    except:
        places = None

    return render(request, 'partials/choose_place_in_cart.html',
                  {'places': places, 'cityChoosed': places != None, 'placeChoosed': False})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def choose_place_in_cart_not_precart(request):
    place_id = request.GET.get('place_id')
    try:
        place = Place.objects.get(pk=place_id)
        orders = place.order_set.filter(isComplete=False)
        preorders = place.getUcompletePreorderSet()
    except:
        place = None
        orders =None
        preorders = None



    return render(request, 'partials/choose_uncompleted_order_in_cart.html', {'orders': orders, 'place': place, 'preorders': preorders, 'isPlaceChoosed': place != None})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def get_agreement_for_place_for_city_in_cart(request):
    place_id = request.GET.get('place_id')
    place = Place.objects.get(pk=place_id)
    agreements = place.preorder_set.filter(isComplete=False)

    return render(request, 'partials/choose_agreement_forplace_incart.html', {'agreements': agreements, 'isPendingPreorderExist': agreements.exists(), 'isPlaceChoosed': True})


def sendTeamsMsgCart(order):
    agreementString = ''
    if order.for_preorder:
        agreementString = f'Передзамовлення № {order.for_preorder.id}'

    myTeamsMessage = pymsteams.connectorcard(
        "https://ddxi.webhook.office.com/webhookb2/e9d80572-d9a1-424e-adb4-e6e2840e8c34@d4f5ac22-fa4d-4156-b0e0-9c62234c6b45/IncomingWebhook/c6694506a800419ab9aa040b09d0a5b1/3894266e-3403-44b0-a8e4-5a568f2b70a4")
    myTeamsMessage.title(f'Замовлення №{order.id},\n\n{order.place.name}, {order.place.city_ref.name}')

    myTeamsMessage.addLinkButton("Деталі замовлення", f'https://dmdxstorage.herokuapp.com/orders/{order.id}/0')
    myTeamsMessage.addLinkButton("Excel", f'https://dmdxstorage.herokuapp.com/order-detail-csv/{order.id}')
    created = f'*створив:*  **{order.userCreated.first_name} {order.userCreated.last_name}**'
    if order.comment:
        comment = f'*комментарій:*  **{order.comment}**'
        myTeamsMessage.text(f'{agreementString}\n\n{created}\n\n{comment};')
        myTeamsMessage.send()
    else:
        myTeamsMessage.text(f'{agreementString}\n\n{created}')
        myTeamsMessage.send()

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def cartDetail(request):
    orderInCart = OrderInCart.objects.first()
    cartCountData = countCartItemsHelper(request)
    supplies = orderInCart.supplyinorderincart_set.all()
    orderForm = OrderInCartForm(request.POST or None)
    cities = City.objects.all()
    if request.method == 'POST':
        if 'save' in request.POST:
            orderType = request.POST.get('orderType')
            if orderForm.is_valid():
                place_id = request.POST.get('place_id')
                place = Place.objects.get(id=place_id)
                comment = orderForm.cleaned_data['comment']
                try:
                    isComplete = orderForm.cleaned_data['isComplete']
                except:
                    isComplete = False

                if isComplete:
                    dateSent = timezone.now().date()
                else:
                    dateSent = None
                if orderType == 'new_order':

                    order = Order(userCreated=orderInCart.userCreated, place=place, dateSent=dateSent,
                                  isComplete=isComplete,
                                  comment=comment)
                    order.save()

                    for index, sup in enumerate(supplies):
                        count = request.POST.get(f'count_{sup.id}')
                        suppInOrder = SupplyInOrder(count_in_order=count,
                                                    supply=sup.supply,
                                                    generalSupply=sup.supply.general_supply,
                                                    supply_for_order=order,
                                                    lot=sup.lot,
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
                            supDeltaCount = supply.count - countInOrder
                            if supDeltaCount == 0:
                                supply.delete()
                            else:
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

                    t = threading.Thread(target=sendTeamsMsgCart, args=[order], daemon=True)
                    t.start()


                elif orderType == 'add_to_Exist_order':
                    selected_non_completed_order = request.POST.get('selected_non_completed_order')
                    selectedOrder = Order.objects.get(id=selected_non_completed_order)

                    selectedOrder.dateSent = dateSent
                    selectedOrder.isComplete = isComplete
                    if selectedOrder.comment and comment:
                        selectedOrder.comment += f' / {comment}'
                    elif comment:
                        selectedOrder.comment = comment
                    selectedOrder.save()

                    sups_in_order = selectedOrder.supplyinorder_set.all()
                    # print("----||||||||---------")
                    # print(sups_in_preorder)
                    sups_in_order_arr = []
                    sups_in_order_arr = list(sups_in_order)


                    for sup in supplies:
                        count = request.POST.get(f'count_{sup.id}')
                        general_sup = sup.supply.general_supply
                        try:
                            exist_sup = sups_in_order.get(supply=sup.supply)
                            exist_sup.count_in_order += int(count)
                            exist_sup.save()
                            supply = exist_sup.supply
                            sups_in_order_arr.remove(exist_sup)
                            print('------------removed-------------')
                            print(exist_sup.supply.general_supply.name)
                            try:
                                countOnHold = int(supply.countOnHold)
                            except:
                                countOnHold = 0
                            countInOrder = exist_sup.count_in_order
                            if isComplete:
                                print(isComplete)
                                supply.countOnHold -= countOnHold
                                supply.count -= countInOrder
                                supply.save(update_fields=['countOnHold', 'count'])
                                if supply.count == 0:
                                    supply.delete()

                                genSupInPreorder = exist_sup.supply_in_preorder
                                if genSupInPreorder:
                                    genSupInPreorder.count_in_order_current += exist_sup.count_in_order
                                    if genSupInPreorder.count_in_order - genSupInPreorder.count_in_order_current <= 0:
                                        genSupInPreorder.state_of_delivery = 'Complete'
                                    else:
                                        genSupInPreorder.state_of_delivery = 'Partial'
                                    genSupInPreorder.save()

                            else:
                                if supply.countOnHold:
                                    print('-------------------------')
                                    print(supply.countOnHold)
                                    print(f'count on hold = {countOnHold}')
                                    print(f'count in order = {count}')
                                    print('-------------------------')
                                    supply.countOnHold = countOnHold + int(count)
                                    supply.save(update_fields=['countOnHold'])
                                else:
                                    supply.countOnHold = 0
                                    supply.save(update_fields=['countOnHold'])
                                    supply.countOnHold = countOnHold + int(count)
                                    supply.save(update_fields=['countOnHold'])

                        except:
                            try:
                                sup_in_preorder = selectedOrder.for_preorder.supplyinpreorder_set.get(
                                    generalSupply=general_sup)
                            except:
                                sup_in_preorder = None
                            suppInOrder = SupplyInOrder(count_in_order=count,
                                                        supply=sup.supply,
                                                        generalSupply=general_sup,
                                                        supply_for_order=selectedOrder,
                                                        supply_in_preorder=sup_in_preorder,
                                                        lot=sup.lot,
                                                        date_created=sup.date_created,
                                                        date_expired=sup.date_expired,
                                                        internalName=general_sup.name,
                                                        internalRef=general_sup.ref)
                            suppInOrder.save()
                            supply = suppInOrder.supply
                            try:
                                countOnHold = int(supply.countOnHold)
                            except:
                                countOnHold = 0
                            countInOrder = int(suppInOrder.count_in_order)
                            if isComplete:
                                supDeltaCount = supply.count - countInOrder
                                if supDeltaCount == 0:
                                    supply.delete()
                                else:
                                    supply.count -= countInOrder
                                    supply.save(update_fields=['count'])

                                genSupInPreorder = suppInOrder.supply_in_preorder
                                if genSupInPreorder:
                                    genSupInPreorder.count_in_order_current += countInOrder
                                    if genSupInPreorder.count_in_order - genSupInPreorder.count_in_order_current <= 0:
                                        genSupInPreorder.state_of_delivery = 'Complete'
                                    else:
                                        genSupInPreorder.state_of_delivery = 'Partial'
                                    genSupInPreorder.save()


                            else:
                                if supply.countOnHold:
                                    supply.countOnHold = countOnHold + countInOrder
                                    supply.save(update_fields=['countOnHold'])
                                else:
                                    supply.countOnHold = 0
                                    supply.save(update_fields=['countOnHold'])
                                    supply.countOnHold = countOnHold + countInOrder
                                    supply.save(update_fields=['countOnHold'])

                    print('---------------------////////////----------------')
                    if isComplete:
                        for su in sups_in_order_arr:
                            try:
                                countOnHold = int(su.supply.countOnHold)
                            except:
                                countOnHold = 0
                            print(su.supply.general_supply.name)
                            su.supply.countOnHold -= countOnHold
                            su.supply.count -= su.count_in_order
                            su.supply.save(update_fields=['countOnHold', 'count'])
                            if su.supply.count == 0:
                                su.supply.delete()

                            genSupInPreorder = su.supply_in_preorder
                            if genSupInPreorder:
                                genSupInPreorder.count_in_order_current += su.count_in_order
                                if genSupInPreorder.count_in_order - genSupInPreorder.count_in_order_current <= 0:
                                    genSupInPreorder.state_of_delivery = 'Complete'
                                else:
                                    genSupInPreorder.state_of_delivery = 'Partial'
                            genSupInPreorder.save()


                    if selectedOrder.for_preorder and isComplete:
                        sups_in_preorder = selectedOrder.for_preorder.supplyinpreorder_set.all()
                        if all(sp.state_of_delivery == 'Complete' for sp in sups_in_preorder):
                            selectedOrder.for_preorder.state_of_delivery = 'Complete'
                        elif any(x.state_of_delivery == 'Partial' or 'Awaiting' for x in sups_in_preorder):
                            selectedOrder.for_preorder.state_of_delivery = 'Partial'
                        selectedOrder.for_preorder.save(update_fields=['state_of_delivery'])



            orderInCart.delete()
            return redirect('/orders')


        if 'delete' in request.POST:
            next = request.POST.get('next')
            orderInCart.delete()
            return HttpResponseRedirect(next)


    return render(request, 'supplies/cart.html',
                  {'title': 'Корзина', 'order': orderInCart, 'cartCountData': cartCountData, 'supplies': supplies,
                   'orderForm': orderForm, 'cities': cities,
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
            name = ''
            ref = ''
            lot = ''
            category = ''
            if row.general_supply:
                name = row.general_supply.name
                ref = row.general_supply.ref
                category = row.general_supply.category.name

            if row.supplyLot:
                lot = row.supplyLot
            count = row.count
            date_expired = row.expiredDate.strftime("%d.%m.%Y")
            if row.name:
                name = row.name



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
                  {'title': 'Дочерні товари', 'supplies': supplies, 'cartCountData': cartCountData,
                   'suppFilter': suppFilter, 'isHome': True, 'isChild': True})



@login_required(login_url='login')
def order_delete(request, order_id):
    order = Order.objects.get(id=order_id)
    if not order.isComplete:
        supps = order.supplyinorder_set.all()
        for el in supps:
            if el.hasSupply():
                countInOrder = el.count_in_order
                supp = el.supply
                supp.countOnHold -= countInOrder
                supp.save(update_fields=['countOnHold'])

    if order.npdeliverycreateddetailinfo_set.exists():
        # for delInfo in order.npdeliverycreateddetailinfo_set.all():
        docrefs = order.npdeliverycreateddetailinfo_set.values_list('ref')
        params = {
              "apiKey": "[ВАШ КЛЮЧ]",
              "modelName": "InternetDocument",
              "calledMethod": "delete",
              "methodProperties": {
                    "DocumentRefs": docrefs
                   }
        }

        data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
        print(data)

    order.delete()
    next = request.GET.get('next')
    return HttpResponseRedirect(next)


@login_required(login_url='login')
def agreements(request):
    cartCountData = countCartItemsHelper(request)
    orders = Agreement.objects.all().order_by('-id')
    totalCount = orders.count()

    title = f'Всі договори. ({totalCount} шт.)'

    return render(request, 'supplies/agreements.html',
                  {'title': title, 'orders': orders, 'cartCountData': cartCountData, 'isOrders': True,
                   'totalCount': totalCount,
                   'isAgreementsTab': True})


@login_required(login_url='login')
def orders(request):
    cartCountData = countCartItemsHelper(request)

    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        orders = Order.objects.filter(place__user=request.user).order_by('-id')
        totalCount = orders.count()
        title = f'Всі замовлення для {request.user.first_name} {request.user.last_name}. ({totalCount} шт.)'

    else:
        orders = Order.objects.all().order_by('-id')
        totalCount = orders.count()
        title = f'Всі замовлення. ({totalCount} шт.)'

    orderFilter = OrderFilter(request.POST or None, queryset=orders)
    orders = orderFilter.qs
    paginator = Paginator(orders, 20)
    page_number = request.POST.get('page')
    orders = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_orders = request.POST.getlist('register_print_buttons')
        print("------ ", selected_orders, "-----------")
        selected_ids = map(int, selected_orders)
        fileteredOredrs = Order.objects.filter(pk__in=selected_ids)
        for_orders_name_list = []
        for ordr in fileteredOredrs:
            ordrString = f'№{ordr.id} - {ordr.place}'
            for_orders_name_list.append(ordrString)
        documentsIdFromOrders = fileteredOredrs.values_list('npdeliverycreateddetailinfo__ref', flat=True)
        listToStr = ','.join(map(str, documentsIdFromOrders))
        print(listToStr)
        print("------------------------------------------------list string np red")

        if 'print_choosed' in request.POST:
            print('---------------------PRINT CHOOSED --------------------------------')
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
            print(data)
            register_Ref = ""
            if list_data:
                register_Ref = list_data[0]["Ref"]
                register_number = list_data[0]["Number"]
                date = list_data[0]["Date"]

                in_list = []
                for obj in list_data[0]["Success"]:
                    in_list.append(obj['Number'])
                np_link_print = f'//my.novaposhta.ua/scanSheet/printScanSheet/refs[]/{register_Ref}/type/pdf/apiKey/99f738524ca3320ece4b43b10f4181b1'
                dt_obj = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                date_string = dt_obj.strftime('%d.%m.%Y %H:%M')
                regInfoModel = RegisterNPInfo(barcode_string=register_number, register_url=np_link_print, date=date_string, documentsId=in_list, for_orders=for_orders_name_list)
                regInfoModel.save()

                return redirect(np_link_print)

            if data["errors"]:
                errors = data["errors"]
                print(errors)
                for error in errors:
                    messages.info(request, error)
                return render(request, 'supplies/orders_new.html',
                              {'title': title, 'orders': orders, 'cartCountData': cartCountData, 'isOrders': True,
                               'totalCount': totalCount,
                               'isOrdersTab': True})


    return render(request, 'supplies/orders_new.html',
                  {'title': title, 'orders': orders, 'orderFilter': orderFilter, 'cartCountData': cartCountData, 'isOrders': True, 'totalCount': totalCount,
                   'isOrdersTab': True})


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

    preorderFilter = PreorderFilter(request.GET, queryset=orders)
    orders = preorderFilter.qs

    return render(request, 'supplies/preorders.html',
                  {'title': title, 'orders': orders, 'preorderFilter': preorderFilter, 'cartCountData': cartCountData, 'isOrders': True,
                   'isPreordersTab': True})


@login_required(login_url='login')
def delete_preorder_sup_in_preorder_cart(request, sup_id, order_id):
    print(order_id)
    print(sup_id)
    preorderInCart = PreorderInCart.objects.get(id=order_id)
    sup = preorderInCart.supplyinpreorderincart_set.get(id=sup_id)
    sup.delete()
    supplies = preorderInCart.supplyinpreorderincart_set.all()
    if supplies.count() == 0:
        preorderInCart.delete()
    supDict = {}
    for d in supplies:
        t = supDict.setdefault(d.general_supply.category, [])
        t.append(d)

    return render(request, 'partials/preorders_cart_list.html',
                  {'supDict': supDict, 'order': preorderInCart})



@login_required(login_url='login')
def deletePreorder(request, order_id):
    objTodelete = PreOrder.objects.get(id=order_id)
    objTodelete.delete()
    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        orders = PreOrder.objects.filter(place__user=request.user).order_by('-id')
    else:
        orders = PreOrder.objects.all().order_by('-id')

    return render(request, 'partials/preorders-list.html',
                  {'orders': orders})


@login_required(login_url='login')
def updatePreorderStatus(request, order_id):
    order = PreOrder.objects.get(id=order_id)

    order.isComplete = True
    order.dateSent = timezone.now().date()
    order.save()

    return render(request, 'partials/preorder_preview_cell.html', {'order': order})


@login_required(login_url='login')
def orderUpdateStatus(request, order_id):
        order = Order.objects.get(id=order_id)
        supps = order.supplyinorder_set.all()
        for el in supps:
            countInOrder = el.count_in_order
            supp = el.supply
            supp.countOnHold -= countInOrder
            supp.count -= countInOrder
            supp.save(update_fields=['countOnHold', 'count'])
            if supp.count == 0:
                supp.delete()

            genSupInPreorder = el.supply_in_preorder
            if genSupInPreorder:
                genSupInPreorder.count_in_order_current += el.count_in_order
                if genSupInPreorder.count_in_order - genSupInPreorder.count_in_order_current <= 0:
                    genSupInPreorder.state_of_delivery = 'Complete'
                else:
                    genSupInPreorder.state_of_delivery = 'Partial'
                genSupInPreorder.save()



        order.isComplete = True
        order.dateSent = timezone.now().date()
        order.save()

        preorder = order.for_preorder
        if preorder:
            sups_in_preorder = preorder.supplyinpreorder_set.all()
            if all(sp.state_of_delivery == 'Complete' for sp in sups_in_preorder):
                preorder.state_of_delivery = 'Complete'
            elif any(x.state_of_delivery == 'Partial' or 'Awaiting' for x in sups_in_preorder):
                preorder.state_of_delivery = 'Partial'
            preorder.save(update_fields=['state_of_delivery'])

        return render(request, 'partials/order_preview_cel.html', {'order': order})

    # elif action == 'delete' and request.user.groups.filter(name='admin').exists():
    #     order = Order.objects.get(id=prodId)
    #     if not order.isComplete:
    #         supps = order.supplyinorder_set.all()
    #         for el in supps:
    #             if el.hasSupply():
    #                 countInOrder = el.count_in_order
    #                 supp = el.supply
    #                 supp.countOnHold -= countInOrder
    #                 supp.save(update_fields=['countOnHold'])
    #     order.delete()
    #
    # elif action == 'delete-preorder':
    #     order = PreOrder.objects.get(id=prodId)
    #     order.delete()
    #
    # elif action == 'update-preorder':
    #     order = PreOrder.objects.get(id=prodId)
    #     order.isComplete = True
    #     order.dateSent = timezone.now().date()
    #     order.save()




@login_required(login_url='login')
def ordersForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    orders = place.order_set.all().order_by('-id')
    orderFilter = OrderFilter(request.GET, queryset=orders)
    orders = orderFilter.qs
    title = f'Всі замовлення для клієнта: \n {place.name}, {place.city_ref.name}'
    if not orders:
        title = f'В клієнта "{place.name}, {place.city_ref.name}" ще немає замовлень'

    return render(request, 'supplies/orders_new.html', {'title': title, 'orders': orders, 'orderFilter': orderFilter, 'isClients': True})


@login_required(login_url='login')
def agreementsForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    orders = place.preorder_set.all().order_by('-id')
    preorderFilter = PreorderFilter(request.GET, queryset=orders)
    orders = preorderFilter.qs
    cartCountData = countCartItemsHelper(request)
    title = f'Всі передзамовлення для клієнта: \n {place.name}, {place.city_ref.name}'

    return render(request, 'supplies/preorders.html',
           {'title': title, 'orders': orders, 'preorderFilter': preorderFilter, 'cartCountData': cartCountData,
            'isOrders': True,
            'isPreordersTab': True, 'fromClientList': True})


@login_required(login_url='login')
def devicesForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    devices = place.device_set.all()
    title = f'Всі прилади для клієнта: \n {place.name}, {place.city_ref.name}'

    cartCountData = countCartItemsHelper(request)

    if not devices:
        title = f'В клієнта "{place.name}, {place.city_ref.name}" ще немає замовлень'

    return render(request, 'supplies/devices.html',
                  {'title': title, 'devices': devices, 'cartCountData': cartCountData, 'isClients': True})


def devicesList(request):
    devices = Device.objects.all().order_by('-id')
    devFilters = DeviceFilter(request.GET, queryset=devices)
    devices = devFilters.qs
    title = f'Вcі прилади'
    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/devices.html',
                  {'title': title, 'devices': devices, 'cartCountData': cartCountData, 'filter': devFilters,
                   'isDevices': True})


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
                  {'title': title, 'serviceNotes': serviceNotes, 'form': form, 'cartCountData': cartCountData,
                   'isClients': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'engineer'])
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
@allowed_users(allowed_roles=['admin', 'engineer'])
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
                  {'title': f'Редагувати запис №{supp_id}', 'cartCountData': cartCountData, 'form': form,
                   'suppId': supp_id})


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
                suppInOrder = SupplyInOrder.objects.get(supply=supp, generalSupply=supp.general_supply,
                                                        supply_for_order=order, lot=supp.supplyLot,
                                                        date_created=supp.dateCreated, date_expired=supp.expiredDate)
                suppInOrder.count_in_order += count
            except:
                suppInOrder = SupplyInOrder(count_in_order=count, supply=supp,
                                            generalSupply=supp.general_supply, supply_for_order=order,
                                            lot=supp.supplyLot,
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
                   'orderForm': orderForm, 'supplies': [supply], 'cartCountData': cartCountData, 'placeExist': True,
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
                suppInOrder = SupplyInPreorder.objects.get(supply=supp, generalSupply=supp.general_supply,
                                                           supply_for_order=order, lot=supp.supplyLot,
                                                           date_created=supp.dateCreated, date_expired=supp.expiredDate)
                suppInOrder.count_in_order += count
            except:
                suppInOrder = SupplyInPreorder(count_in_order=count, supply=supp,
                                               generalSupply=supp.general_supply, supply_for_order=order,
                                               lot=supp.supplyLot,
                                               date_created=supp.dateCreated, date_expired=supp.expiredDate)
            suppInOrder.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)

    return render(request, 'supplies/cart.html',
                  {'title': 'Додати до замовлення',
                   'orderForm': orderForm, 'supplies': [supply], 'cartCountData': cartCountData, 'placeExist': True,
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
                suppInOrder = SupplyInPreorder.objects.get(generalSupply=general_supp, supply_for_order=order,
                                                           date_expired=None)
                suppInOrder.count_in_order += count
            except:
                suppInOrder = SupplyInPreorder(generalSupply=general_supp, supply_for_order=order, date_expired=None,
                                               count_in_order=count)

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
    form = NewGeneralSupplyForm(instance=supp)
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        next = request.POST.get('next')
        if 'save' in request.POST:
            form = NewGeneralSupplyForm(request.POST, request.FILES, instance=supp)
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
            obj.name = generalSupp.name
            obj.ref = generalSupp.ref
            obj.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати новий LOT для {generalSupp.name}', 'form': form, 'cartCountData': cartCountData})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def addgeneralSupply(request):
    form = NewSupplyForm()
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        form = NewSupplyForm(request.POST)
        if form.is_valid():
            try:
                genSupp = GeneralSupply.objects.get(name=form.cleaned_data['name'].strip())
            except:
                genSupp = GeneralSupply(name=form.cleaned_data['name'].strip(), ref=form.cleaned_data['ref'].strip(),
                                        category=form.cleaned_data['category'])
            genSupp.save()
            obj = form.save(commit=False)
            obj.general_supply = genSupp
            obj.save()
            # form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати новий товар', 'form': form, 'cartCountData': cartCountData})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def addNewCity(request):
    form = NewCityForm()
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        form = NewCityForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати нове місто', 'form': form, 'cartCountData': cartCountData})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def addNewCategory(request):
    form = NewCategoryForm()
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        form = NewCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати нову категорію для товара', 'form': form, 'cartCountData': cartCountData})



@login_required(login_url='login')
def addgeneralSupplyOnly(request):
    form = NewGeneralSupplyForm()
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        form = NewGeneralSupplyForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати нову назву товару', 'form': form, 'cartCountData': cartCountData})


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
                                  {'title': f'Додати нового клієнта', 'inputForm': form,
                                   'cartCountData': cartCountData})

            org.save()
            return redirect('/clientsInfo')
    return render(request, 'supplies/create_np_order_doucment.html',
                  {'title': f'Додати нового клієнта', 'inputForm': form, 'cartCountData': cartCountData})


@login_required(login_url='login')
def addNewDeviceForClient(request, client_id):
    client = Place.objects.get(id=client_id)
    form = DeviceForm(request.POST or None, request.FILES or None)
    cartCountData = countCartItemsHelper(request)
    if request.method == 'POST':
        if form.is_valid():
            form_to_save = form.save(commit=False)  # gives you the instance without saving it
            form_to_save.in_city = client.city_ref
            form_to_save.in_place = client
            form_to_save.save()
            return redirect('/clientsInfo')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'Додати прилад для: \n {client.name}, {client.city_ref.name}', 'form': form,
                   'cartCountData': cartCountData})


@login_required(login_url='login')
def editWorkerInfo(request, worker_id):
    wrkr = Workers.objects.get(id=worker_id)
    form = WorkerForm(request.POST or None, instance=wrkr)
    place = wrkr.for_place
    cartCountData = countCartItemsHelper(request)
    orgRefExist = place.ref_NP is not None

    if request.method == 'POST':
        if 'save' in request.POST:
            radioButton = request.POST.get('flexRadioDefault')
            if form.is_valid():
                refNP = None
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
                        return redirect(reverse('editWorkerInfo', kwargs={'worker_id': worker_id}))
                obj.ref_counterparty_NP = refNP
                obj.save()
                next = request.POST.get('next')
                return redirect(next)

        if 'delete' in request.POST:
            wrkr.delete()
            next = request.POST.get('next')
            return redirect(next)

    return render(request, 'supplies/addNewWorkerForClient.html',
                  {'title': f'Редагувати працівника для: \n{place.name}, {place.city_ref.name}', 'form': form,
                   'cartCountData': cartCountData, 'orgRefExist': orgRefExist})


@login_required(login_url='login')
def editClientInfo(request, client_id):
    client = Place.objects.get(id=client_id)
    form = ClientForm(request.POST or None, instance=client)
    workersSet = client.workers.filter(ref_NP__isnull=False, ref_counterparty_NP__isnull=False)
    adressesSet = client.delivery_places.all()
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

            # Counterparty REF for add address as private person, but if organization added as organization to NP, address ref should be save for orgRef
            counterpartyref = "3b0e7317-2a6b-11eb-8513-b88303659df5"

            if client.ref_NP is not None:
                counterpartyref = client.ref_NP


            if recipientType == 'Doors':
                params = {
                    "apiKey": "99f738524ca3320ece4b43b10f4181b1",
                    "modelName": "Address",
                    "calledMethod": "save",
                    "methodProperties": {
                        "CounterpartyRef": counterpartyref,
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
                    deliveryPlace = DeliveryPlace(cityName=cityName, addressName=addressName, city_ref_NP=cityRef,
                                                  address_ref_NP=addressRef, deliveryType=recipientType,
                                                  for_place=client)
                    deliveryPlace.save()
                    return redirect(f'/clientsInfo/{client_id}/editInfo')
                if data["errors"]:
                    errors = data["errors"]
                    print(errors)
                    for error in errors:
                        messages.info(request, error)
                        return redirect(f'/clientsInfo/{client_id}/editInfo')
            else:
                deliveryPlace = DeliveryPlace(cityName=cityName, addressName=addressName, city_ref_NP=cityRef,
                                              address_ref_NP=addressRef, deliveryType=recipientType,
                                              for_place=client)
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
                            return redirect(reverse('editClientInfo', kwargs={'client_id': client_id}))

                form.save()
                return redirect('/clientsInfo')

    return render(request, 'supplies/editClientDetail.html',
                  {'title': f'Редагувати клієнта: {client.name}, {client.city_ref.name}', 'place': client, 'form': form,
                   'cartCountData': cartCountData, 'workersSetExist': workersSetExist, 'adressSetExist': adressSetExist,
                   'clientId': client_id})


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
                    return redirect(reverse('newWorkerForPlace', kwargs={'place_id': place_id}))
            obj.ref_counterparty_NP = refNP
            obj.for_place = place
            obj.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)
    return render(request, 'supplies/addNewWorkerForClient.html',
                  {'title': f'Додати нового працівника для {place.name}, {place.city}', 'form': form,
                   'cartCountData': cartCountData, 'orgRefExist': orgRefExist})


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
        writer.writerow([supp.generalSupply.name, supp.generalSupply.category.name, supp.generalSupply.ref, supp.lot,
                         supp.date_expired])

    return response


def render_to_xls(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Order-{order_id}-{order.place.name}-{order.place.city}.xlsx"

    row_num = 3
    row_num_to_table = 3

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet(f'№{order_id}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)

    columns_table = [{'header': '№'},
                     {'header': 'Назва товару'},
                     {'header': 'Пакування / Тести'},
                     {'header': 'Категорія'},
                     {'header': 'REF'},
                     {'header': 'SMN Code'},
                     {'header': 'LOT'},
                     {'header': 'К-ть'},
                     {'header': 'Тер.прид.'},
                     ]

    ws.write(0, 0,
             f'Замов. №{order_id} для {order.place.name}, {order.place.city} від {order.dateCreated.strftime("%d-%m-%Y")}',
             format)
    if order.comment:
        format = wb.add_format()
        format.set_font_size(14)
        ws.write(1, 0, f'Коммент.: {order.comment}', format)
    ws.write(2, 0, f'Всього: {supplies_in_order.count()} шт.', format)

    if order.npdeliverycreateddetailinfo_set.exists():
        format = wb.add_format()
        format.set_font_size(15)
        for deliveryInfo in order.npdeliverycreateddetailinfo_set.all():
            row_num += 1
            ws.write(row_num, 0, f'Номер накладної НП: {deliveryInfo.document_id}', format)
            row_num += 1
            ws.write(row_num, 0, f'Aдреса отримувача: {deliveryInfo.recipient_address}', format)
            row_num += 1
            ws.write(row_num, 0, f'Контактна особа-отримувач: {deliveryInfo.recipient_worker}', format)
            row_num += 1
            ws.write(row_num, 0, f'Розрахункова дата доставки: {deliveryInfo.estimated_time_delivery}', format)
            row_num += 1
            ws.write(row_num, 0, f'Вартість доставки: {deliveryInfo.cost_on_site} грн.', format)
            row_num += 1
            ws.write(row_num, 0, '', format)
            row_num += 1
            row_num_to_table = row_num

    format = wb.add_format()
    format.set_font_size(14)
    ws.add_table(row_num, 0, supplies_in_order.count() + row_num, len(columns_table) - 1, {'columns': columns_table})

    for row in supplies_in_order:
        row_num += 1
        name = row.generalSupply.name
        category = row.generalSupply.category
        ref = ''
        if row.generalSupply.ref:
            ref = row.generalSupply.ref
        smn_code = ''
        if row.generalSupply.SMN_code:
            smn_code = row.generalSupply.SMN_code
        packtests = ''
        if row.generalSupply.package_and_tests:
            packtests = row.generalSupply.package_and_tests

        lot = ''
        if row.lot:
            lot = row.lot
        count = row.count_in_order

        date_expired = row.date_expired.strftime("%d-%m-%Y")

        val_row = [name, packtests, category, ref, smn_code, lot, count, date_expired]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - row_num_to_table)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 35)
    ws.set_column(2, 3, 15)
    ws.set_column(4, 5, 20)
    ws.set_column(6, 6, 15)
    ws.set_column(7, 7, 5)
    ws.set_column(8, 8, 12)
    wb.close()

    return response


def preorder_render_to_xls(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order_all = order.supplyinpreorder_set.all()
    supplies_in_order = []
    for sup in supplies_in_order_all:
        if sup.count_in_order - sup.count_in_order_current > 0:
            supplies_in_order.append(sup)
    print(supplies_in_order)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Preorder_{order_id}.xlsx"

    row_num = 9

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet(f'№{order_id}, {order.place.name}, {order.place.city_ref.name}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)

    columns_table = [{'header': '№'},
                     {'header': 'Name'},
                     {'header': 'Category'},
                     {'header': 'REF'},
                     {'header': 'SMN code'},
                     {'header': 'Count in order'},
                     {'header': 'Delivered count'},
                     {'header': 'Awaiting count'},
                     # {'header': 'Index'}
                     ]

    ws.write(0, 0,
             f'Замов. №{order_id} для {order.place.name[:30]}, {order.place.city_ref.name} від {order.dateCreated.strftime("%d-%m-%Y")}',
             format)
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
        smn = ''
        if row.generalSupply.SMN_code:
            smn = row.generalSupply.SMN_code
        category = ''
        if row.generalSupply.category:
            category = row.generalSupply.category
        count_in_order = row.count_in_order
        current_delivery_count = row.count_in_order_current
        count_borg = row.count_in_order - row.count_in_order_current
        date_expired = ''

        val_row = [name, category, ref, smn, count_in_order, current_delivery_count, count_borg]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 35)
    ws.set_column(2, 4, 20)
    ws.set_column(4, 7, 15)
    # ws.set_column(8, 8, 5)

    ws.add_table(9, 0, len(supplies_in_order) + 9, len(columns_table) - 1, {'columns': columns_table})
    wb.close()

    return response


@login_required(login_url='login')
def devices_render_to_xls(request):
    translator = Translator()
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
        customer = translate_text(row.in_place.name, target_language='en')
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
def orderDetail(request, order_id, sup_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all().order_by('id')
    cartCountData = countCartItemsHelper(request)
    next = request.POST.get('next')

    if request.method == 'POST':

        if 'delete' in request.POST:
            next = request.POST.get('next')
            if not order.isComplete:
                supps = order.supplyinorder_set.all()
                for el in supps:
                    if el.hasSupply():
                        countInOrder = el.count_in_order
                        supp = el.supply
                        supp.countOnHold -= countInOrder
                        supp.save(update_fields=['countOnHold'])

                    for_preorder = el.supply_for_order.for_preorder or None
                    if for_preorder:
                        sup_in_preorder = for_preorder.supplyinpreorder_set.get(generalSupply=el.generalSupply)
                        sup_in_preorder.count_in_order_current -= countInOrder
                        if sup_in_preorder.count_in_order_current >= sup_in_preorder.count_in_order:
                            sup_in_preorder.state_of_delivery = 'Complete'
                        elif sup_in_preorder.count_in_order_current != 0 and sup_in_preorder.count_in_order_current < sup_in_preorder.count_in_order:
                            sup_in_preorder.state_of_delivery = 'Partial'
                        else:
                            sup_in_preorder.state_of_delivery = 'Awaiting'

                        sup_in_preorder.save(update_fields=['count_in_order_current', 'state_of_delivery'])

            if order.npdeliverycreateddetailinfo_set.exists():
                docrefs = order.npdeliverycreateddetailinfo_set.values_list('ref')
                for ref in docrefs:
                    params = {
                        "apiKey": "99f738524ca3320ece4b43b10f4181b1",
                        "modelName": "InternetDocument",
                        "calledMethod": "delete",
                        "methodProperties": {
                            "DocumentRefs": ref
                        }
                    }
                    data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
                    print(data)

            order.delete()
            return HttpResponseRedirect(next)

    return render(request, 'supplies/orderDetail.html',
                  {'title': f'Замовлення № {order_id}', 'order': order, 'supplies': supplies_in_order,
                   'cartCountData': cartCountData, 'isOrders': True, 'highlighted_sup_id': sup_id})


@login_required(login_url='login')
def get_agreement_detail_for_cart(request):
    agr_id = request.GET.get('agreement_id')
    try:
        agreement = Agreement.objects.get(pk=agr_id)
        supplies_in_agreement = agreement.supplyinagreement_set.all().order_by('id')
    except:
        agreement = None
        supplies_in_agreement = None


    return render(request, 'partials/get_agreement_detail_for_cart.html',
                  {'agreement': agreement, 'supplies': supplies_in_agreement, 'agreement_is_exist': agreement != None })




@login_required(login_url='login')
def agreementDetail(request, agreement_id):
    agreement = get_object_or_404(Agreement, pk=agreement_id)
    supplies_in_agreement = agreement.supplyinagreement_set.all().order_by('id')
    orders_in_agreement = agreement.order_set.all().order_by('-id')
    cartCountData = countCartItemsHelper(request)
    next = request.POST.get('next')

    # if request.method == 'POST':
    #
    #     if 'delete' in request.POST:
    #         next = request.POST.get('next')
    #         if not order.isComplete:
    #             supps = order.supplyinorder_set.all()
    #             for el in supps:
    #                 if el.hasSupply():
    #                     countInOrder = el.count_in_order
    #                     supp = el.supply
    #                     supp.countOnHold -= countInOrder
    #                     supp.save(update_fields=['countOnHold'])
    #
    #         if order.npdeliverycreateddetailinfo_set.exists():
    #             docrefs = order.npdeliverycreateddetailinfo_set.values_list('ref')
    #             for ref in docrefs:
    #                 params = {
    #                     "apiKey": "99f738524ca3320ece4b43b10f4181b1",
    #                     "modelName": "InternetDocument",
    #                     "calledMethod": "delete",
    #                     "methodProperties": {
    #                         "DocumentRefs": ref
    #                     }
    #                 }
    #                 data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
    #                 print(data)
    #
    #         order.delete()
    #         return HttpResponseRedirect(next)

    return render(request, 'supplies/agreementDetail.html',
                  {'title': f'Договір № {agreement.description}', 'agreement': agreement, 'supplies': supplies_in_agreement, 'orders': orders_in_agreement,
                   'cartCountData': cartCountData, 'isOrders': True})



@login_required(login_url='login')
def preorderDetail(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all().order_by('id')
    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/preorderDetail.html',
                  {'title': f'Передзамовлення № {order_id}', 'order': order, 'supplies': supplies_in_order,
                   'cartCountData': cartCountData, 'isOrders': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def preorderDetail_generateOrder(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all().order_by('id')
    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':
        checkBoxSuppIdList = request.POST.getlist('flexCheckDefault')
        count_list = request.POST.getlist('count_list')
        count_list_id = request.POST.getlist('count_list_id')
        print("POST ---")



        count_for_id_dict = dict(zip(count_list_id, count_list))
        result = {k: v for k, v in count_for_id_dict.items() if k in checkBoxSuppIdList}

        chekedSups = []
        for sup in checkBoxSuppIdList:
            supp = Supply.objects.get(id=int(sup))
            count = int(result[sup])
            supp.count = count
            chekedSups.append(supp)

        supDict = {}
        for d in chekedSups:
            t = supDict.setdefault(d.general_supply, [])
            t.append(d)

        if supDict:
            new_order = Order(userCreated=request.user, for_preorder=order, place=order.place)
            new_order.save()
            for key, value in supDict.items():
                print("------------------------")
                print(key)
                allCount = 0
                genSupInPreorder = supplies_in_order.get(generalSupply_id=key)

                for s in value:
                    allCount += s.count

                    supInOrder = SupplyInOrder(count_in_order=s.count,
                                               generalSupply=s.general_supply,
                                               supply=s,
                                               supply_in_preorder=genSupInPreorder,
                                               supply_for_order=new_order,
                                               lot=s.supplyLot,
                                               date_expired=s.expiredDate,
                                               date_created=s.dateCreated,
                                               internalName=s.general_supply.name,
                                               internalRef=s.general_supply.ref
                                               )
                    supInOrder.save()
                    s.countOnHold += s.count
                    s.save(update_fields=['countOnHold'])

            t = threading.Thread(target=sendTeamsMsgCart, args=[new_order], daemon=True)
            t.start()
            return redirect('/orders')

        else:
            messages.info(request, "Жодний товар не вибраний для формування замовлення!")


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
                  {'title': f'Клієнти', 'clients': place, 'placeFilter': placeFilter, 'cartCountData': cartCountData,
                   'isClients': True})


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
                  {'title': f'Сервiсні записи', 'serviceNotes': serviceNotes, 'cartCountData': cartCountData,
                   'form': form, 'serviceFilters': serviceFilters, 'isService': True})
