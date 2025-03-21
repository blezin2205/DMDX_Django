import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from .decorators import unauthenticated_user, allowed_users
from .models import *
from .serializers import *
from datetime import date
from django.contrib.auth import authenticate, login, logout
from .filters import *
from .forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.core.paginator import Paginator
from django.db.models import *
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
from collections import defaultdict
import os
from xlsxwriter.workbook import Workbook
from django_htmx.http import trigger_client_event
from django.contrib import messages
import requests
import csv
import pymsteams
from django.db.models import Sum, F
from .tasks import *
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from firebase_admin import storage
from django.template.loader import render_to_string

# @login_required(login_url='login')
# @allowed_users(allowed_roles=['admin'])
# def receive_and_load_new_supplies_order(request):

def celery_test(request):
    task = go_to_sleep.delay(1)
    return render(request, 'supplies/misc/celery-test.html', {'task_id': task.task_id})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def app_settings(request):
    app_settings, created = AppSettings.objects.get_or_create(userCreated=request.user)

    if request.method == 'POST':
        form = AppSettingsForm(request.POST, instance=app_settings)
        if form.is_valid():
            form.save()
            return redirect('/')
    else:
        form = AppSettingsForm(instance=app_settings)

    return render(request, 'supplies/settings/app_settings.html', {'form': form})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def np_info_sync_ref_post_request(request):
    np_ref = request.POST.get('np_ref')
    print(np_ref)
    button = '<button class="btn btn-sm btn-success ms-2"><i class="bi bi-check-square"></i></button>'
    return HttpResponse(button)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def np_info_table_sync_for_user(request):
    user = request.user

    if request.method == 'POST':
        np_ref = request.POST.get('np_ref')
        user.np_contact_sender_ref = np_ref
        user.save(update_fields=['np_contact_sender_ref'])

    current_ref = user.np_contact_sender_ref
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

    return render(request, "supplies/nova_poshta/np_info_table_sync_for_user.html", {'data': data["data"], 'current_ref': current_ref})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def chartOfSoldSupplies(request):

    # sups = SupplyInOrder.objects.filter(generalSupply__isnull=False, generalSupply__category_id=1).values(
    #     'generalSupply'
    # ).annotate(
    #     total_count_in_order=Sum('count_in_order')
    # ).order_by(
    #     'generalSupply'
    # )

    # supply_in_order_list = []
    # for sup in sups:
    #     general_supply_id = sup['generalSupply']
    #     total_count_in_order = sup['total_count_in_order']
    #     supply_in_order = SupplyInOrder.objects.filter(generalSupply_id=general_supply_id).first()
    #     supply_in_order.count_in_order = total_count_in_order
    #     supply_in_order_list.append(supply_in_order)

    # # supply_in_order_list = sorted(supply_in_order_list, key=lambda x: x.count_in_order)
    # fig = px.bar(
    #     x=[item.generalSupply.name for item in supply_in_order_list],
    #     y=[item.count_in_order for item in supply_in_order_list],
    #     title="Supplies in Orders",
    #     labels={'x': 'name', 'y': 'count'}
    # )

    # fig.update_layout(title={
    #     'font_size': 22,
    #     'xanchor': 'center',
    #     'x': 0.5
    # })

    # chart = fig.to_html()
    context = {}
    return render(request, "supplies/misc/chart-sold.html", context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def load_xms_data(request):
    print('Hello')
    counter = 0

    blobs = storage.bucket().list_blobs()


    files = []
    for blob in blobs:
        print(blob)
        print(blob.public_url)

    file_url = ''


    if request.POST:
        file = request.FILES["excel_file"]
        file_name = default_storage.save(file.name, ContentFile(file.read()))
        blob = storage.bucket().blob(file.name)
        blob.upload_from_string(file.read(), content_type=file.content_type)

        file_url = blob.generate_signed_url(expiration=3600)
        print("FILE URL = ", file_url)





    return render(request, 'supplies/misc/load_xms_data.html', {'counter': counter, 'file_url': file_url})



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
    # for obj in vals:
    #     ref = obj[0]
    #     print('----------------------------------')
    #     print(obj)
        # smn = str(obj[2]).removesuffix('.0')
        # name = str(obj[1])
        # packed = obj[2]
        # tests = obj[5]
        # tests = obj[5]
        # if name != 'nan':
        #     print(name, ref, packed)
        #     genSup = GeneralSupply(name=name, ref=ref, package_and_tests=packed, category_id=5)
        #     genSup.save()

@login_required(login_url='login')
def register_exls_selected_buttons(request):
    cheked = False
    if request.method == 'POST':
        selected_orders = request.POST.getlist('register_exls_selected_buttons')
        cheked = len(selected_orders) > 0
    return render(request, 'partials/register_butons_for_seelcted_orders.html', {'cheked': cheked})

@login_required(login_url='login')
def countCartItemsHelper(request):
    app_settings, created = AppSettings.objects.get_or_create(userCreated=request.user)
    isClient = request.user.groups.filter(name='client').exists()
    preorders_await = 0
    preorders_partial = 0
    order_to_send_today = 0
    expired_orders = 0
    is_one_cart = ''

    if app_settings.enable_show_other_booked_cart:
        booked_carts = BookedOrderInCart.objects.all()
    else:
        booked_carts = BookedOrderInCart.objects.filter(place__user=request.user)

    carts_count = booked_carts.count()
    if 2 > carts_count > 0:
        is_one_cart = "IS_ONE"
    elif carts_count > 1:
        is_one_cart = "IS_MANY"
    booked_cart_first = booked_carts.first()

    if isClient:
        booked_carts = booked_carts.filter(place__user=request.user)
        carts_count = booked_carts.count()
        if 2 > carts_count > 0:
            is_one_cart = "IS_ONE"
        elif carts_count > 1:
            is_one_cart = "IS_MANY"
        booked_cart_first = booked_carts.first()



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
        order_to_send_today = Order.objects.filter(dateToSend=date.today(), isComplete=False).count()
        expired_orders = Order.objects.filter(dateToSend__lt=date.today(), isComplete=False).count()




    return {'cart_items': cart_items,
            'precart_items': precart_items,
            'orders_incomplete': orders_incomplete,
            'preorders_incomplete': preorders_incomplete,
            'preorders_await': preorders_await,
            'preorders_partial': preorders_partial,
            'order_to_send_today': order_to_send_today,
            'expired_orders': expired_orders,
            'is_one_cart': is_one_cart,
            'booked_cart_first': booked_cart_first
            }

@login_required(login_url='login')
def full_image_view_for_device_image(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    return render(request, 'supplies/devices/full_image_view_for_device_image.html', {'device': device})


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
def deleteSupplyInOrderNPDocumentButton(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']
    print(action)

    if action == 'delete':
        statusParsel = StatusNPParselFromDoucmentID.objects.get(pk=prodId)
        npDocument = NPDeliveryCreatedDetailInfo.objects.get(document_id=statusParsel.docNumber)

        params = {
            "apiKey": "99f738524ca3320ece4b43b10f4181b1",
            "modelName": "InternetDocument",
            "calledMethod": "delete",
            "methodProperties": {
                "DocumentRefs": npDocument.ref
            }
        }
        data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
        print(data)

        statusParsel.delete()
        npDocument.delete()
        print("NP DOCUMENT ACTION TO DELETE")
        print(prodId)

    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def deleteSupplyInOrder(request):
    prodId = request.POST.get('del_sup_id')
    suppInOrder = SupplyInOrder.objects.get(id=prodId)
    for_order = suppInOrder.supply_for_order

    if suppInOrder.supply_in_booked_order:
        suppInOrder.supply_in_booked_order.countOnHold -= suppInOrder.count_in_order
        suppInOrder.supply_in_booked_order.save(update_fields=['countOnHold'])
    elif suppInOrder.hasSupply():
        supp_for_supp_in_order = suppInOrder.supply
        supp_for_supp_in_order.countOnHold -= suppInOrder.count_in_order
        supp_for_supp_in_order.save(update_fields=['countOnHold'])

    # for_preorder = suppInOrder.supply_for_order.for_preorder or None
    #
    # if for_preorder:
    #     sup_in_preorder = for_preorder.supplyinpreorder_set.get(generalSupply=suppInOrder.generalSupply)
    #     sup_in_preorder.count_in_order_current -= suppInOrder.count_in_order
    #     if sup_in_preorder.count_in_order_current >= sup_in_preorder.count_in_order:
    #         sup_in_preorder.state_of_delivery = 'Complete'
    #     elif sup_in_preorder.count_in_order_current != 0 and sup_in_preorder.count_in_order_current < sup_in_preorder.count_in_order:
    #         sup_in_preorder.state_of_delivery = 'Partial'
    #     else:
    #         sup_in_preorder.state_of_delivery = 'Awaiting'
    #
    #     sup_in_preorder.save(update_fields=['count_in_order_current', 'state_of_delivery'])

    if for_order.supplyinorder_set.count() == 0:
       for_order.delete()
    else:
        suppInOrder.delete()

    return HttpResponse(status=200)


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
    response = render(request, 'partials/cart/add_precart_button_general.html',
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

    response = render(request, 'supplies/orders/preorder_detail_list_item.html', {'el': gen_sup_in_preorder, 'order': gen_sup_in_preorder.supply_for_order})
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
    response = render(request, 'partials/cart/add_cart_button.html',
                      {'cartCountData': cartCountData, 'supp': supply, 'deltaCount': deltaCountOnHold,
                       'countInCart': countInCart, 'deltaCountOnCart': deltaCountOnCart})
    trigger_client_event(response, 'subscribe', {})
    return response


def updateCartItemCount(request):
    cartCountData = countCartItemsHelper(request)
    return render(request, 'partials/cart/cart-badge.html', {'cartCountData': cartCountData})


def updatePreCartItemCount(request):
    cartCountData = countCartItemsHelper(request)
    return render(request, 'partials/cart/precart-badge.html', {'cartCountData': cartCountData})


@login_required(login_url='login')
def update_order_count(request):
    prodId = request.POST.get('del_sup_id')
    action = request.POST.get('action')
    counter = request.POST.get('counter')

    print('Action', action)
    print('id', prodId)
    print('counter', counter)
    supply = SupplyInOrder.objects.get(id=prodId)
    for_order = supply.supply_for_order

    if action == 'plus':
        if supply.supply_in_booked_order:
            supply.count_in_order += 1
            supply.supply_in_booked_order.countOnHold += 1
            supply.supply_in_booked_order.save(update_fields=['countOnHold'])
            supply.save(update_fields=['count_in_order'])
        else:
            supply.count_in_order += 1
            supply.supply.countOnHold += 1
            supply.supply.save(update_fields=['countOnHold'])
            supply.save(update_fields=['count_in_order'])

    elif action == 'minus':
        if supply.supply_in_booked_order:
            supply.count_in_order -= 1
            supply.supply_in_booked_order.countOnHold -= 1
            supply.supply_in_booked_order.save(update_fields=['countOnHold'])
            supply.save(update_fields=['count_in_order'])
        else:
            supply.count_in_order -= 1
            supply.supply.countOnHold -= 1
            supply.supply.save(update_fields=['countOnHold'])
            supply.save(update_fields=['count_in_order'])
        if supply.count_in_order <= 0:
            supply.delete()
            return HttpResponse(status=200)
        if for_order.supplyinorder_set.count() == 0:
           for_order.delete()
           return HttpResponse(status=200)

    return render(request, 'partials/orders/orderDetail_cell_item.html', {'el': supply, 'counter': counter})


@login_required(login_url='login')
def orderTypeDescriptionField(request):
    orderType = request.POST.get('orderType')
    isAgreement = orderType == 'Agreement'
    return render(request, 'partials/orders/orderTypeDescriptionField.html', {'isAgreement': isAgreement})

@login_required(login_url='login')
def add_to_exist_order_from_cart(request):
    orderType = request.POST.get('orderType')
    isAdd_to_exist_order = orderType == 'add_to_Exist_order'
    orders = []
    if isAdd_to_exist_order:
        place_id = request.POST.get('place_id')
        print("PLACE ID = ", place_id)
        place = Place.objects.get(pk=place_id)
        orders = place.order_set.filter(isComplete=False)
    return render(request, 'partials/cart/add_to_exist_order_from_cart.html', {'isAdd_to_exist_order': isAdd_to_exist_order, 'orders': orders})


@login_required(login_url='login')
def orderTypeDescriptionField_for_client(request):
    orderType = request.POST.get('orderType')
    place_id_Selected = request.POST.get('place_id')
    isAddedToExistPreorder = orderType == 'add_to_Exist_preorder'
    preorders = PreOrder.objects.filter(place_id=place_id_Selected).filter(Q(state_of_delivery='awaiting_from_customer') | Q(state_of_delivery='accepted_by_customer') | Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial'))

    return render(request, 'partials/orders/orderTypeDescriptionField_for_client.html', {'isAddedToExistPreorder': isAddedToExistPreorder, 'preorders': preorders})



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

from itertools import chain
from django_user_agents.utils import get_user_agent

@login_required(login_url='login')
def home(request):
    user_agent = get_user_agent(request)
    if user_agent.is_mobile:
        # Render mobile template
        print("MOBILE VERSION")
    else:
        print("DESKTOP VERSION")

    uncompleteOrdersExist = Order.objects.filter(isComplete=False).exists()
    isClient = request.user.groups.filter(name='client').exists() and not request.user.is_staff
    booked_list_exist = False
    if isClient:
        user_places = request.user.place_set.all()
        user_allowed_categories = set()
        for plc in user_places:
            categories = plc.allowed_categories.values_list('id', flat=True)
            # user_allowed_categories.add(categories.values())
            booked_list_exist = SupplyInBookedOrder.objects.filter(supply_for_place=plc).exists()
            for quer in categories:
                user_allowed_categories.add(quer)

        uncompletePreOrdersExist = PreOrder.objects.filter(isComplete=False, place__user=request.user).exists()
        html_page = 'supplies/home/home_for_client.html'
        supplies = GeneralSupply.objects.filter(category_id__in=user_allowed_categories).order_by('name')
        suppFilter = SupplyFilter(request.GET, queryset=supplies)
        category = Category.objects.filter(id__in=user_allowed_categories)
        suppFilter.form.fields['category'].queryset = category

    else:
        supplies = GeneralSupply.objects.all().order_by('name')
        suppFilter = SupplyFilter(request.GET, queryset=supplies)
        uncompletePreOrdersExist = PreOrder.objects.filter(isComplete=False).exists()
        html_page = 'supplies/home/home.html'

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

#     auth_token = 'b38b9b168929ecd6568ceede5432f2cd7b12d1c8'
#     hed = {'Authorization': 'Bearer ' + auth_token}
#     data = {
#    "recipients": [
#       "380503346204",
#       "380992438918",
#    ],
#    "sms": {
#       "sender": "DIAMEDIX",
#       "text": "Diamedix Top!!!!!!!!"
#    }
# }
#
#     url = 'https://api.turbosms.ua/message/send.json'
#     response = requests.post(url, json=data, headers=hed)
#     print(response)
#     print(response.json())

    # subject = 'welcome to GFG world'
    # message = f'Hi, thank you for registering in geeksforgeeks.'
    # email_from = settings.EMAIL_HOST_USER
    # recipient_list = ['oleksandr.stepanov@diamedix.ro']
    # send_mail(subject, message, email_from, recipient_list)

    return render(request, html_page, {'title': 'Всі товари',
                                                  'cartCountData': cartCountData,
                                                  'supplies': page_obj, 'suppFilter': suppFilter,
                                                  'isHome': True,
                                                  'isAll': True,
                                                   'booked_list_exist': booked_list_exist,
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
def sendTeamsMsg(request, order):
    app_settings, created = AppSettings.objects.get_or_create(userCreated=request.user)
    if app_settings.send_teams_msg_preorders:
        myTeamsMessage = pymsteams.connectorcard(
            settings.TEAMS_WEBHOOK_URL_PREORDERS)
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
    total_count_in_cart = supplies.aggregate(total_count=Sum('count_in_order'))['total_count']
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
            preorderType = request.POST.get('preorderType')
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

                teams_channel = settings.TEAMS_WEBHOOK_URL_PREORDERS

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
                isPreorder = preorderType == 'new_preorder'
                state_of_delivery = 'awaiting_from_customer'
                if isComplete:
                    dateSent = timezone.now().date()
                    state_of_delivery = 'accepted_by_customer'
                else:
                    dateSent = None
                order = PreOrder(userCreated=orderInCart.userCreated, place=place, dateSent=dateSent,
                                 isComplete=isComplete, isPreorder=isPreorder,
                                 comment=comment, state_of_delivery=state_of_delivery)
                order.save()
                print("----------------PREORDER-------------------")
                print(state_of_delivery)

                for index, sup in enumerate(supplies):
                    count = request.POST.get(f'count_{sup.id}')
                    general_sup = sup.general_supply
                    suppInOrder = SupplyInPreorder(count_in_order=count,
                                                   generalSupply=general_sup,
                                                   supply_for_order=order)

                    suppInOrder.save()

                t = threading.Thread(target=sendTeamsMsg, args=[request, order], daemon=True)
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

                for index, sup in enumerate(supplies):
                    count = request.POST.get(f'count_{sup.id}')
                    general_sup = sup.general_supply


                    try:
                        exist_sup = sups_in_preorder.get(generalSupply=general_sup)
                        exist_sup.count_in_order += int(count)
                        exist_sup.save()
                    except:
                        suppInOrder = SupplyInPreorder(count_in_order=count,
                                                       generalSupply=general_sup,
                                                       supply_for_order=selectedPreorder)
                        suppInOrder.save()


        orderInCart.delete()

        return redirect('/preorders')

    return render(request, 'supplies/cart/preorder-cart.html',
                  {'title': f'Корзина передзамовлення ({total_count_in_cart} шт.)', 'order': orderInCart, 'cartCountData': cartCountData,
                   'supplies': supplies, 'cities': cities, 'total_count_in_cart': total_count_in_cart,
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

    return render(request, 'supplies/cart/cart.html',
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

    return render(request, 'supplies/nova_poshta/add_new_sender_np_place.html', {'places': places})




@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl', 'client'])
def choose_preorder_in_cart_for_client(request):
    try:
        place = request.GET.get('place_id')
        preorders = Place.objects.get(id=place).preorder_set.filter(isComplete=False)
    except:
        place = None
        preorders = None

    return render(request, 'partials/cart/choose_preorder_in_cart_for_client.html',
                  {'preorders': preorders, 'placeChoosed': place != None})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def get_place_for_city_in_precart(request):
    city_id = request.GET.get('city')
    try:
        places = Place.objects.filter(city_ref_id=city_id)
    except:
        places = None

    return render(request, 'partials/cart/choose_place_in_cart_not_precart.html', {'places': places, 'cityChoosed': places != None, 'placeChoosed': False})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def get_place_for_city_in_cart(request):
    city_id = request.GET.get('city')
    try:
        places = Place.objects.filter(city_ref_id=city_id)
    except:
        places = None

    return render(request, 'partials/cart/choose_place_in_cart.html',
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



    return render(request, 'partials/cart/choose_uncompleted_order_in_cart.html', {'orders': orders, 'place': place, 'preorders': preorders, 'isPlaceChoosed': place != None})

@login_required(login_url='login')
def minus_from_preorders_detail_general_item(request):
    el_id = request.GET.get('el_id')
    for_preorder_id = request.GET.get('for_preorder_id')
    gen_sup_in_preorder = SupplyInPreorder.objects.get(id=el_id, supply_for_order_id=for_preorder_id)
    gen_sup_in_preorder.count_in_order -= 1
    if gen_sup_in_preorder.count_in_order == 0:
        gen_sup_in_preorder.delete()
        return HttpResponse(status=200)
    else:
        gen_sup_in_preorder.save(update_fields=['count_in_order'])

    print(el_id)
    print(for_preorder_id)
    return render(request, 'supplies/preorder_detail_list_item.html', {'el': gen_sup_in_preorder, 'order': gen_sup_in_preorder.supply_for_order})

@login_required(login_url='login')
def plus_from_preorders_detail_general_item(request):
    el_id = request.GET.get('el_id')
    for_preorder_id = request.GET.get('for_preorder_id')
    gen_sup_in_preorder = SupplyInPreorder.objects.get(id=el_id, supply_for_order_id=for_preorder_id)
    gen_sup_in_preorder.count_in_order += 1
    gen_sup_in_preorder.save(update_fields=['count_in_order'])

    print(el_id)
    print(for_preorder_id)
    return render(request, 'supplies/preorder_detail_list_item.html', {'el': gen_sup_in_preorder, 'order': gen_sup_in_preorder.supply_for_order})

@login_required(login_url='login')
def delete_from_preorders_detail_general_item(request, el_id):
    gen_sup_in_preorder = SupplyInPreorder.objects.get(id=el_id)
    gen_sup_in_preorder.delete()
    return HttpResponse(status=200)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def get_agreement_for_place_for_city_in_cart(request):
    place_id = request.GET.get('place_id')
    place = Place.objects.get(pk=place_id)
    agreements = place.preorder_set.filter(Q(state_of_delivery='awaiting_from_customer') | Q(state_of_delivery='accepted_by_customer'))

    return render(request, 'partials/cart/choose_agreement_forplace_incart.html', {'agreements': agreements, 'isPendingPreorderExist': agreements.exists(), 'isPlaceChoosed': True})


def sendTeamsMsgCart(request, order):
    app_settings, created = AppSettings.objects.get_or_create(userCreated=request.user)
    if app_settings.send_teams_msg:
        agreementString = ''
        if order.for_preorder:
            agreementString = f'Передзамовлення № {order.for_preorder.id}'

        myTeamsMessage = pymsteams.connectorcard(settings.TEAMS_WEBHOOK_URL_ORDERS)
        myTeamsMessage.title(f'Замовлення №{order.id},\n\n{order.place.name}, {order.place.city_ref.name}')

        myTeamsMessage.addLinkButton("Деталі замовлення", f'https://dmdxstorage.herokuapp.com/orders/{order.id}/0')
        myTeamsMessage.addLinkButton("Excel", f'https://dmdxstorage.herokuapp.com/order-detail-csv/{order.id}')
        created = f'*створив:*  **{order.userCreated.first_name} {order.userCreated.last_name}**'
        if order.comment:
            comment = f'*коментар:*  **{order.comment}**'
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
    total_count_in_cart = supplies.aggregate(total_count=Sum('count_in_order'))['total_count']
    orderForm = OrderInCartForm(request.POST or None)
    cities = City.objects.all()
    if request.method == 'POST':
        place_id = request.POST.get('place_id')
        place = Place.objects.get(id=place_id)
        orderType = request.POST.get('orderType')
        if 'delete' in request.POST:
            next = request.POST.get('next')
            orderInCart.delete()
            return HttpResponseRedirect(next)
        if 'save' in request.POST:
            
            if orderForm.is_valid():
                comment = orderForm.cleaned_data['comment']
                dateToSend = orderForm.cleaned_data['dateToSend']
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
                                  comment=comment, dateToSend=dateToSend)
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

                    t = threading.Thread(target=sendTeamsMsgCart, args=[request, order], daemon=True)
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

        if 'save_as_booked_order' in request.POST:
            for sup in supplies:
                count = int(request.POST.get(f'count_{sup.id}'))
                try:
                    supInOrder = SupplyInBookedOrder.objects.get(supply=sup.supply, supply_for_place=place)
                    supInOrder.count_in_order += count
                except:
                    supInOrder = SupplyInBookedOrder(
                        count_in_order=count,
                        generalSupply=sup.supply.general_supply,
                        supply=sup.supply,
                        supply_for_place=place,
                        lot=sup.supply.supplyLot,
                        date_expired=sup.supply.expiredDate,
                        internalName=sup.supply.general_supply.name,
                        internalRef=sup.supply.general_supply.ref
                    )
                supInOrder.save()
                sup.supply.countOnHold += count
                sup.supply.save(update_fields=['countOnHold'])

            orderInCart.delete()
            return redirect(f'/clientsInfo/{place_id}/booked_supplies_list')
    return render(request, 'supplies/cart/cart.html',
                  {'title': f'Корзина ({total_count_in_cart} шт.)', 'order': orderInCart, 'cartCountData': cartCountData, 'supplies': supplies,
                   'orderForm': orderForm, 'cities': cities, 'total_count_in_cart': total_count_in_cart,
                   })


@login_required(login_url='login')
def childSupply(request):
    supplies = Supply.objects.all().order_by('name')
    suppFilter = ChildSupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs
    print("HOME CHILD")

    if 'xls_button' in request.GET:
        supplies = supplies.annotate(available_count=ExpressionWrapper(
        F('count') - F('countOnHold'),
        output_field=IntegerField(),
        )).filter(available_count__gt=0).order_by('name')

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f"attachment; filename=Supply_List.xlsx"

        row_num = 3

        wb = Workbook(response, {'in_memory': True})
        ws = wb.add_worksheet('Supply-List')
        format = wb.add_format({'bold': True})
        format.set_font_size(16)

        columns_table = [{'header': '№'},
                         {'header': 'Назва товару'},
                         {'header': 'Пакування/Тести'},
                         {'header': 'SMN Code'},
                         {'header': 'REF'},
                         {'header': 'LOT'},
                         {'header': 'К-ть'},
                         {'header': 'Тер.прид.'},
                         {'header': 'Категорія'},
                         {'header': 'Оновлено'},
                         ]

        ws.write(0, 0,
                 f'Загальний список товарів (Без броні)',
                 format)

        format = wb.add_format({'num_format': 'dd.mm.yyyy'})
        format.set_font_size(12)

        for row in supplies:
            row_num += 1
            name = ''
            smn = ''
            package = ''
            ref = ''
            lot = ''
            category = ''
            if row.name:
                name = row.name
            if row.general_supply:
                name = row.general_supply.name
                category = row.general_supply.category.name
                package = row.general_supply.package_and_tests
                if row.general_supply.ref:
                    ref = row.general_supply.ref
                if row.general_supply.SMN_code:
                    smn = row.general_supply.SMN_code
                if row.general_supply.package_and_tests:
                    package = row.general_supply.package_and_tests

            if row.supplyLot:
                lot = row.supplyLot
            count = row.count - row.countOnHold
            date_expired = row.expiredDate.strftime("%d.%m.%Y")
            date_created = row.dateCreated.strftime("%d.%m.%Y")

            val_row = [name, package, smn, ref, lot, count, date_expired, category, date_created]

            for col_num in range(len(val_row)):
                ws.write(row_num, 0, row_num - 3)
                ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 35)
        ws.set_column(2, 5, 15)
        ws.set_column(6, 7, 10)
        ws.set_column(7, 8, 12)

        ws.add_table(3, 0, suppFilter.qs.count() + 3, len(columns_table) - 1, {'columns': columns_table})
        wb.close()
        return response

    if 'all_xls_button' in request.GET:
        print("all_xls_button")

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f"attachment; filename=Supply_List.xlsx"

        row_num = 3

        wb = Workbook(response, {'in_memory': True})
        ws = wb.add_worksheet('Supply-List')
        format = wb.add_format({'bold': True})
        format.set_font_size(16)

        columns_table = [{'header': '№'},
                         {'header': 'Назва товару'},
                         {'header': 'Пакування/Тести'},
                         {'header': 'SMN Code'},
                         {'header': 'REF'},
                         {'header': 'LOT'},
                         {'header': 'К-ть'},
                         {'header': 'Тер.прид.'},
                         {'header': 'Категорія'},
                         {'header': 'Оновлено'},
                         ]

        ws.write(0, 0,
                 f'Загальний список товарів (Всі товари)',
                 format)

        format = wb.add_format({'num_format': 'dd.mm.yyyy'})
        format.set_font_size(12)

        for row in supplies:
            row_num += 1
            name = ''
            smn = ''
            package = ''
            ref = ''
            lot = ''
            category = ''
            if row.name:
                name = row.name
            if row.general_supply:
                name = row.general_supply.name
                category = row.general_supply.category.name
                package = row.general_supply.package_and_tests
                if row.general_supply.ref:
                    ref = row.general_supply.ref
                if row.general_supply.SMN_code:
                    smn = row.general_supply.SMN_code
                if row.general_supply.package_and_tests:
                    package = row.general_supply.package_and_tests

            if row.supplyLot:
                lot = row.supplyLot
            count = row.count
            date_expired = row.expiredDate.strftime("%d.%m.%Y")
            date_created = row.dateCreated.strftime("%d.%m.%Y")

            val_row = [name, package, smn, ref, lot, count, date_expired, category, date_created]

            for col_num in range(len(val_row)):
                ws.write(row_num, 0, row_num - 3)
                ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 35)
        ws.set_column(2, 5, 15)
        ws.set_column(6, 7, 10)
        ws.set_column(7, 8, 12)

        ws.add_table(3, 0, suppFilter.qs.count() + 3, len(columns_table) - 1, {'columns': columns_table})
        wb.close()
        return response

    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/home/homeChild.html',
                  {'title': 'Дочерні товари', 'supplies': supplies, 'cartCountData': cartCountData,
                   'suppFilter': suppFilter, 'isHome': True, 'isChild': True})


@login_required(login_url='login')
def historySupply(request):
    supplies = SupplyForHistory.objects.all().order_by('-id')
    suppFilter = HistorySupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    if 'xls_button' in request.GET:

        suppFilter = HistorySupplyFilter(request.POST, queryset=supplies)
        supplies = suppFilter.qs
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f"attachment; filename=Supplies_History_List.xlsx"

        wb = Workbook(response, {'in_memory': True})
        ws = wb.add_worksheet('Sup_History_List')
        format = wb.add_format({'bold': True})
        format.set_font_size(16)

        columns_table = [{'header': '№'},
                         {'header': 'ACTION'},
                         {'header': 'Назва товару'},
                         {'header': 'REF'},
                         {'header': 'LOT'},
                         {'header': 'К-ть'},
                         {'header': 'Тер.прид.'},
                         {'header': 'Категорія'},
                         {'header': 'Оновлено'},
                         ]

        ws.write(0, 0, f'Загальний список товарів', format)

        format = wb.add_format({'num_format': 'dd.mm.yyyy'})
        format.set_font_size(12)

        row_num = 3

        for row in supplies:
            row_num += 1
            action = row.get_action_type_value()
            name = ''
            ref = ''
            lot = ''
            category = ''
            if row.name:
                name = row.name
            if row.general_supply:
                name = row.general_supply.name
                ref = row.general_supply.ref
                category = row.general_supply.category.name

            if row.supplyLot:
                lot = row.supplyLot
            count = row.count
            date_expired = row.expiredDate.strftime("%d.%m.%Y")
            date_created = row.dateCreated.strftime("%d.%m.%Y")

            val_row = [action, name, ref, lot, count, date_expired, category, date_created]

            for col_num in range(len(val_row)):
                ws.write(row_num, 0, row_num - 3)
                ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 15)
        ws.set_column(2, 2, 35)
        ws.set_column(3, 4, 15)
        ws.set_column(5, 6, 10)
        ws.set_column(7, 8, 12)

        ws.add_table(3, 0, row_num, len(columns_table) - 1, {'columns': columns_table})
        wb.close()
        return response

    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/home/home-history.html',
                  {'title': 'Історія товарів', 'supplies': supplies, 'cartCountData': cartCountData,
                   'suppFilter': suppFilter, 'isHome': True, 'isHistory': True})




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

    return render(request, 'supplies/agreements/agreements.html',
                  {'title': title, 'orders': orders, 'cartCountData': cartCountData, 'isOrders': True,
                   'totalCount': totalCount,
                   'isAgreementsTab': True})


def get_selected_xls_orders_sups(supply_in_order_list: defaultdict):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Selected_Orders_List_{datetime.datetime.now().strftime('%d.%m.%Y  %H:%M')}.xlsx"
    wb = Workbook(response, {'in_memory': True})

    for order_list_info in supply_in_order_list:
        print(order_list_info)
        render_to_xls_selected_order(order_list_info[0][1], order_list_info[0][0], order_list_info[1], wb)
    wb.close()
    return response


def render_to_xls_selected_order(table_header, place, supplies_in_order, wb):

    row_num = 3
    row_num_to_table = 3

    ws = wb.add_worksheet(f'№{place.id}')
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
    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 35)
    ws.set_column(2, 3, 15)
    ws.set_column(4, 5, 20)
    ws.set_column(6, 6, 15)
    ws.set_column(7, 7, 5)
    ws.set_column(8, 8, 12)

    ws.write(0, 0,
             f'{place.name}, {place.city_ref.name}. Замовлення №: {table_header}',
             format)
    ws.write(2, 0, f'Всього: {len(supplies_in_order)} шт.', format)

    format = wb.add_format()
    format.set_font_size(14)
    ws.add_table(row_num, 0, len(supplies_in_order) + row_num, len(columns_table) - 1, {'columns': columns_table})

    for row in supplies_in_order:
        row_num += 1
        name = ''
        name = ''
        ref = ''
        smn = ''
        category = ''
        packtests = ''
        if row.general_supply:
            if row.general_supply.name:
                name = row.general_supply.name
            if row.general_supply.ref:
                ref = row.general_supply.ref
            if row.general_supply.SMN_code:
                smn = row.general_supply.SMN_code
            if row.general_supply.category:
                category = row.general_supply.category
            if row.general_supply.package_and_tests:
                packtests = row.general_supply.package_and_tests
        lot = ''
        if row.supplyLot:
            lot = row.supplyLot
        count = row.count

        date_expired = row.expiredDate.strftime("%d-%m-%Y")

        val_row = [name, packtests, category, ref, smn, lot, count, date_expired]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - row_num_to_table)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

@login_required(login_url='login')
def orders(request):
    cartCountData = countCartItemsHelper(request)

    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        ordersObj = Order.objects.filter(place__user=request.user).order_by('-id')
        totalCount = ordersObj.count()
        title = f'Всі замовлення для {request.user.first_name} {request.user.last_name}. ({totalCount} шт.)'

    else:
        ordersObj = Order.objects.all().order_by('isComplete', 'dateToSend', '-id')
        totalCount = ordersObj.count()
        title = f'Всі замовлення. ({totalCount} шт.)'

    orderFilter = OrderFilter(request.POST or None, queryset=ordersObj)
    orders = orderFilter.qs
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
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

        if 'export_to_excel_choosed' in request.POST:
            print('---------------------export_to_excel_choosed--------------------------------')
            selected_orders = request.POST.getlist('register_exls_selected_buttons')
            selected_orders = ordersObj.filter(id__in=selected_orders)
            # Step 1: Group orders by place
            orders_by_place = defaultdict(list)
            for order in selected_orders:
                orders_by_place[order.place].append(order)

            # Step 2: Iterate over each group of orders
            supply_in_order_list = defaultdict(list)
            for place, sel_orders in orders_by_place.items():
                supply_in_order_dict = defaultdict(int)
                sel_orders_ids = []
                for sel_order in sel_orders:
                    sel_orders_ids.append(str(sel_order.id))
                    # Step 2a: Collect associated SupplyInOrder instances and sum count_in_order
                    supply_in_orders = SupplyInOrder.objects.filter(supply_for_order=sel_order)
                    for supply_in_order in supply_in_orders:
                        key = supply_in_order.supply
                        supply_in_order_dict[key] += supply_in_order.count_in_order

                sel_orders_ids = ",".join(sel_orders_ids)
                # Step 3: Compile the result for each group into a single list
                for key, count in supply_in_order_dict.items():
                    supply_in_order = key
                    supply_in_order.count = count
                    supply_in_order_list[(place, sel_orders_ids)].append(supply_in_order)
            return get_selected_xls_orders_sups(supply_in_order_list.items())


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
                return render(request, 'supplies/orders/orders_new.html',
                              {'title': title, 'orders': orders, 'cartCountData': cartCountData, 'isOrders': True,
                               'totalCount': totalCount,
                               'isOrdersTab': True})


    return render(request, 'supplies/orders/orders_new.html',
                  {'title': title, 'orders': orders, 'orderFilter': orderFilter, 'cartCountData': cartCountData, 'isOrders': True, 'totalCount': totalCount,
                   'isOrdersTab': True})



def generate_list_of_xls_from_preorders_list(preorders_list, withChangedStatus = False, set_complete_ctatus = False, set_is_closed=False, all_items=False):
    selected_ids = map(int, preorders_list)
    fileteredOredrs = PreOrder.objects.filter(pk__in=selected_ids)
    if withChangedStatus:
        for ord in fileteredOredrs:
            if ord.state_of_delivery == 'accepted_by_customer':
                ord.state_of_delivery = 'Awaiting'
                ord.save(update_fields=['state_of_delivery'])
    if set_complete_ctatus:
        for ord in fileteredOredrs:
            ord.state_of_delivery = 'Complete_Handle'
            ord.save(update_fields=['state_of_delivery'])
        return
    if set_is_closed:
        for ord in fileteredOredrs:
            ord.isClosed = True
            ord.isComplete = True
            if ord.state_of_delivery != 'Complete':
                ord.state_of_delivery = 'Complete_Handle'
            ord.save(update_fields=['isClosed', 'isComplete', 'state_of_delivery'])
        return


    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Preorders_List_{datetime.datetime.now().strftime('%d.%m.%Y  %H:%M')}.xlsx"
    wb = Workbook(response, {'in_memory': True})
    for preorder in fileteredOredrs:
        preorder_render_to_xls_by_preorder(response, preorder, wb, all_items)
    wb.close()
    return response




def preorder_render_to_xls_by_preorder(response, order: PreOrder, wb: Workbook, all_items: bool):
    order_id = order.id
    supplies_in_order_all = order.supplyinpreorder_set.all()
    supplies_in_order = []
    if all_items:
        supplies_in_order = supplies_in_order_all
    else:
        for sup in supplies_in_order_all:
          if sup.count_in_order - sup.count_in_order_current - sup.get_booked_count() > 0:
            supplies_in_order.append(sup)
    row_num = 4
    init_row_num = row_num


    ws = wb.add_worksheet(f'Order №{order_id}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)
    if all_items:
        columns_table = [{'header': '№'},
                     {'header': 'Name'},
                     {'header': 'Category'},
                     {'header': 'Package / Tests'},
                     {'header': 'REF'},
                     {'header': 'SMN code'},
                     {'header': 'Count'},
                     # {'header': 'Index'}
                     ]
    else:
        columns_table = [{'header': '№'},
                     {'header': 'Name'},
                     {'header': 'Category'},
                     {'header': 'Package / Tests'},
                     {'header': 'REF'},
                     {'header': 'SMN code'},
                     {'header': 'Awaiting count'},
                     # {'header': 'Index'}
                     ]
    ws.write(0, 0,
             f'Замов. №{order_id} для {order.place.name[:30]}, {order.place.city_ref.name} від {order.dateCreated.strftime("%d-%m-%Y")}',
             format)

    format = wb.add_format()
    format.set_font_size(14)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 35)
    ws.set_column(2, 5, 20)
    ws.set_column(5, 6, 15)
    # ws.set_column(8, 8, 5)

    ws.add_table(row_num, 0, len(supplies_in_order) + row_num, len(columns_table) - 1, {'columns': columns_table})

    if order.comment:
        ws.write(1, 0, f'Коммент.: {order.comment}', format)
        ws.write(2, 0, f'Всього: {len(supplies_in_order)} шт.', format)
    else:
        ws.write(1, 0, f'Всього: {len(supplies_in_order)} шт.', format)



    for row in supplies_in_order:
        row_num += 1
        name = ''
        ref = ''
        smn = ''
        category = ''
        pckg_and_tests = ''
        if row.generalSupply:
            if row.generalSupply.name:
                name = row.generalSupply.name
            if row.generalSupply.ref:
                ref = row.generalSupply.ref
            if row.generalSupply.SMN_code:
                smn = row.generalSupply.SMN_code
            if row.generalSupply.category:
                category = row.generalSupply.category
            if row.generalSupply.package_and_tests:
                pckg_and_tests = row.generalSupply.package_and_tests

        count_in_order = row.count_in_order
        current_delivery_count = row.count_in_order_current
        if all_items:
            count_borg = count_in_order
        else:
            count_borg = row.count_in_order - row.count_in_order_current - row.get_booked_count()
        date_expired = ''

        val_row = [name, category, pckg_and_tests, ref, smn, count_borg]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - init_row_num)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)


@login_required(login_url='login')
def preorders(request):
    cartCountData = countCartItemsHelper(request)
    isArchiveChoosed = False

    isClient = request.user.groups.filter(name='client').exists()
    if isClient:
        if 'get_archive_preorders' in request.POST:
            isArchiveChoosed = True
            orders = PreOrder.objects.filter(place__user=request.user, isClosed=True).order_by('-id')
        else:
            orders = PreOrder.objects.filter(place__user=request.user, isClosed=False).order_by('-id')
        title = f'Всі передзамовлення для {request.user.first_name} {request.user.last_name}'
    else:
        if 'get_archive_preorders' in request.POST:
            isArchiveChoosed = True
            orders = PreOrder.objects.filter(isClosed=True).order_by('-state_of_delivery', '-id')
        else:
            orders = PreOrder.objects.filter(isClosed=False).order_by('-state_of_delivery', '-id')

        title = 'Всі передзамовлення'

    preorderFilter = PreorderFilter(request.POST, queryset=orders)
    orders = preorderFilter.qs

    if request.method == 'POST':
        selected_orders = request.POST.getlist('xls_preorder_print_buttons')
        if 'print_choosed' in request.POST:
            return generate_list_of_xls_from_preorders_list(selected_orders)
        if 'print_choosed_and_status_updated' in request.POST:
            return generate_list_of_xls_from_preorders_list(selected_orders, True)
        if 'mark_as_delivery_completed' in request.POST:
            generate_list_of_xls_from_preorders_list(selected_orders, False, True)
        if 'set_is_closed' in request.POST:
            generate_list_of_xls_from_preorders_list(selected_orders, False, False, True)

    return render(request, 'supplies/orders/preorders.html',
                  {'title': title, 'isArchiveChoosed': isArchiveChoosed, 'orders': orders, 'preorderFilter': preorderFilter, 'cartCountData': cartCountData, 'isOrders': True,
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

    return render(request, 'partials/preorders/preorders_cart_list.html',
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

    return render(request, 'partials/preorders/preorders-list.html',
                  {'orders': orders})


@login_required(login_url='login')
def updatePreorderStatus(request, order_id):
    order = PreOrder.objects.get(id=order_id)

    order.isComplete = True
    order.state_of_delivery = 'accepted_by_customer'
    order.dateSent = timezone.now().date()
    order.save()

    return render(request, 'partials/preorders/preorder_preview_cell.html', {'order': order})


def update_order_status_core(order_id, user):
    """
    Core function to update order status without template rendering.
    Returns the updated order object.
    """
    order = Order.objects.get(id=order_id)
    
    supps = order.supplyinorder_set.all()
    for el in supps:
        countInOrder = el.count_in_order
        supp = None
        if el.supply:
           supp = el.supply
           supp.countOnHold -= countInOrder
           supp.count -= countInOrder

        if el.supply_in_booked_order:
            supply_in_booked_order = el.supply_in_booked_order
            supply_in_booked_order.countOnHold -= countInOrder
            supply_in_booked_order.count_in_order -= countInOrder
            if supply_in_booked_order.count_in_order == 0:
                supply_in_booked_order.delete()
            else:
                supply_in_booked_order.save(update_fields=['countOnHold', 'count_in_order'])

        genSupInPreorder = el.supply_in_preorder
        if genSupInPreorder:
            genSupInPreorder.count_in_order_current += el.count_in_order
            if genSupInPreorder.count_in_order - genSupInPreorder.count_in_order_current <= 0:
                genSupInPreorder.state_of_delivery = 'Complete'
            else:
                genSupInPreorder.state_of_delivery = 'Partial'
            genSupInPreorder.save()

        if supp:
            if supp.count == 0:
                supp.delete()
            else:
                supp.save(update_fields=['countOnHold', 'count'])

    order.isComplete = True
    order.dateToSend = None
    order.dateSent = timezone.now().date()
    order.userSent = user
    order.save()

    preorder = order.for_preorder
    if preorder:
        sups_in_preorder = preorder.supplyinpreorder_set.all()
        if all(sp.state_of_delivery == 'Complete' for sp in sups_in_preorder):
            preorder.state_of_delivery = 'Complete'
        elif any(x.state_of_delivery == 'Partial' or 'Awaiting' for x in sups_in_preorder):
            preorder.state_of_delivery = 'Partial'
        preorder.save(update_fields=['state_of_delivery'])

    return order

@login_required(login_url='login')
def orderUpdateStatus(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        
        if order.isComplete:
            return JsonResponse({
                'error': True,
                'message': 'Цей замовлення вже завершено і не може бути оновлено. Оновіть сторінку.'
            }, status=400)
            
        order = update_order_status_core(order_id, request.user)
        
        user_agent = get_user_agent(request)
        if user_agent.is_mobile:
            template = 'supplies_mobile/order_cell.html'
        else:
            template = 'partials/orders/order_preview_cel.html'

        return render(request, template, {'order': order})
    except Exception as e:
        # Return error response with status code 400
        return JsonResponse({
            'error': True,
            'message': f'№{order.id}: ' + str(e)
        }, status=400)


@login_required(login_url='login')
def ordersForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    orders = place.order_set.all().order_by('-id')
    orderFilter = OrderFilter(request.GET, queryset=orders)
    orders = orderFilter.qs
    title = f'Всі замовлення для клієнта: \n {place.name}, {place.city_ref.name}'
    if not orders:
        title = f'В клієнта "{place.name}, {place.city_ref.name}" ще немає замовлень'

    return render(request, 'supplies/orders/orders_new.html', {'title': title, 'orders': orders, 'orderFilter': orderFilter, 'isClients': True})


@login_required(login_url='login')
def agreementsForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    cartCountData = countCartItemsHelper(request)
    title = f'Всі передзамовлення для клієнта: \n {place.name}, {place.city_ref.name}'
    isArchiveChoosed = False
    if 'get_archive_preorders' in request.POST:
        isArchiveChoosed = True
        orders = place.preorder_set.filter(isClosed=True).order_by('-state_of_delivery', '-id')
    else:
        orders = place.preorder_set.filter(isClosed=False).order_by('-state_of_delivery', '-id')

    preorderFilter = PreorderFilter(request.GET, queryset=orders)
    orders = preorderFilter.qs


    if request.method == 'POST':
        selected_orders = request.POST.getlist('xls_preorder_print_buttons')
        if 'print_choosed' in request.POST:
            return generate_list_of_xls_from_preorders_list(selected_orders)
        if 'print_choosed_and_status_updated' in request.POST:
            return generate_list_of_xls_from_preorders_list(selected_orders, True)
        if 'mark_as_delivery_completed' in request.POST:
            generate_list_of_xls_from_preorders_list(selected_orders, False, True)

    return render(request, 'supplies/preorders.html',
           {'title': title, 'orders': orders, 'preorderFilter': preorderFilter, 'cartCountData': cartCountData,
            'isOrders': True,
            'isArchiveChoosed': isArchiveChoosed,
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

    return render(request, 'supplies/devices/devices.html',
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
    return render(request, 'supplies/service/serviceNotes.html',
                  {'title': title, 'serviceNotes': serviceNotes, 'form': form, 'cartCountData': cartCountData,
                   'isClients': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'engineer'])
def createNote(request):
    form = ServiceNoteForm()
    # form.fields.pop("for_place")
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = CustomUser.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/service/createNote.html',
                  {'title': f'Створити новий запис', 'form': form, 'cartCountData': cartCountData,
                   'isService': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'engineer'])
def createNote_for_client(request, client_id):
    client = Place.objects.get(id=client_id)
    form = ServiceNoteForm(initial={'for_place': client})
    # form.fields.pop("for_place")

    if request.method == 'POST':
        form = ServiceNoteForm(request.POST, initial={'for_place': client})

        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = CustomUser.objects.get(pk=request.user.id)
            obj.for_place = client
            obj.save()
            return redirect('/serviceNotes')

    cartCountData = countCartItemsHelper(request)

    return render(request, 'supplies/service/createNote.html',
                  {'title': f'Створити новий запис', 'form': form, 'cartCountData': cartCountData,
                   'isHiddenPlace': True})


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

    return render(request, 'supplies/service/createNote.html',
                  {'title': f'Редагувати запис №{note_id}', 'form': form, 'cartCountData': cartCountData,
                   'isService': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateSupply(request, supp_id):
    note = Supply.objects.get(id=supp_id)
    generalSupp = note.general_supply
    form = SupplyForm(instance=note)

    cartCountData = countCartItemsHelper(request)

    if request.method == 'POST':
        next = request.POST.get('next')
        if 'save' in request.POST:
            form = SupplyForm(request.POST, instance=note)
            if form.is_valid():
                obj = form.save(commit=False)
                # obj.from_user = User.objects.get(pk=request.user.id)
                suppForHistory = obj.get_supp_for_history()
                suppForHistory.action_type = 'updated'
                suppForHistory.save()
                obj.save()
        elif 'delete' in request.POST:
            supp = Supply.objects.get(id=supp_id)
            suppForHistory = supp.get_supp_for_history()
            suppForHistory.action_type = 'deleted'
            suppForHistory.save()
            supp.delete()

        html = render_to_string('partials/supplies/supply_row.html', {
            'el': generalSupp,
            'request': request
        })
        return JsonResponse({
            'html': html,
            'generalSuppId': generalSupp.id,
            'success': True
        })

    return render(request, 'supplies/supplies/update_supply.html',
                  {'cartCountData': cartCountData, 'form': form,
                   'suppId': supp_id, 'editMode': True, 'generalSupp': generalSupp})


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

    return render(request, 'supplies/supplies/create_new_lot_modal.html',
                  {'cartCountData': cartCountData, 'form': orderForm, 'supplies': [supply], 'placeExist': True,
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

    return render(request, 'supplies/supplies/create_new_lot_modal.html',
                  {'cartCountData': cartCountData, 'form': orderForm, 'supplies': [supply], 'placeExist': True,
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

    return render(request, 'supplies/supplies/create_new_lot_modal.html',
                  {'cartCountData': cartCountData, 'form': orderForm, 'supplies': [supply],
                   })


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateGeneralSupply(request, supp_id):
    supp = GeneralSupply.objects.get(id=supp_id)
    form = NewGeneralSupplyForm(instance=supp)
    if request.method == 'POST':
        next = request.POST.get('next')
        if 'save' in request.POST:
            form = NewGeneralSupplyForm(request.POST, request.FILES, instance=supp)
            if form.is_valid():
                # obj = form.save(commit=False)
                # obj.from_user = User.objects.get(pk=request.user.id)
                form.save()
                next = request.POST.get('next')
            html = render_to_string('partials/supplies/supply_row.html', {
            'el': supp,
            'request': request
        })
            return JsonResponse({
            'html': html,
            'success': True
        })    

        elif 'delete' in request.POST:
            supp.delete()
            return JsonResponse({'success': True})

    return render(request, 'supplies/supplies/update_supply.html',
                  {'title': f'Редагувати запис №{supp_id}', 'form': form, 'generalSupp': supp})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def history_for_supply(request, supp_id):
    cartCountData = countCartItemsHelper(request)
    generalSupp = GeneralSupply.objects.get(id=supp_id)
    # supplies = generalSupp.supplyforhistory_set.all().order_by('-id')
    in_orders = generalSupp.inGeneralSupp.all().order_by('-id')
    total_count_in_orders = in_orders.aggregate(total_count=Sum('count_in_order'))['total_count']

    in_preorders = generalSupp.supplyinpreorder_set.all().order_by('-id')
    total_count_in_preorders = in_preorders.aggregate(total_count=Sum('count_in_order'))['total_count']

    in_deliveries = generalSupp.deliverysupplyincart_set.all().order_by('-id')
    total_count_in_deliveries = in_deliveries.aggregate(total_count=Sum('count'))['total_count']

    in_booked_sup = generalSupp.supplyinbookedorder_set.all().order_by('-id')
    total_count_in_booked_sup = in_booked_sup.aggregate(total_count=Sum('count_in_order'))['total_count']

    return render(request, 'supplies/history_for_supply_list.html',
                  {'generalSupp': generalSupp,
                   'supplies': in_orders,
                   'in_preorders': in_preorders,
                   'in_deliveries': in_deliveries,
                   'in_booked_sup': in_booked_sup,
                   'total_count_in_orders': total_count_in_orders,
                   'total_count_in_booked_sup': total_count_in_booked_sup,
                   'total_count_in_preorders': total_count_in_preorders,
                   'total_count_in_deliveries': total_count_in_deliveries,
                   'cartCountData': cartCountData})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def addNewLotforSupply(request, supp_id):
    form = SupplyForm()
    generalSupp = GeneralSupply.objects.get(id=supp_id)
    if request.method == 'POST':
        form = SupplyForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.general_supply = generalSupp
            obj.category = generalSupp.category
            obj.name = generalSupp.name
            obj.ref = generalSupp.ref
            next = request.POST.get('next')

            lot = form.cleaned_data['supplyLot']
            count = form.cleaned_data['count']
            expiredDate = form.cleaned_data['expiredDate']
            try:
                supIfExist = generalSupp.general.get(supplyLot=lot, expiredDate=expiredDate)
                supIfExist.count += count
                supIfExist.save()

            except:
                obj.save()

            supHistory = obj.get_supp_for_history()

            try:
                supForHistory = SupplyForHistory.objects.get(supplyLot=supHistory.supplyLot,
                                                             dateCreated=supHistory.dateCreated, expiredDate=supHistory.expiredDate)
                supForHistory.count += supHistory.count
                supForHistory.action_type = 'added-handle'
                supForHistory.save()

            except:
                supHistory.action_type = 'added-handle'
                supHistory.save()

            html = render_to_string('partials/supplies/supply_row.html', {
            'el': generalSupp,
            'request': request
        })
            return JsonResponse({
            'html': html,
            'success': True
        })
    return render(request, 'supplies/supplies/create_new_lot_modal.html',
                  {'form': form, 'generalSupp': generalSupp})


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

    return render(request, 'supplies/supplies/createSupply.html',
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

    return render(request, 'supplies/supplies/createSupply.html',
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

    return render(request, 'supplies/supplies/createSupply.html',
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

    return render(request, 'supplies/supplies/createSupply.html',
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
            isPrivatePlace = form.cleaned_data['isPrivatePlace']

            org = Place(name=name, city_ref=city_ref, address=address, link=link, isPrivatePlace=isPrivatePlace)

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
                    return render(request, 'supplies/nova_poshta/create_np_order_doucment.html',
                                  {'title': f'Додати нового клієнта', 'inputForm': form,
                                   'cartCountData': cartCountData})

            org.save()
            return redirect('/clientsInfo')
    return render(request, 'supplies/nova_poshta/create_np_order_doucment.html',
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

    return render(request, 'supplies/supplies/createSupply.html',
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

    return render(request, 'supplies/clients/addNewWorkerForClient.html',
                  {'title': f'Редагувати працівника для: \n{place.name}, {place.city_ref.name}', 'form': form,
                   'cartCountData': cartCountData, 'orgRefExist': orgRefExist})


@login_required(login_url='login')
def worker_card_info_delete_worker(request):
    worker_id = request.POST.get('worker_id')
    worker = Workers.objects.get(id=worker_id)
    worker.delete()
    return HttpResponse(status=200)

@login_required(login_url='login')
def worker_card_info_edit_action(request):
    worker_id = request.POST.get('worker_id')
    worker = Workers.objects.get(id=worker_id)
    return render(request, 'supplies/clients/editClientDetail_worker_edit_view.html',
                  {'worker': worker})


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

    return render(request, 'supplies/clients/editClientDetail.html',
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
    return render(request, 'supplies/clients/addNewWorkerForClient.html',
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
    template = get_template('supplies/orders/orderdetail-pdf.html')
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
        name = ''
        name = ''
        ref = ''
        smn = ''
        category = ''
        packtests = ''
        if row.generalSupply:
            if row.generalSupply.name:
                name = row.generalSupply.name
            if row.generalSupply.ref:
                ref = row.generalSupply.ref
            if row.generalSupply.SMN_code:
                smn = row.generalSupply.SMN_code
            if row.generalSupply.category:
                category = row.generalSupply.category
            if row.generalSupply.package_and_tests:
                packtests = row.generalSupply.package_and_tests
        lot = ''
        if row.lot:
            lot = row.lot
        count = row.count_in_order

        date_expired = row.date_expired.strftime("%d-%m-%Y")

        val_row = [name, packtests, category, ref, smn, lot, count, date_expired]

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
    return generate_list_of_xls_from_preorders_list([order_id])

def preorder_render_to_xls_all_items(request, order_id):
    return generate_list_of_xls_from_preorders_list([order_id], all_items=True)

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
def orderDetail_add_comment(request):
    order_id = request.POST.get("order_id")
    comment = request.POST.get("comment") or ""
    print("order_id = ", order_id)
    print("comment = ", comment)
    return render(request, 'partials/common/comment_input_textfield_area.html', {'order_id': order_id, 'comment': comment})


@login_required(login_url='login')
def orderDetail_save_comment(request):
    order_id = request.POST.get("order_id")
    comment_textfield = request.POST.get("comment_textfield")
    order = Order.objects.get(id=order_id)
    order.comment = comment_textfield
    order.save(update_fields=["comment"])

    print("order_id = ", order_id)
    print("comment_textfield = ", comment_textfield)
    return render(request, 'partials/common/comment_textfield_area.html', {'order': order})

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
                for suppInOrder in supps:
                    if suppInOrder.supply_in_booked_order:
                        suppInOrder.supply_in_booked_order.countOnHold -= suppInOrder.count_in_order
                        suppInOrder.supply_in_booked_order.save(update_fields=['countOnHold'])
                    elif suppInOrder.hasSupply():
                        supp_for_supp_in_order = suppInOrder.supply
                        supp_for_supp_in_order.countOnHold -= suppInOrder.count_in_order
                        supp_for_supp_in_order.save(update_fields=['countOnHold'])

                    # for_preorder = suppInOrder.supply_for_order.for_preorder or None
                    # if for_preorder:
                    #     sup_in_preorder = for_preorder.supplyinpreorder_set.get(generalSupply=suppInOrder.generalSupply)
                    #     sup_in_preorder.count_in_order_current -= suppInOrder.count_in_order
                    #     if sup_in_preorder.count_in_order_current >= sup_in_preorder.count_in_order:
                    #         sup_in_preorder.state_of_delivery = 'Complete'
                    #     elif sup_in_preorder.count_in_order_current != 0 and sup_in_preorder.count_in_order_current < sup_in_preorder.count_in_order:
                    #         sup_in_preorder.state_of_delivery = 'Partial'
                    #     else:
                    #         sup_in_preorder.state_of_delivery = 'Awaiting'
                    #
                    #     sup_in_preorder.save(update_fields=['count_in_order_current', 'state_of_delivery'])

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

    return render(request, 'supplies/orders/orderDetail.html',
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


    return render(request, 'partials/common/get_agreement_detail_for_cart.html',
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

    return render(request, 'supplies/agreements/agreementDetail.html',
                  {'title': f'Договір № {agreement.description}', 'agreement': agreement, 'supplies': supplies_in_agreement, 'orders': orders_in_agreement,
                   'cartCountData': cartCountData, 'isOrders': True})



@login_required(login_url='login')
def preorderDetail(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all()
    cartCountData = countCartItemsHelper(request)
    if order.isPreorder:
        title = f'Передзамовлення № {order_id}'
    else:
        title = f'Договір № {order_id}'

    return render(request, 'supplies/orders/preorderDetail.html',
                  {'title': title, 'order': order, 'supplies': supplies_in_order,
                   'cartCountData': cartCountData, 'isOrders': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def preorderDetail_generateOrder(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all().order_by('id')
    cartCountData = countCartItemsHelper(request)
    orderForm = OrderInCartForm(request.POST or None)

    if request.method == 'POST':
        checkBoxSuppIdList = request.POST.getlist('flexCheckDefault')
        count_list = request.POST.getlist('count_list')
        count_list_id = request.POST.getlist('count_list_id')
        booked_items_id = request.POST.getlist('booked_items_id')
        comment_for_order = request.POST.get('comment_for_order')
        count_for_id_dict = dict(zip(count_list_id, count_list))
        result = {k: v for k, v in count_for_id_dict.items() if k in checkBoxSuppIdList}

        print("-------------------- booked_items_id ----------------------")
        print(booked_items_id)

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


        sup_in_preorder_checked_for_booked = supplies_in_order.filter(id__in=booked_items_id)

        if 'create_order' in request.POST:
            if supDict or sup_in_preorder_checked_for_booked.count() > 0:
                new_order = Order(userCreated=request.user, for_preorder=order, place=order.place,
                                  comment=comment_for_order)
                if orderForm.is_valid():
                    comment = orderForm.cleaned_data['comment']
                    dateToSend = orderForm.cleaned_data['dateToSend']
                    new_order.comment = comment
                    new_order.dateToSend = dateToSend
                new_order.save()

                if sup_in_preorder_checked_for_booked.count() > 0:
                    for sup_in_booked in sup_in_preorder_checked_for_booked:
                        booked_sups = sup_in_booked.supplyinbookedorder_set.all()
                        for sup in booked_sups:
                            sup.countOnHold += sup.count_in_order
                            suppInOrder = SupplyInOrder(count_in_order=sup.count_in_order,
                                                        supply=sup.supply,
                                                        generalSupply=sup.supply.general_supply,
                                                        supply_for_order=new_order,
                                                        supply_in_preorder=sup_in_booked,
                                                        supply_in_booked_order=sup,
                                                        lot=sup.lot,
                                                        date_created=sup.date_created,
                                                        date_expired=sup.date_expired,
                                                        internalName=sup.supply.general_supply.name,
                                                        internalRef=sup.supply.general_supply.ref)
                            suppInOrder.save()
                            sup.save(update_fields=['countOnHold'])

                if supDict:
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

                t = threading.Thread(target=sendTeamsMsgCart, args=[request, new_order], daemon=True)
                t.start()
                return redirect('/orders')

            else:
               messages.info(request, "Жодний товар не вибраний для формування замовлення!")

        if 'create_booked_order' in request.POST:
            if supDict:
                for key, value in supDict.items():
                    genSupInPreorder = supplies_in_order.get(generalSupply_id=key)
                    for s in value:
                        try:
                            supInOrder = SupplyInBookedOrder.objects.get(supply=s, supply_in_preorder=genSupInPreorder, supply_for_place=order.place)
                            supInOrder.count_in_order += s.count
                        except:
                            supInOrder = SupplyInBookedOrder(
                                count_in_order=s.count,
                                generalSupply=s.general_supply,
                                supply=s,
                                supply_for_place=order.place,
                                supply_in_preorder=genSupInPreorder,
                                lot=s.supplyLot,
                                date_expired=s.expiredDate,
                                internalName=s.general_supply.name,
                                internalRef=s.general_supply.ref
                            )
                        supInOrder.save()
                        s.countOnHold += s.count
                        s.save(update_fields=['countOnHold'])

                return redirect(f'/clientsInfo/{order.place.id}/booked_supplies_list')
            else:
                messages.info(request, "Жодний товар не вибраний для формування замовлення!")

    return render(request, 'supplies/orders/preorderDetail-generate-order.html',
                  {'title': f'Передзамовлення № {order_id}', 'order': order, 'orderForm': orderForm, 'supplies': supplies_in_order,
                   'cartCountData': cartCountData, 'isOrders': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def clientsInfo(request):
    place = Place.objects.all().order_by('-id')
    placeFilter = PlaceFilter(request.GET, queryset=place)
    place = placeFilter.qs
    paginator = Paginator(place, 20)
    page_number = request.GET.get('page')
    place = paginator.get_page(page_number)
    cartCountData = countCartItemsHelper(request)
    return render(request, 'supplies/clients/clientsList.html',
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

    return render(request, 'supplies/service/serviceNotes.html',
                  {'title': f'Сервiсні записи', 'serviceNotes': serviceNotes, 'cartCountData': cartCountData,
                   'form': form, 'serviceFilters': serviceFilters, 'isService': True})
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def import_general_supplies_from_excel(request):
    if request.method == 'POST':
        if 'excel_file' in request.FILES:
            try:
                excel_file = request.FILES['excel_file']
                # Get column mappings from form
                name_col = int(request.POST.get('name_column', 0))
                ref_col = request.POST.get('ref_column')
                smn_code_col = request.POST.get('smn_code_column')
                package_tests_col = request.POST.get('package_tests_column')
                category_id = request.POST.get('category')
                
                # Read excel file
                import pandas as pd
                df = pd.read_excel(excel_file)
                
                success_count = 0
                update_count = 0
                error_count = 0
                error_messages = []
                
                # Get the selected category
                category = Category.objects.get(id=category_id)
                
                for index, row in df.iterrows():
                    try:
                        # Prepare data dictionary with required fields
                        supply_data = {
                            'name': row[name_col],
                            'category': category
                        }
                        
                        # Add optional fields only if they exist and are not empty
                        if ref_col and ref_col.strip() != '':
                            ref_col_num = int(ref_col)
                            if pd.notna(row[ref_col_num]):
                                supply_data['ref'] = str(row[ref_col_num])
                            
                        if smn_code_col and smn_code_col.strip() != '':
                            smn_code_col_num = int(smn_code_col)
                            if pd.notna(row[smn_code_col_num]):
                                supply_data['SMN_code'] = str(row[smn_code_col_num])
                            
                        if package_tests_col and package_tests_col.strip() != '':
                            package_tests_col_num = int(package_tests_col)
                            if pd.notna(row[package_tests_col_num]):
                                supply_data['package_and_tests'] = str(row[package_tests_col_num])
                        
                        # Check if GeneralSupply with this name exists
                        existing_supply = GeneralSupply.objects.filter(name=row[name_col], category=category).first()
                        
                        if existing_supply:
                            # Update existing supply
                            for key, value in supply_data.items():
                                setattr(existing_supply, key, value)
                            existing_supply.save()
                            update_count += 1
                        else:
                            # Create new supply
                            general_supply = GeneralSupply(**supply_data)
                            general_supply.save()
                            success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        error_messages.append(f"Row {index + 1}: {str(e)}")
                        print(f"Error on row {index}: {str(e)}")
                        continue

                if success_count > 0 or update_count > 0:
                    message = []
                    if success_count > 0:
                        message.append(f'Created {success_count} new items')
                    if update_count > 0:
                        message.append(f'Updated {update_count} existing items')
                    messages.success(request, ' | '.join(message))
                if error_count > 0:
                    messages.warning(request, f'Failed to process {error_count} items. Check the console for details.')
                return redirect('import_general_supplies_from_excel')
                
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
                return redirect('import_general_supplies_from_excel')
    
    # Get all categories for the dropdown
    categories = Category.objects.all().order_by('name')
    
    return render(request, 'supplies/supplies/import_general_supplies.html', {
        'title': 'Import General Supplies',
        'cartCountData': countCartItemsHelper(request),
        'categories': categories
    })


