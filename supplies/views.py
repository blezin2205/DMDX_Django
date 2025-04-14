import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
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
from django.db.models import Sum, F, Exists, OuterRef, Max, Case, When, Value, IntegerField, Q, BooleanField
from .tasks import *
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from firebase_admin import storage
from django.template.loader import render_to_string
from django.db import transaction
from .analytics import PreorderAnalytics
from django.utils import timezone


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
    param = {'apiKey': settings.NOVA_POSHTA_API_KEY,
             'modelName': 'Counterparty',
             'calledMethod': 'getCounterpartyContactPersons',
             'methodProperties': {'Ref': settings.NOVA_POSHTA_SENDER_DMDX_REF}}
    getListOfCitiesParams = {
        "apiKey": settings.NOVA_POSHTA_API_KEY,
        "modelName": "Address",
        "calledMethod": "getCities",
        "methodProperties": {
            "Page": "0"
        }
    }

    data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(param)).json()

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
    merge_button_available = False
    if request.method == 'POST':
        selected_orders = request.POST.getlist('register_exls_selected_buttons')
        cheked = len(selected_orders) > 0
        merge_button_available = len(selected_orders) > 1
    return render(request, 'partials/register_butons_for_seelcted_orders.html', {'cheked': cheked, 'merge_button_available': merge_button_available})

@login_required(login_url='login')
def countCartItemsHelper(request):
    app_settings, created = AppSettings.objects.get_or_create(userCreated=request.user)
    isClient = request.user.groups.filter(name='client').exists()
    preorders_await = 0
    preorders_partial = 0
    order_to_send_today = 0
    expired_orders = 0
    orders_pinned = 0
    orders_with_uncompleted_np = 0
    preorders_pinned = 0
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
        orders_with_uncompleted_np = StatusNPParselFromDoucmentID.objects.filter(status_code__in=['3', '4', '41', '5', '6', '7', '8', '10', '11', '12', '101', '102', '103', '104', '105', '106', '111', '112']).count()
        orders_pinned = Order.objects.filter(isPinned=True).count()
        preorders_pinned = PreOrder.objects.filter(isPinned=True).count()




    return {'cart_items': cart_items,
            'precart_items': precart_items,
            'orders_incomplete': orders_incomplete,
            'preorders_incomplete': preorders_incomplete,
            'preorders_await': preorders_await,
            'preorders_partial': preorders_partial,
            'order_to_send_today': order_to_send_today,
            'expired_orders': expired_orders,
            'is_one_cart': is_one_cart,
            'booked_cart_first': booked_cart_first,
            'orders_pinned': orders_pinned,
            'preorders_pinned': preorders_pinned,
            'orders_with_uncompleted_np': orders_with_uncompleted_np
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
            "apiKey": settings.NOVA_POSHTA_API_KEY,
            "modelName": "InternetDocument",
            "calledMethod": "delete",
            "methodProperties": {
                "DocumentRefs": npDocument.ref
            }
        }
        data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
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
    suggested_quantity = request.POST.get('suggested_quantity')  # Fixed parameter name
    place_id = request.POST.get('place_id')
    general_supply = GeneralSupply.objects.get(id=prodId)
    quantity = suggested_quantity if suggested_quantity else 1
    place = None
    print('PLACE ID = ', place_id)
    if place_id:
       print('PLACE ID 1 = ', place_id)
       place = Place.objects.get(id=place_id)
       preorderInCart = PreorderInCart.objects.filter(userCreated=user, isComplete=False).first()
       if preorderInCart:
          if preorderInCart.place:
             if preorderInCart.place != place:
                return HttpResponse('Спочатку завершіть створену корзину передзамовлення для організації: \n' + preorderInCart.place.name + ' ' + preorderInCart.place.city_ref.name , status=400)
          else:
            return HttpResponse('Спочатку завершіть створену корзину передзамовлення', status=400)    
       else:
            preorderInCart = PreorderInCart.objects.create(userCreated=user, isComplete=False, place=place)
    else:
       preorderInCart, created = PreorderInCart.objects.get_or_create(userCreated=user, isComplete=False)
       
    try:
        suppInCart = SupplyInPreorderInCart.objects.get(
                                        supply_for_order=preorderInCart,
                                        general_supply=general_supply)
        suppInCart.count_in_order += 1
        suppInCart.save(update_fields=['count_in_order'])
    except:
        suppInCart = SupplyInPreorderInCart(count_in_order=quantity,
                                            supply_for_order=preorderInCart,
                                            general_supply=general_supply)
        suppInCart.save()

    countInPreorder = suppInCart.count_in_order
    response = render(request, 'partials/cart/add_precart_button_general.html',
                      {'el': general_supply, 'countInPreCart': countInPreorder, 'place_id': place_id})
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

    response = render(request, 'partials/cart/add_cart_button.html',
                      {'supp': supply})
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
    isClient = request.user.isClient() and not request.user.is_staff
    place = None
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
        place = user_places.first()
        html_page = 'supplies/home/home_for_client.html'
        supplies = GeneralSupply.objects.filter(category_id__in=user_allowed_categories).order_by('name')
        suppFilter = SupplyFilter(request.GET, queryset=supplies)
        category = Category.objects.filter(id__in=user_allowed_categories)
        suppFilter.form.fields['category'].queryset = category

    else:
        supplies = GeneralSupply.objects.all().order_by('name')
        suppFilter = SupplyFilter(request.GET, queryset=supplies)
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
                                                  'place': place,
                                                   'booked_list_exist': booked_list_exist})




def update_count_in_preorder_cart(request, itemId):


    if request.method == 'POST':
        count = request.POST.get(f'count_{itemId}')
        countId = request.POST.get(f'count_id_{itemId}')

        supsInPreorderInCart = SupplyInPreorderInCart.objects.get(id=itemId)
        print(f'NAME:  {supsInPreorderInCart.general_supply.name} = {count}')

        supsInPreorderInCart.count_in_order = count
        supsInPreorderInCart.save(update_fields=['count_in_order'])
        response = updatePreCartItemCount(request)
        trigger_client_event(response, 'subscribe_precart', {})
        return response


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
    existing_place_for_preorder = orderInCart.place
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
            is_pinned = request.POST.get('isPinned') is not None
            place = existing_place_for_preorder if existing_place_for_preorder else Place.objects.get(id=place_id)

            if orderType == 'Preorder':
                isPreorder = preorderType == 'new_preorder'
                state_of_delivery = 'awaiting_from_customer'
                if isComplete:
                    dateSent = timezone.now().date()
                    state_of_delivery = 'accepted_by_customer'
                else:
                    dateSent = None
                order = PreOrder(userCreated=orderInCart.userCreated, place=place, dateSent=dateSent,
                                 isComplete=isComplete, isPreorder=isPreorder, isPinned=is_pinned,
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
                selectedPreorder.isPinned = is_pinned
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
                   'supplies': supplies, 'existing_place_for_preorder': existing_place_for_preorder, 'cities': cities, 'total_count_in_cart': total_count_in_cart,
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
    return render(request, 'supplies/orders/preorder_detail_list_item.html', {'el': gen_sup_in_preorder, 'order': gen_sup_in_preorder.supply_for_order})

@login_required(login_url='login')
def plus_from_preorders_detail_general_item(request):
    el_id = request.GET.get('el_id')
    for_preorder_id = request.GET.get('for_preorder_id')
    gen_sup_in_preorder = SupplyInPreorder.objects.get(id=el_id, supply_for_order_id=for_preorder_id)
    gen_sup_in_preorder.count_in_order += 1
    gen_sup_in_preorder.save(update_fields=['count_in_order'])

    print(el_id)
    print(for_preorder_id)
    return render(request, 'supplies/orders/preorder_detail_list_item.html', {'el': gen_sup_in_preorder, 'order': gen_sup_in_preorder.supply_for_order})

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
        orderType = request.POST.get('orderType')
        is_pinned = request.POST.get('isPinned') is not None
        print("is_pinned: ", is_pinned)
        if 'delete' in request.POST:
            next = request.POST.get('next')
            orderInCart.delete()
            return HttpResponseRedirect(next)
        if 'save' in request.POST:
            place_id = request.POST.get('place_id')
            place = Place.objects.get(id=place_id)
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
                                  isPinned=is_pinned,
                                  comment=comment, 
                                  dateToSend=dateToSend)
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
                    selectedOrder.isPinned = is_pinned
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
            place_id = request.POST.get('place_id')
            place = Place.objects.get(id=place_id)
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
                        date_created=sup.supply.dateCreated,
                        internalName=sup.supply.general_supply.name,
                        internalRef=sup.supply.general_supply.ref
                    )
               
                supInOrder.save()
                sup.supply.countOnHold += count
                sup.supply.save(update_fields=['countOnHold'])
                print("SupplyInBookedOrder DATE CREATED: ", supInOrder.date_created)
                print('SupplyInBookedOrder ID: ', supInOrder.id)

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
        ordersObj = Order.objects.filter(place__user=request.user).order_by(
            '-isPinned', 
            'isComplete', 
            'dateToSend', 
            Case(
                When(
                    statusnpparselfromdoucmentid__status_code__in=['1', '2', '3', '4', '41', '5', '6', '7', '8', '10', '11', '12', '101', '102', '103', '104', '105', '106', '111', '112'],
                    then=Value(0)
                ),
                default=Value(1),
                output_field=IntegerField(),
            ),
            '-id'
        )
        pinned_orders = ordersObj.filter(isPinned=True)
        pinned_orders_exists = pinned_orders.count() > 0
        totalCount = ordersObj.count()
        title = f'Всі замовлення для {request.user.first_name} {request.user.last_name}. ({totalCount} шт.)'

    else:
        ordersObj = Order.objects.all().order_by(
            '-isPinned', 
            'isComplete', 
            'dateToSend', 
            Case(
                When(
                    statusnpparselfromdoucmentid__status_code__in=['1', '2', '3', '4', '41', '5', '6', '7', '8', '10', '11', '12', '101', '102', '103', '104', '105', '106', '111', '112'],
                    then=Value(0)
                ),
                default=Value(1),
                output_field=IntegerField(),
            ),
            '-id'
        )
        pinned_orders = ordersObj.filter(isPinned=True)
        pinned_orders_exists = pinned_orders.count() > 0
        totalCount = ordersObj.count()
        title = f'Всі замовлення. ({totalCount} шт.)'

    orderFilter = OrderFilter(request.POST or None, queryset=ordersObj)
    orders = orderFilter.qs
    
    # Skip pagination if isComplete filter is set to '0' (В очікуванні)
    if request.POST and request.POST.get('isComplete') == '0':
        orders = orders  # Return all filtered orders without pagination
        print("Return all filtered orders without pagination")
    else:
        paginator = Paginator(orders, 20)
        page_number = request.GET.get('page')
        orders = paginator.get_page(page_number)
        
    is_more_then_one_order_exists_for_the_same_place = False
    uncomplete_orders_exists = False
    if not isClient:
        filtered_orders = ordersObj.filter(isComplete=False)
        uncomplete_orders_exists = filtered_orders.count() > 0
        orders_by_place = defaultdict(list)
        for order in filtered_orders:
            orders_by_place[order.place].append(order)
        is_more_then_one_order_exists_for_the_same_place = any(len(orders) > 1 for orders in orders_by_place.values())    
        
        if 'uncomplete_orders_complete_all_action' in request.POST:
            print('---------------------uncomplete_orders_complete_all_action--------------------------------')
            completed_count = 0
            for order in filtered_orders:
                try:
                    update_order_status_core(order, request.user)
                    completed_count += 1
                except Exception as e:
                    print(f"Error completing order {order.id}: {str(e)}")
            
            return JsonResponse({
                'message': f'Успішно завершено {completed_count} з {len(filtered_orders)} замовлень',
                'status': 'success',
                'completed_count': completed_count,
                'total_count': len(filtered_orders)
            })
            
        if 'merge_all_orders_for_the_same_place' in request.POST:
            print('---------------------merge_all_orders_for_the_same_place--------------------------------')
            # Get all orders from the current queryset
            merged_orders = merge_orders(filtered_orders, request.user)
            
            if not merged_orders:
                return JsonResponse({
                    'message': 'Не було об\'єднано жодного замовлення. Для об\'єднання потрібно щонайменше 2 замовлення для однієї організації',
                    'status': 'warning'
                })
                
            return JsonResponse({
                'message': 'Замовлення успішно об\'єднано',
                'merged_order_ids': [order.id for order in merged_orders],
                'status': 'success'
            })
            
            

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
        if 'remove_all_pinned_orders_action' in request.POST:
            if not (request.user.groups.filter(name='empl').exists() or request.user.is_staff):
                return HttpResponseForbidden("You don't have permission to perform this action")
            pinned_orders.update(isPinned=False)
            pinned_orders = pinned_orders.filter(isPinned=True)
            pinned_orders_exists = pinned_orders.count() > 0
            
        if 'print_choosed' in request.POST:
            print('---------------------PRINT CHOOSED --------------------------------')
            np_link_print = settings.NOVA_POSHTA_PRINT_MARKING_MULTIPLE_URL_TEMPLATE.format(
                refs=listToStr,
                api_key=settings.NOVA_POSHTA_API_KEY
            )
            return JsonResponse({
                'url': np_link_print,
                'open_in_new_tab': True
            })

        if 'merge_choosed' in request.POST:
            print('---------------------merge_choosed--------------------------------')
            print(request.POST)
            selected_orders = request.POST.getlist('register_exls_selected_buttons')
            selected_orders = ordersObj.filter(id__in=selected_orders)
            merged_orders = merge_orders(selected_orders, request.user)
            
            if not merged_orders:
                return JsonResponse({
                    'message': 'Не було об\'єднано жодного замовлення. Для об\'єднання потрібно вибрати щонайменше 2 замовлення для однієї організації',
                    'status': 'warning'
                })
                
            # Count how many orders were merged
            total_merged = len(merged_orders)
            total_selected = len(selected_orders)
            
            return JsonResponse({
                'message': f'Замовлення успішно об\'єднано. \n Вибрано {total_selected} замовлень, створено {total_merged} нових об\'єднаних замовлень.',
                'merged_order_ids': [order.id for order in merged_orders],
                'status': 'success'
            })

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
                "apiKey": settings.NOVA_POSHTA_API_KEY,
                "modelName": "ScanSheet",
                "calledMethod": "insertDocuments",
                "methodProperties": {
                    "DocumentRefs": list_of_refs
                }
            }
            data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
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
                np_link_print = settings.NOVA_POSHTA_PRINT_SCAN_SHEET_URL_TEMPLATE.format(
                    ref=register_Ref,
                    api_key=settings.NOVA_POSHTA_API_KEY
                )
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
                              {'title': title, 
                               'orders': orders, 
                               'orderFilter': orderFilter, 
                               'cartCountData': cartCountData, 
                               'isOrders': True,
                               'totalCount': totalCount,
                               'isOrdersTab': True,
                               'is_more_then_one_order_exists_for_the_same_place': is_more_then_one_order_exists_for_the_same_place,
                               'uncomplete_orders_exists': uncomplete_orders_exists})


    return render(request, 'supplies/orders/orders_new.html',
                  {'title': title, 
                   'orders': orders, 
                   'orderFilter': orderFilter, 
                   'cartCountData': cartCountData, 
                   'isOrders': True, 
                   'totalCount': totalCount,
                   'isOrdersTab': True, 
                   'pinned_orders_exists': pinned_orders_exists, 
                   'is_more_then_one_order_exists_for_the_same_place': is_more_then_one_order_exists_for_the_same_place,
                   'uncomplete_orders_exists': uncomplete_orders_exists})



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
            orders = PreOrder.objects.filter(place__user=request.user, isClosed=True).annotate(
            state_priority=Case(
                When(state_of_delivery='awaiting_from_customer', then=Value(1)),
                When(state_of_delivery='accepted_by_customer', then=Value(2)),
                When(state_of_delivery='Awaiting', then=Value(3)),
                When(state_of_delivery='Partial', then=Value(4)),
                When(state_of_delivery='Complete', then=Value(5)),
                When(state_of_delivery='Complete_Handle', then=Value(6)),
                default=Value(0),
                output_field=IntegerField(),
                )
            ).order_by('isComplete', 'state_priority', '-id')
        else:
            orders = PreOrder.objects.filter(place__user=request.user, isClosed=False).annotate(
            state_priority=Case(
                When(state_of_delivery='awaiting_from_customer', then=Value(1)),
                When(state_of_delivery='accepted_by_customer', then=Value(2)),
                When(state_of_delivery='Awaiting', then=Value(3)),
                When(state_of_delivery='Partial', then=Value(4)),
                When(state_of_delivery='Complete', then=Value(5)),
                When(state_of_delivery='Complete_Handle', then=Value(6)),
                default=Value(0),
                output_field=IntegerField(),
                )
            ).order_by('isComplete', 'state_priority', '-id')
            completed_orders = orders.filter(state_of_delivery='Complete')
            if completed_orders.count() > 0:
                for ord in completed_orders:
                    ord.isClosed = True
                    ord.isComplete = True
                    ord.save(update_fields=['isClosed', 'isComplete'])
        title = f'Всі передзамовлення для {request.user.first_name} {request.user.last_name}'
    else:
        if 'get_archive_preorders' in request.POST:
            isArchiveChoosed = True
            orders = PreOrder.objects.filter(isClosed=True).annotate(
            state_priority=Case(
                When(state_of_delivery='awaiting_from_customer', then=Value(1)),
                When(state_of_delivery='accepted_by_customer', then=Value(2)),
                When(state_of_delivery='Awaiting', then=Value(3)),
                When(state_of_delivery='Partial', then=Value(4)),
                When(state_of_delivery='Complete', then=Value(5)),
                When(state_of_delivery='Complete_Handle', then=Value(6)),
                default=Value(0),
                output_field=IntegerField(),
                )
            ).order_by('-isPinned', 'isComplete', 'state_priority', '-id')
        else:
            orders = PreOrder.objects.filter(isClosed=False).annotate(
            state_priority=Case(
                When(state_of_delivery='awaiting_from_customer', then=Value(1)),
                When(state_of_delivery='accepted_by_customer', then=Value(2)),
                When(state_of_delivery='Awaiting', then=Value(3)),
                When(state_of_delivery='Partial', then=Value(4)),
                When(state_of_delivery='Complete', then=Value(5)),
                When(state_of_delivery='Complete_Handle', then=Value(6)),
                default=Value(0),
                output_field=IntegerField(),
                )
            ).order_by('-isPinned', 'isComplete', 'state_priority', '-id')
            completed_orders = orders.filter(state_of_delivery='Complete')
            if completed_orders.count() > 0:
                for ord in completed_orders:
                    ord.isClosed = True
                    ord.isComplete = True
                    ord.save(update_fields=['isClosed', 'isComplete'])
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
                  {'title': title, 'isArchiveChoosed': isArchiveChoosed, 'orders': orders, 'preorderFilter': preorderFilter, 'cartCountData': cartCountData, 'isOrders': False,
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

    if request.user_agent.is_mobile:
        return render(request, 'supplies_mobile/preorder_cell.html', {'order': order})
    else:
        return render(request, 'partials/preorders/preorder_preview_cell.html', {'order': order})

@login_required(login_url='login')
def updatePreorderStatusPinned(request, order_id):
    if not (request.user.groups.filter(name='empl').exists() or request.user.is_staff):
        return HttpResponseForbidden("You don't have permission to perform this action")
        
    order = PreOrder.objects.get(id=order_id)
    is_pinned = request.POST.get('is_pinned')
    is_pinned_bool = is_pinned.lower() == 'true'
    order.isPinned = is_pinned_bool
    order.save(update_fields=['isPinned'])
    
    if request.user_agent.is_mobile:
        return render(request, 'supplies_mobile/preorder_cell.html', {'order': order})
    else:
        return render(request, 'partials/preorders/preorder_preview_cell.html', {'order': order})

def updateOrderPinnedStatus(request, order_id):
    if not (request.user.groups.filter(name='empl').exists() or request.user.is_staff):
        return HttpResponseForbidden("You don't have permission to perform this action")
        
    is_pinned = request.POST.get('is_pinned')
    is_pinned_bool = is_pinned.lower() == 'true'
    
    order = Order.objects.get(id=order_id)
    order.isPinned = is_pinned_bool
    order.save(update_fields=['isPinned'])
    # Check if user agent is mobile
    if request.user_agent.is_mobile:
        template = 'supplies_mobile/order_cell.html'
    else:
        template = 'partials/orders/order_preview_cel.html'
    return render(request, template, {'order': order})

def update_order_status_core(order_id_or_obj, user):
    # Check if the first parameter is an Order object or an ID
    if isinstance(order_id_or_obj, Order):
        order = order_id_or_obj
    else:
        order = Order.objects.get(id=order_id_or_obj)
    
    if order.isComplete:
        raise ValueError('Це замовлення вже завершено і не може бути оновлено')
    
    try:
        with transaction.atomic():
            supps = order.supplyinorder_set.all()
            for el in supps:
                countInOrder = el.count_in_order
                if el.supply:
                    supp = el.supply
                    new_count_on_hold = max(0, supp.countOnHold - countInOrder)
                    new_count = max(0, supp.count - countInOrder)
                    supp.countOnHold = new_count_on_hold
                    supp.count = new_count
                    if new_count == 0:
                        supp.delete()
                    else:
                        supp.save(update_fields=['countOnHold', 'count'])

                try:
                    if el.supply_in_booked_order:
                        supply_in_booked_order = el.supply_in_booked_order
                        new_count_on_hold = max(
                            0, supply_in_booked_order.countOnHold - countInOrder)
                        new_count_in_order = max(
                            0, supply_in_booked_order.count_in_order - countInOrder)
                        supply_in_booked_order.countOnHold = new_count_on_hold
                        supply_in_booked_order.count_in_order = new_count_in_order

                        if supply_in_booked_order.count_in_order == 0:
                            supply_in_booked_order.delete()
                        else:
                            supply_in_booked_order.save(
                                update_fields=['countOnHold', 'count_in_order'])
                except SupplyInBookedOrder.DoesNotExist:
                    # If the booked order doesn't exist, just continue with the next item
                    continue

                try:
                    if el.supply_in_preorder:
                        genSupInPreorder = el.supply_in_preorder
                        genSupInPreorder.count_in_order_current += el.count_in_order
                        if genSupInPreorder.count_in_order - genSupInPreorder.count_in_order_current <= 0:
                           genSupInPreorder.state_of_delivery = 'Complete'
                        else:
                            genSupInPreorder.state_of_delivery = 'Partial'
                        genSupInPreorder.save()
                except SupplyInPreorder.DoesNotExist:
                    # If the preorder doesn't exist, just continue with the next item
                    continue

            if order.for_preorder:
                preorder = order.for_preorder
                preorder.update_order_state_of_delivery_status()
            if order.related_preorders:
                print("upd order status for related preorders: ", order.related_preorders.all().count())
                for preorder in order.related_preorders.all():
                    preorder.update_order_state_of_delivery_status()
                    
            order.isComplete = True
            order.dateToSend = None
            order.dateSent = timezone.now().date()
            order.userSent = user
            order.save()        

        return order
    except Exception as e:
        # Re-raise the exception to be handled by the calling function
        raise ValueError(f'Помилка при оновленні статусу замовлення: {str(e)}')


@login_required(login_url='login')
def orderUpdateStatus(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        
        if order.isComplete:
            raise ValueError('Це замовлення вже завершено і не може бути закрито.\nОновіть сторінку браузера.')
            
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
        orders = place.preorder_set.filter(isClosed=False).annotate(
            state_priority=Case(
                When(state_of_delivery='awaiting_from_customer', then=Value(1)),
                When(state_of_delivery='accepted_by_customer', then=Value(2)),
                When(state_of_delivery='Awaiting', then=Value(3)),
                When(state_of_delivery='Partial', then=Value(4)),
                When(state_of_delivery='Complete', then=Value(5)),
                When(state_of_delivery='Complete_Handle', then=Value(6)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('isComplete', 'state_priority', '-id')

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

    return render(request, 'supplies/orders/preorders.html',
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
                obj.save()
        elif 'delete' in request.POST:
            note.delete()
        
        user_agent = get_user_agent(request)
        if user_agent.is_mobile:
                template = 'partials/supplies/supply_row_mobile.html'
        else:
                template = 'partials/supplies/supply_row.html'
        html = render_to_string(template, {
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
                   'title': 'Редагувати LOT товара',
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
            user_agent = get_user_agent(request)
            if user_agent.is_mobile:
                 template = 'partials/supplies/supply_row_mobile.html'
            else:
                 template = 'partials/supplies/supply_row.html'
            html = render_to_string(template, {
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
                  {'title': 'Редагувати назву товара', 'form': form, 'generalSupp': supp})


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

    return render(request, 'supplies/supplies/history_for_supply_list.html',
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

            user_agent = get_user_agent(request)
            if user_agent.is_mobile:
                 template = 'partials/supplies/supply_row_mobile.html'
            else:
                 template = 'partials/supplies/supply_row.html'
            html = render_to_string(template, {
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
    orgRefExist = place.ref_NP is not None

    if request.method == 'POST':
        if 'save' in request.POST:
            print("save editWorkerInfo")
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

        if 'delete' in request.POST:
            wrkr.delete()
        
        html = render_to_string('partials/clients/client_card.html', {
            'client': place,
            'request': request
        })
        return JsonResponse({
            'html': html,
            'clientId': place.id,
            'success': True
        })

    return render(request, 'supplies/clients/addNewWorkerForClient.html',
                  {'place': place, 'form': form, 'editMode': True, 'orgRefExist': orgRefExist})


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
            counterpartyref = settings.NOVA_POSHTA_SENDER_DMDX_REF

            if client.ref_NP is not None:
                counterpartyref = client.ref_NP


            if recipientType == 'Doors':
                params = {
                    "apiKey": settings.NOVA_POSHTA_API_KEY,
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
                data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
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
                        "apiKey": settings.NOVA_POSHTA_API_KEY,
                        "modelName": "Counterparty",
                        "calledMethod": "save",
                        "methodProperties": {
                            "CounterpartyType": "Organization",
                            "EDRPOU": f'{organization_code}',
                            "CounterpartyProperty": "Recipient"
                        }
                    }
                    data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
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
    orgRefExist = place.ref_NP is not None

    if request.method == 'POST':
        form = WorkerForm(request.POST)
        radioButton = request.POST.get('flexRadioDefault')
        if form.is_valid():
            refNP = ""
            if radioButton == 'asOrganization':
                refNP = place.ref_NP
            if radioButton == 'asPrivateUser':
                refNP = settings.NOVA_POSHTA_SENDER_DMDX_REF

            params = {
                "apiKey": settings.NOVA_POSHTA_API_KEY,
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
                data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
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
            html = render_to_string('partials/clients/client_card.html', {
            'client': place,
            'request': request
            })
            return JsonResponse({
                'html': html,
                'clientId': place.id,
                'success': True
            })
    return render(request, 'supplies/clients/addNewWorkerForClient.html',
                  {'place': place, 'form': form, 'orgRefExist': orgRefExist})


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
    supplies_in_order = order.supplyinorder_set.all().order_by('generalSupply__category', 'generalSupply__name')
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
                        "apiKey": settings.NOVA_POSHTA_API_KEY,
                        "modelName": "InternetDocument",
                        "calledMethod": "delete",
                        "methodProperties": {
                            "DocumentRefs": ref
                        }
                    }
                    data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
                    print(data)

            order.delete()
            return HttpResponseRedirect(next)

    return render(request, 'supplies/orders/orderDetail.html',
                  {'title': f'Замовлення № {order_id}', 'order': order, 'supplies': supplies_in_order,
                   'cartCountData': cartCountData, 'isOrders': True, 'highlighted_sup_id': sup_id})


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
                                date_created=s.dateCreated,
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

@login_required
@allowed_users(allowed_roles=['admin', 'empl'])
def analytics_report(request, place_id):
    cartCountData = countCartItemsHelper(request)
    place = get_object_or_404(Place, id=place_id)
    analytics = PreorderAnalytics(place)
    report = analytics.get_analytics_report()
    
    # Отримуємо всі передзамовлення для цього місця
    preorders = PreOrder.objects.filter(place=place).order_by('-dateCreated')
    
    # Отримуємо всі товари з передзамовлень, згруповані за generalSupply
    preorder_items = SupplyInPreorder.objects.filter(
        supply_for_order__in=preorders
    ).values(
        'generalSupply',
        'generalSupply__name',
        'generalSupply__package_and_tests',
        'generalSupply__category__name'
    ).annotate(
        total_quantity=Sum('count_in_order'),
        last_order_date=Max('supply_for_order__dateCreated')
    ).order_by('-total_quantity')
    
    # Отримуємо аналітичний звіт
    report = PreorderAnalytics(place).get_analytics_report()
    
    context = {
        'report': report,
        'preorders': preorders,
        'preorder_items': preorder_items,
        'cartCountData': cartCountData
    }
    return render(request, 'supplies/analytics_report.html', context)

@login_required
def analytics_preorders_list_for_client(request):
    cartCountData = countCartItemsHelper(request)
    place_id = request.user.get_user_place_id()
    place = get_object_or_404(Place, id=place_id)
    analytics = PreorderAnalytics(place)
    report = analytics.get_analytics_report()
    booked_list_exist = SupplyInBookedOrder.objects.filter(supply_for_place=place).exists()
    
    # Отримуємо всі передзамовлення для цього місця
    preorders = PreOrder.objects.filter(place=place).order_by('-dateCreated')
    
    # Отримуємо всі товари з передзамовлень, згруповані за generalSupply
    preorder_items = SupplyInPreorder.objects.filter(
        supply_for_order__in=preorders
    ).values(
        'generalSupply',
        'generalSupply__name',
        'generalSupply__package_and_tests',
        'generalSupply__category__name'
    ).annotate(
        total_quantity=Sum('count_in_order'),
        last_order_date=Max('supply_for_order__dateCreated')
    ).order_by('-total_quantity')
    
    # Отримуємо аналітичний звіт
    report = PreorderAnalytics(place).get_analytics_report()
    
    context = {
        'title': 'Аналітика передзамовлень',
        'report': report,
        'preorders': preorders,
        'preorder_items': preorder_items,
        'cartCountData': cartCountData  ,
        'place_id': place_id,
        'booked_list_exist': booked_list_exist,
        'isAnalytics': True
    }
    return render(request, 'supplies/clients/analytics_preorders_list.html', context)


def teams_reminders_task():
    
    # Отримуємо всі замовлення, які треба відправити сьогодні
    order_to_send_today = Order.objects.filter(dateToSend=date.today(), isComplete=False)
    order_to_send_today_count = order_to_send_today.count()
    if order_to_send_today_count > 0:
        title = f'Відправити замовлень сьогодні: {order_to_send_today_count} шт.'
        orderInfo = ''
        for order in order_to_send_today:
             orderInfo += f' • *№{order.id}:*  **{order.place.name}, {order.place.city_ref.name}**\n\n'
        teams_reminders_send_message(title, orderInfo)
        
    # Отримуємо всі передзамовлення, в яких прогнозована дата передзамовлення сьогодні
    current_date = timezone.now().date()
    
    # First filter places that have at least one preorder
    places_with_preorders = Place.objects.filter(preorder__isnull=False, preorder__isPreorder=True).distinct()
    
    # Then filter based on predicted next order date
    from .analytics import PreorderAnalytics
    places_needing_order = []
    
    for place in places_with_preorders:
        analytics = PreorderAnalytics(place)
        next_order_date = analytics.predict_next_order_date()
        if next_order_date == current_date:
           places_needing_order.append(place.id)
    place_need_preorder_today = Place.objects.filter(id__in=places_needing_order)       
    place_need_preorder_today_count = place_need_preorder_today.count()
    if place_need_preorder_today_count > 0:
        title = f'Організації, яким рекомендовані передзамовлення сьогодні: {place_need_preorder_today_count}'
        place_info = ''
        for place in place_need_preorder_today:
            place_info += f' • {place.name}, {place.city_ref.name}\n\n'
        teams_reminders_send_message(title, place_info)
    
def teams_reminders_send_message(title, message, attachment=None):
    myTeamsMessage = pymsteams.connectorcard(
        settings.TEAMS_WEBHOOK_URL_REMINDERS)
    myTeamsMessage.title(title)
    myTeamsMessage.text(message)
    if attachment:
        myTeamsMessage.addSection(attachment)
    myTeamsMessage.send()

def merge_orders(orders, user):
    """
    Merge multiple orders for the same place into a single order.
    
    Args:
        orders: A list of Order objects to merge
        user: The user who is performing the merge
        
    Returns:
        A list of newly created merged orders
    """
    # Step 1: Group orders by place
    orders_by_place = defaultdict(list)
    for order in orders:
        orders_by_place[order.place].append(order)
    
    # Step 2: Create new merged orders for each place
    merged_orders = []
    for place, orders in orders_by_place.items():
        # Only process places with more than 1 order
        if len(orders) <= 1:
            continue
            
        # Initialize aggregated values
        dateToSend = None
        documentsId_aggregated = []
        np_delivery_created_detail_info_aggregated = []
        status_npp_aggregated = []
        comment_aggregated = ''
        
        # Aggregate values from all orders
        for order in orders:
            # Aggregate dateToSend (take the earliest date if multiple exist)
            if order.dateToSend:
                if dateToSend is None or order.dateToSend < dateToSend:
                    dateToSend = order.dateToSend
            
            # Aggregate documentsId arrays
            if order.documentsId:
                documentsId_aggregated.extend(order.documentsId)
            
            # Aggregate comments
            if order.comment:
                comment_aggregated += f'{order.comment}\n'
            if order.npdeliverycreateddetailinfo_set.exists():
                np_delivery_created_detail_info_aggregated.extend(order.npdeliverycreateddetailinfo_set.all())
            if order.statusnpparselfromdoucmentid_set.exists():
                status_npp_aggregated.extend(order.statusnpparselfromdoucmentid_set.all())
        # Create new order for this place
        new_order = Order.objects.create(
            userCreated=user,
            place=place,
            dateCreated=timezone.now().date(),
            isComplete=False,
            comment=comment_aggregated,
            isMerged=True,
            dateToSend=dateToSend,  # This will be None if no orders had a dateToSend
            documentsId=documentsId_aggregated
        )
        new_order.npdeliverycreateddetailinfo_set.add(*np_delivery_created_detail_info_aggregated)
        new_order.statusnpparselfromdoucmentid_set.add(*status_npp_aggregated)
        
        # Extract PreOrder objects from the orders
        preorders = []
        for order in orders:
            if order.for_preorder:
                preorders.append(order.for_preorder)
            # Add all related preorders from each order
            preorders.extend(order.related_preorders.all())

        # Add these PreOrder objects to the related_preorders field
        new_order.related_preorders.add(*preorders)
        
        # Get all SupplyInOrder objects for these orders
        supply_in_orders = SupplyInOrder.objects.filter(supply_for_order__in=orders)
        
        # Separate orders into three categories:
        # 1. Orders with no preorder or booked order (need merging by supply)
        # 2. Orders with preorder (need merging by preorder's supply_for_order)
        # 3. Orders with booked order (need merging by booked order)
        orders_to_merge_by_supply = [sio for sio in supply_in_orders if sio.supply_in_preorder is None and sio.supply_in_booked_order is None]
        orders_with_preorder = [sio for sio in supply_in_orders if sio.supply_in_preorder is not None]
        orders_with_booked = [sio for sio in supply_in_orders if sio.supply_in_booked_order is not None]
        
        # 1. Handle orders with no preorder or booked order - merge by supply
        supplies_by_supply = defaultdict(list)
        for supply_in_order in orders_to_merge_by_supply:
            if supply_in_order.supply:
                supplies_by_supply[supply_in_order.supply].append(supply_in_order)
        
        for supply, supply_in_orders_list in supplies_by_supply.items():
            total_count = sum(sio.count_in_order for sio in supply_in_orders_list)
            template_sio = supply_in_orders_list[0]
            
            SupplyInOrder.objects.create(
                count_in_order=total_count,
                generalSupply=template_sio.generalSupply,
                supply=template_sio.supply,
                supply_in_preorder=template_sio.supply_in_preorder,
                supply_for_order=new_order,
                supply_in_booked_order=template_sio.supply_in_booked_order,
                lot=template_sio.lot,
                date_expired=template_sio.date_expired,
                date_created=template_sio.date_created,
                internalName=template_sio.internalName,
                internalRef=template_sio.internalRef
            )
        
        # 2. Handle orders with preorder - merge by preorder's supply_for_order
        preorders_by_key = defaultdict(list)
        for sio in orders_with_preorder:
            # Get the PreOrder associated with this SupplyInPreorder
            preorder = sio.supply_in_preorder
            key = preorder.supply_for_order  # This is the PreOrder
            preorders_by_key[key].append(sio)
        
        for preorder, sio_list in preorders_by_key.items():
            total_count = sum(sio.count_in_order for sio in sio_list)
            template_sio = sio_list[0]
            
            SupplyInOrder.objects.create(
                count_in_order=total_count,
                generalSupply=template_sio.generalSupply,
                supply=template_sio.supply,
                supply_in_preorder=template_sio.supply_in_preorder,
                supply_for_order=new_order,
                supply_in_booked_order=template_sio.supply_in_booked_order,
                lot=template_sio.lot,
                date_expired=template_sio.date_expired,
                date_created=template_sio.date_created,
                internalName=template_sio.internalName,
                internalRef=template_sio.internalRef
            )
        
        # 3. Handle orders with booked order - merge by booked order
        booked_by_key = defaultdict(list)
        for sio in orders_with_booked:
            booked_by_key[sio.supply_in_booked_order].append(sio)
        
        for booked_order, sio_list in booked_by_key.items():
            total_count = sum(sio.count_in_order for sio in sio_list)
            template_sio = sio_list[0]
            
            SupplyInOrder.objects.create(
                count_in_order=total_count,
                generalSupply=template_sio.generalSupply,
                supply=template_sio.supply,
                supply_in_preorder=template_sio.supply_in_preorder,
                supply_for_order=new_order,
                supply_in_booked_order=booked_order,
                lot=template_sio.lot,
                date_expired=template_sio.date_expired,
                date_created=template_sio.date_created,
                internalName=template_sio.internalName,
                internalRef=template_sio.internalRef
            )

        merged_orders.append(new_order)
        for order in orders:
            order.delete()
    
    return merged_orders

