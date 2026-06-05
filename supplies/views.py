import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
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
from django_htmx.http import trigger_client_event
from django.contrib import messages
import requests
import csv
from django.db.models import Sum, F, Exists, OuterRef, Max, Case, When, Value, IntegerField, Q, BooleanField, Avg, Count
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.db import transaction
from .analytics import PreorderAnalytics, build_orders_analytics, build_preorders_analytics, build_supply_statistics, build_clients_info_analytics, bulk_predict_next_order_dates
from .query_utils import related_count_subquery, devices_list_queryset, servicenotes_list_queryset, places_for_filter_queryset, place_choice_label
from .topbar_cart_counts import topbar_cart_count_context
from .home_table_display import HOME_TABLE_DISPLAY_JS_TO_MODEL, home_table_display_settings_for_user
from django.utils import timezone
from urllib.parse import urlparse
from .excel_sheets.excel_views import (
    _group_order_supplies_for_display,
    export_child_supplies_xlsx,
    export_selected_orders_to_xlsx,
    generate_list_of_xls_from_preorders_list,
)


# @login_required(login_url='login')
# @allowed_users(allowed_roles=['admin'])
# def receive_and_load_new_supplies_order(request):

_APP_SETTINGS_TOGGLE_FIELDS = frozenset(AppSettingsForm.Meta.fields)


@login_required(login_url='login')
@require_POST
def home_table_display_toggle(request):
    field_key = request.POST.get('field')
    model_field = HOME_TABLE_DISPLAY_JS_TO_MODEL.get(field_key)
    if not model_field:
        return HttpResponse(status=400)
    raw = str(request.POST.get('value', '')).lower()
    value = raw in ('true', '1', 'on', 'yes')
    obj = request.user.get_app_settings()
    setattr(obj, model_field, value)
    obj.save(update_fields=[model_field])
    return HttpResponse(status=204)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
@require_POST
def app_settings_toggle(request):
    field = request.POST.get('field')
    if field not in _APP_SETTINGS_TOGGLE_FIELDS:
        return HttpResponse(status=400)
    raw = str(request.POST.get('value', '')).lower()
    value = raw in ('true', '1', 'on', 'yes')
    obj = request.user.get_app_settings()
    setattr(obj, field, value)
    obj.save(update_fields=[field])
    return HttpResponse(status=204)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def app_settings(request):
    app_settings_obj = request.user.get_app_settings()
    form = AppSettingsForm(instance=app_settings_obj)

    return render(
        request,
        'supplies/settings/app_settings.html',
        {
            'form': form,
            'title': 'Налаштування застосунку',
            'title_icon': 'bi-sliders',
            'subtitle': 'Тумблери зберігаються автоматично при зміні. Push-налаштування — у мобільному додатку.',
        },
    )

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
        messages.success(request, 'REF контактної особи збережено.')

    current_ref = user.np_contact_sender_ref
    param = {'apiKey': settings.NOVA_POSHTA_API_KEY,
             'modelName': 'Counterparty',
             'calledMethod': 'getCounterpartyContactPersons',
             'methodProperties': {'Ref': settings.NOVA_POSHTA_SENDER_DMDX_REF}}

    try:
        response = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(param), timeout=30)
        payload = response.json()
    except (requests.RequestException, ValueError):
        payload = {}

    rows = payload.get('data') if isinstance(payload, dict) else None
    counterparty_rows = rows if isinstance(rows, list) else []

    return render(
        request,
        'supplies/nova_poshta/np_info_table_sync_for_user.html',
        {
            'data': counterparty_rows,
            'current_ref': current_ref,
            'title': 'Контакти відправника (Нова Пошта)',
            'title_icon': 'bi-person-badge',
            'subtitle': 'Оберіть REF контактної особи; він синхронізується з вашим профілем для відправлень.',
        },
    )

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

def countCartItemsHelper(request):
    """Повні лічильники для явних викликів (не context processor)."""
    return topbar_cart_count_context(request)['cartCountData']

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


def delete_np_parsel_document(status_parsel):
    """Видалити накладну НП через API та прибрати локальні записи (status + detail info)."""
    np_document = NPDeliveryCreatedDetailInfo.objects.get(document_id=status_parsel.docNumber)
    params = {
        "apiKey": settings.NOVA_POSHTA_API_KEY,
        "modelName": "InternetDocument",
        "calledMethod": "delete",
        "methodProperties": {
            "DocumentRefs": np_document.ref
        }
    }
    response_data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
    status_parsel.delete()
    np_document.delete()
    return response_data


@login_required(login_url='login')
def deleteSupplyInOrderNPDocumentButton(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']
    print(action)

    if action == 'delete':
        status_parsel = StatusNPParselFromDoucmentID.objects.get(pk=prodId)
        response_data = delete_np_parsel_document(status_parsel)
        print(response_data)
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
    hx_current_url = request.headers.get('HX-Current-URL', '')
    parsed_url = urlparse(hx_current_url) if hx_current_url else None
    next_url = '/'
    if parsed_url and parsed_url.path:
        is_service_url = parsed_url.path in ('/update-cart-item-count/', '/update-precart-item-count/')
        if not is_service_url:
            next_url = parsed_url.path
            if parsed_url.query:
                next_url = f'{next_url}?{parsed_url.query}'
    return render(
        request,
        'partials/cart/cart-badge.html',
        {'cart_next_url': next_url, **topbar_cart_count_context(request)},
    )


def updatePreCartItemCount(request):
    hx_current_url = request.headers.get('HX-Current-URL', '')
    parsed_url = urlparse(hx_current_url) if hx_current_url else None
    next_url = '/'
    if parsed_url and parsed_url.path:
        is_service_url = parsed_url.path in ('/update-cart-item-count/', '/update-precart-item-count/')
        if not is_service_url:
            next_url = parsed_url.path
            if parsed_url.query:
                next_url = f'{next_url}?{parsed_url.query}'
    return render(
        request,
        'partials/cart/precart-badge.html',
        {'precart_next_url': next_url, **topbar_cart_count_context(request)},
    )


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
        elif supply.supply_id:
            supply.count_in_order += 1
            supply.supply.countOnHold += 1
            supply.supply.save(update_fields=['countOnHold'])
            supply.save(update_fields=['count_in_order'])
        else:
            supply.count_in_order += 1
            supply.save(update_fields=['count_in_order'])

    elif action == 'minus':
        if supply.supply_in_booked_order:
            supply.count_in_order -= 1
            supply.supply_in_booked_order.countOnHold -= 1
            supply.supply_in_booked_order.save(update_fields=['countOnHold'])
            supply.save(update_fields=['count_in_order'])
        elif supply.supply_id:
            supply.count_in_order -= 1
            supply.supply.countOnHold -= 1
            supply.supply.save(update_fields=['countOnHold'])
            supply.save(update_fields=['count_in_order'])
        else:
            supply.count_in_order -= 1
            supply.save(update_fields=['count_in_order'])
        if supply.count_in_order <= 0:
            supply.delete()
            return HttpResponse(status=200)
        if for_order.supplyinorder_set.count() == 0:
           for_order.delete()
           return HttpResponse(status=200)

    order_for_row = _order_detail_single(for_order.pk).first() or for_order
    return render(request, 'partials/orders/orderDetail_cell_item_nested_row.html', {
        'el': supply,
        'counter': counter,
        'order': order_for_row,
        'highlighted_sup_id': 0,
    })


@login_required(login_url='login')
def orderTypeDescriptionField(request):
    orderType = request.POST.get('orderType')
    isAgreement = orderType == 'Agreement'
    return render(request, 'partials/orders/orderTypeDescriptionField.html', {'isAgreement': isAgreement})

@login_required(login_url='login')
def add_to_exist_order_from_cart(request):
    orderType = request.POST.get('orderType')
    isAdd_to_exist_order = orderType == 'add_to_Exist_order'
    print("orderType", orderType)
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
    print("orderType", orderType)
    preorders = PreOrder.objects.filter(place_id=place_id_Selected).filter(Q(state_of_delivery='awaiting_from_customer') | Q(state_of_delivery='accepted_by_customer')).order_by('-id')

    return render(request, 'partials/orders/orderTypeDescriptionField_for_client.html', {'isAddedToExistPreorder': isAddedToExistPreorder, 'preorders': preorders})



@login_required(login_url='login')
def updateCartItem(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']
    next_url = data.get('next') or '/'

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

    return JsonResponse({'isLastItemInCart': isLastItemInCart, 'redirectUrl': next_url}, safe=False)

@login_required(login_url='login')
def registerPage(request):
    form = CreateUserForm()
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            # Apply pending relations (places, categories, and client group)
            form.apply_pending_relations(user)
            messages.success(request, 'Акаунт клієнта створено')
            return redirect('auth')

    return render(request, 'auth/register.html', {
        'title': 'Створити новий аккаунт для клієнта',
        'form': form})


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
        user_places = request.user.place_set.prefetch_related('allowed_categories')
        user_allowed_categories = set()
        for plc in user_places:
            for cat in plc.allowed_categories.all():
                user_allowed_categories.add(cat.id)
        booked_list_exist = SupplyInBookedOrder.objects.filter(
            supply_for_place__in=user_places
        ).exists()
        place = user_places.first()
        html_page = 'supplies/home/home_for_client.html'
        supplies = (
            GeneralSupply.objects.filter(category_id__in=user_allowed_categories)
            .select_related('category')
            .order_by('name')
        )
        suppFilter = SupplyFilter(request.GET, queryset=supplies)
        category = Category.objects.filter(id__in=user_allowed_categories)
        suppFilter.form.fields['category'].queryset = category

    else:
        supplies = GeneralSupply.objects.select_related('category').order_by('name')
        ua = get_user_agent(request)
        if ua.is_mobile:
            html_page = 'supplies/home/home_mobile.html'
        else:
            html_page = 'supplies/home/home_desktop.html'
        filter_get = request.GET.copy()
        if not set(filter_get.keys()) - {'page'}:
            filter_get['ordering'] = SupplyFilter.EXIST_CHOICES.В_наявності
        suppFilter = SupplyFilter(filter_get, queryset=supplies)

    supplies = suppFilter.qs

    paginator = Paginator(supplies, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
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

    context = {
        'title': 'Всі товари',
        'supplies': page_obj,
        'suppFilter': suppFilter,
        'isHome': True,
        'isAll': True,
        'isSupplyStats': False,
        'place': place,
        'booked_list_exist': booked_list_exist,
    }
    if not isClient:
        context['home_table_display'] = home_table_display_settings_for_user(request.user)
    return render(request, html_page, context)




def update_count_in_preorder_cart(request, itemId):


    if request.method == 'POST':
        count = request.POST.get(f'count_{itemId}')
        countId = request.POST.get(f'count_id_{itemId}')

        supsInPreorderInCart = SupplyInPreorderInCart.objects.get(id=itemId)
        print(f'NAME:  {supsInPreorderInCart.general_supply.name} = {count}')

        if count != '':  # Only save if count is not empty
            supsInPreorderInCart.count_in_order = count
            supsInPreorderInCart.save(update_fields=['count_in_order'])
        response = updatePreCartItemCount(request)
        trigger_client_event(response, 'subscribe_precart', {})
        return response


import threading


def sendPushMsgPreorder(preorder):
    from .push_notifications import send_push_new_preorder
    t = threading.Thread(target=send_push_new_preorder, args=[preorder], daemon=True)
    t.start()


@login_required(login_url='login')
def cartDetailForClient(request):
    orderInCart = PreorderInCart.objects.get(userCreated=request.user, isComplete=False)
    existing_place_for_preorder = orderInCart.place
    supplies = orderInCart.supplyinpreorderincart_set.all()
    total_count_in_cart = supplies.aggregate(total_count=Sum('count_in_order'))['total_count']
    cities = City.objects.all()
    
    # Initialize form with isComplete=True only for this view
    initial_data = {'isComplete': True}
    orderForm = OrderInCartForm(request.POST or initial_data)
    
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
        preorders = []
        for place in places:
            preorders.extend(place.preorder_set.filter(Q(state_of_delivery='awaiting_from_customer') | Q(state_of_delivery='accepted_by_customer')))
        preorders = sorted(preorders, key=lambda x: -x.id)

        if places.count() == 1:
            print(places.count())
            placeChoosed = True
            # places.fields['place'].initial = places.first()
        print("preorders", preorders)    
        
    else:
        isPendingPreorderExist = PreOrder.objects.filter(isComplete=False).exists()

    if request.method == 'POST':

        if orderForm.is_valid():
            comment = orderForm.cleaned_data['comment']
            isComplete = orderForm.cleaned_data['isComplete']
            orderType = request.POST.get('orderType') or 'Preorder'
            preorderType = request.POST.get('preorderType')
            isPreorder = preorderType == 'new_preorder'
            place_id = request.POST.get('place_id')
            is_pinned = request.POST.get('isPinned') is not None
            place = existing_place_for_preorder if existing_place_for_preorder else Place.objects.get(id=place_id)
            
            selected_non_completed_preorder = request.POST.get('selected_non_completed_preorder') or None
            selectedPreorder = None    
            if selected_non_completed_preorder:
                try:
                    selectedPreorder = PreOrder.objects.get(id=selected_non_completed_preorder)
                except:
                    selectedPreorder = None    
                    
            if selectedPreorder == None:
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
                print(state_of_delivery)

                for index, sup in enumerate(supplies):
                    count = request.POST.get(f'count_{sup.id}')
                    general_sup = sup.general_supply
                    suppInOrder = SupplyInPreorder(count_in_order=count,
                                                   generalSupply=general_sup,
                                                   supply_for_order=order)

                    suppInOrder.save()

                sendPushMsgPreorder(order)

            else:
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
                  {'title': f'Корзина передзамовлення ({total_count_in_cart} шт.)', 'order': orderInCart,
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

            sendPushMsgCart(order)
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
        messages.success(request, 'Адресу відправлення збережено.')
        return redirect('add_np_sender_place')

    return render(
        request,
        'supplies/nova_poshta/add_new_sender_np_place.html',
        {
            'places': places,
            'title': 'Відділення та адреси відправлення',
            'title_icon': 'bi-geo-alt',
            'subtitle': 'Керуйте збереженими точками відправника та додавайте нові через довідник Нової Пошти.',
        },
    )




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
def get_place_for_city_in_import_new_preorder(request):
    city_id = request.GET.get('city')
    try:
        places = Place.objects.filter(city_ref_id=city_id)
    except:
        places = None

    return render(request, 'partials/preorders/choose_place_in_import_new_preorder.html', {'places': places})




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

def _render_preorder_detail_row_response(request, gen_sup_in_preorder, preorder, *, refresh_status=False):
    preorder.refresh_from_db()
    gen_sup_in_preorder.refresh_from_db()
    response = render(
        request,
        'supplies/orders/preorder_detail_list_item_swap.html',
        {
            'el': gen_sup_in_preorder,
            'order': preorder,
        },
    )
    if refresh_status:
        response = trigger_client_event(response, 'preorderDetailRefreshStatus', {})
    return response


def _preorder_row_delete_response(preorder, row_id, *, refresh_status=False):
    response = HttpResponse(status=200)
    response['HX-Retarget'] = f'#preorder-detail-supply-row-{row_id}'
    response['HX-Reswap'] = 'delete'
    if refresh_status:
        response = trigger_client_event(response, 'preorderDetailRefreshStatus', {})
    return response


def _adjust_preorder_line_count(gen_sup_in_preorder, delta):
    """
    delta: +1 or -1.
    Повертає (result, preorder, deleted_row_id|None).
    """
    preorder = gen_sup_in_preorder.supply_for_order
    ordered = gen_sup_in_preorder.count_in_order or 0

    if delta < 0:
        if not gen_sup_in_preorder.can_decrement:
            return 'unchanged', preorder, None
        new_count = ordered - 1
        if new_count <= 0:
            deleted_row_id = gen_sup_in_preorder.id
            gen_sup_in_preorder.delete()
            if preorder and preorder.should_track_delivery_status_on_quantity_edit():
                preorder.update_order_state_of_delivery_status()
            return 'deleted', preorder, deleted_row_id
        gen_sup_in_preorder.count_in_order = new_count
    else:
        gen_sup_in_preorder.count_in_order = ordered + 1

    gen_sup_in_preorder.save_count_in_order(update_preorder_status=True)
    return 'updated', preorder, None


@login_required(login_url='login')
@transaction.atomic
def minus_from_preorders_detail_general_item(request):
    el_id = request.GET.get('el_id')
    for_preorder_id = request.GET.get('for_preorder_id')
    gen_sup_in_preorder = SupplyInPreorder.objects.select_for_update(of=('self',)).select_related(
        'generalSupply', 'generalSupply__category',
    ).prefetch_related('supplyinorder_set').get(
        id=el_id, supply_for_order_id=for_preorder_id,
    )
    result, preorder, deleted_row_id = _adjust_preorder_line_count(gen_sup_in_preorder, -1)

    if result == 'deleted':
        return _preorder_row_delete_response(
            preorder, deleted_row_id, refresh_status=preorder.should_track_delivery_status_on_quantity_edit(),
        )
    if result == 'unchanged':
        return _render_preorder_detail_row_response(request, gen_sup_in_preorder, preorder)

    return _render_preorder_detail_row_response(
        request, gen_sup_in_preorder, preorder,
        refresh_status=preorder.should_track_delivery_status_on_quantity_edit(),
    )

@login_required(login_url='login')
@transaction.atomic
def plus_from_preorders_detail_general_item(request):
    el_id = request.GET.get('el_id')
    for_preorder_id = request.GET.get('for_preorder_id')
    gen_sup_in_preorder = SupplyInPreorder.objects.select_for_update(of=('self',)).select_related(
        'generalSupply', 'generalSupply__category',
    ).prefetch_related('supplyinorder_set').get(
        id=el_id, supply_for_order_id=for_preorder_id,
    )
    _adjust_preorder_line_count(gen_sup_in_preorder, 1)
    preorder = gen_sup_in_preorder.supply_for_order
    return _render_preorder_detail_row_response(
        request, gen_sup_in_preorder, preorder,
        refresh_status=preorder.should_track_delivery_status_on_quantity_edit(),
    )

@login_required(login_url='login')
@transaction.atomic
def delete_from_preorders_detail_general_item(request, el_id):
    gen_sup_in_preorder = SupplyInPreorder.objects.select_for_update().get(id=el_id)
    preorder = gen_sup_in_preorder.supply_for_order
    row_id = gen_sup_in_preorder.id
    gen_sup_in_preorder.delete()
    refresh = preorder.should_track_delivery_status_on_quantity_edit() if preorder else False
    if refresh:
        preorder.update_order_state_of_delivery_status()
    return _preorder_row_delete_response(preorder, row_id, refresh_status=refresh)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def get_agreement_for_place_for_city_in_cart(request):
    place_id = request.GET.get('place_id')
    place = Place.objects.get(pk=place_id)
    user_settings = request.user.get_app_settings()
    if user_settings.enable_preorder_editing_awaiting_state:
        preorders = place.preorder_set.filter(Q(state_of_delivery='awaiting_from_customer') | Q(state_of_delivery='accepted_by_customer') | Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial')).order_by('-id')
    else:
        preorders = place.preorder_set.filter(Q(state_of_delivery='awaiting_from_customer') | Q(state_of_delivery='accepted_by_customer')).order_by('-id')

    return render(request, 'partials/cart/choose_agreement_forplace_incart.html', {'preorders': preorders})


def sendPushMsgCart(order):
    from .push_notifications import send_push_new_order
    t = threading.Thread(target=send_push_new_order, args=[order], daemon=True)
    t.start()


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
@transaction.atomic
def cartDetail(request):
    orderInCart = OrderInCart.objects.first()
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
                    selected_preorder_id = request.POST.get('selectedPreorder')
                    selectedPreorder = None
                    if selected_preorder_id:
                        selectedPreorder = PreOrder.objects.get(id=selected_preorder_id)

                    order = Order(userCreated=orderInCart.userCreated, 
                                  place=place, 
                                  dateSent=dateSent,
                                  for_preorder=selectedPreorder,
                                  isComplete=isComplete, 
                                  isPinned=is_pinned,
                                  comment=comment, 
                                  dateToSend=dateToSend)
                    order.save()
                    

                    for index, sup in enumerate(supplies):
                        count = request.POST.get(f'count_{sup.id}')
                        suppInPreorder = None
                        if selectedPreorder:
                            try:
                                suppInPreorder = selectedPreorder.supplyinpreorder_set.get(generalSupply=sup.supply.general_supply)
                            except:
                                suppInPreorder = None
                        suppInOrder = SupplyInOrder(count_in_order=count,
                                                    supply=sup.supply,
                                                    generalSupply=sup.supply.general_supply,
                                                    supply_for_order=order,
                                                    supply_in_preorder=suppInPreorder,
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

                    sendPushMsgCart(order)

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
                  {'title': f'Корзина ({total_count_in_cart} шт.)', 'order': orderInCart, 'supplies': supplies,
                   'orderForm': orderForm, 'cities': cities, 'total_count_in_cart': total_count_in_cart})


@login_required(login_url='login')
def childSupply(request):
    supplies = (
        Supply.objects.select_related('general_supply', 'general_supply__category')
        .order_by('name')
    )
    suppFilter = ChildSupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs.select_related('general_supply', 'general_supply__category')

    if 'xls_button' in request.GET:
        export_supplies = supplies.annotate(available_count=ExpressionWrapper(
            F('count') - F('countOnHold'),
            output_field=IntegerField(),
        )).filter(available_count__gt=0).order_by('name')
        return export_child_supplies_xlsx(
            export_supplies,
            'Загальний список товарів (Без броні)',
            suppFilter.qs.count(),
            use_available_count=True,
        )

    if 'all_xls_button' in request.GET:
        return export_child_supplies_xlsx(
            supplies,
            'Загальний список товарів (Всі товари)',
            suppFilter.qs.count(),
        )
    ua = get_user_agent(request)
    child_tpl = (
        'supplies/home/homeChild_mobile.html'
        if ua.is_mobile
        else 'supplies/home/homeChild_desktop.html'
    )
    return render(request, child_tpl,
                  {'title': 'Дочерні товари', 'supplies': supplies,
                   'suppFilter': suppFilter, 'isHome': True, 'isChild': True, 'isSupplyStats': False})


@login_required(login_url='login')
def supply_statistics(request):
    if request.user.isClient() and not request.user.is_staff:
        return redirect('home')
    return render(
        request,
        'supplies/home/supply_statistics.html',
        {
            'title': 'Статистика товарів',
            'isHome': True,
            'isAll': False,
            'isChild': False,
            'isSupplyStats': True,
        },
    )


@login_required(login_url='login')
def supply_statistics_data(request):
    if request.user.isClient() and not request.user.is_staff:
        return JsonResponse({'error': 'forbidden'}, status=403)
    return JsonResponse(build_supply_statistics(request.user))


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





def _orders_list_queryset(qs):
    """
    Картки замовлень (order_preview_cel / order_cell): без цього N+1 на place, userCreated,
    related_preorders (count/first/all), npdelivery detail exists, статуси НП.
    """
    status_np_qs = StatusNPParselFromDoucmentID.objects.order_by('id')
    return (
        qs.select_related(
            'userCreated',
            'userSent',
            'place',
            'place__city_ref',
            'place__address_NP',
            'place__worker_NP',
            'for_preorder',
        )
        .annotate(
            card_related_preorders_count=Count('related_preorders', distinct=True),
            has_np_delivery_detail=Exists(
                NPDeliveryCreatedDetailInfo.objects.filter(for_order_id=OuterRef('pk'))
            ),
            has_status_np=Exists(
                StatusNPParselFromDoucmentID.objects.filter(for_order_id=OuterRef('pk'))
            ),
        )
        .prefetch_related(
            'userCreated__groups',
            'related_preorders',
            Prefetch('statusnpparselfromdoucmentid_set', queryset=status_np_qs),
        )
    )


def _order_singleton_for_card(order_id):
    return _orders_list_queryset(Order.objects.filter(pk=order_id)).first()


def _order_detail_single(order_id):
    """
    Одне замовлення для orderDetail: методи шаблону isUncompletedPreorderForPlaceExist /
    isForPreorderOrItemHasPreorder та related_preorders.count давали зайві запити.
    """
    uncompleted_pre_qs = PreOrder.objects.filter(place_id=OuterRef('place_id')).filter(
        Q(state_of_delivery='Awaiting')
        | Q(state_of_delivery='Partial')
        | Q(state_of_delivery='accepted_by_customer')
    )
    return _orders_list_queryset(Order.objects.filter(pk=order_id)).annotate(
        has_uncompleted_preorder_for_place=Exists(uncompleted_pre_qs),
        detail_has_preorder_lines=Exists(
            SupplyInOrder.objects.filter(
                supply_for_order_id=OuterRef('pk'),
                supply_in_preorder__isnull=False,
            )
        ),
    )


_ORDER_NP_TRANSIT_STATUS_CODES = [
    '1', '2', '3', '4', '41', '5', '6', '7', '8', '10', '11', '12',
    '101', '102', '103', '104', '105', '106', '111', '112',
]


def _orders_default_ordering():
    return (
        '-isPinned',
        'isComplete',
        'dateToSend',
        Case(
            When(
                statusnpparselfromdoucmentid__status_code__in=_ORDER_NP_TRANSIT_STATUS_CODES,
                then=Value(0),
            ),
            default=Value(1),
            output_field=IntegerField(),
        ),
        '-id',
    )


def _orders_base_queryset(user):
    is_client = user.groups.filter(name='client').exists()
    ordering = _orders_default_ordering()
    if is_client:
        qs = Order.objects.filter(place__user=user).order_by(*ordering)
    else:
        qs = Order.objects.all().order_by(*ordering)
    return qs, is_client


def _orders_page_from_filtered(order_filtered, *, page_number=None, skip_pagination=False):
    if skip_pagination:
        return _orders_list_queryset(order_filtered)
    paginator = Paginator(order_filtered, 20)
    orders_page = paginator.get_page(page_number)
    page_ids = [o.pk for o in orders_page.object_list]
    if page_ids:
        annotated_by_id = {
            o.pk: o for o in _orders_list_queryset(Order.objects.filter(pk__in=page_ids))
        }
        orders_page.object_list = [annotated_by_id[pk] for pk in page_ids if pk in annotated_by_id]
    return orders_page


@login_required(login_url='login')
def orders(request):
    isClient = request.user.groups.filter(name='client').exists()
    app_settings = request.user.get_app_settings()
    disable_order_confirmation_send_action = app_settings.disable_order_confirmation_send_action
    ordersObj, _ = _orders_base_queryset(request.user)
    pinned_orders = ordersObj.filter(isPinned=True)
    pinned_orders_exists = pinned_orders.exists()
    totalCount = ordersObj.count()
    if isClient:
        title = f'Всі замовлення для {request.user.first_name} {request.user.last_name}. ({totalCount} шт.)'
    else:
        title = f'Всі замовлення. ({totalCount} шт.)'

    orderFilter = OrderFilter(request.POST or None, queryset=ordersObj)
    order_filtered = orderFilter.qs
    skip_pagination = bool(request.POST and request.POST.get('isComplete') == '0')
    orders = _orders_page_from_filtered(
        order_filtered,
        page_number=request.GET.get('page'),
        skip_pagination=skip_pagination,
    )

    is_more_then_one_order_exists_for_the_same_place = False
    uncomplete_orders_exists = False
    if not isClient:
        uncomplete_qs = ordersObj.filter(isComplete=False)
        uncomplete_orders_exists = uncomplete_qs.exists()
        is_more_then_one_order_exists_for_the_same_place = (
            uncomplete_qs.values('place_id')
            .annotate(c=Count('id'))
            .filter(c__gt=1, place_id__isnull=False)
            .exists()
        )

        if (
            'uncomplete_orders_complete_all_action' in request.POST
            or 'merge_all_orders_for_the_same_place' in request.POST
        ):
            filtered_orders = list(_orders_list_queryset(uncomplete_qs))
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
            pinned_orders_exists = pinned_orders.filter(isPinned=True).exists()
            
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
            return export_selected_orders_to_xlsx(selected_orders)

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
                               'isOrders': True,
                               'totalCount': totalCount,
                               'isOrdersTab': True,
                               'disable_order_confirmation_send_action': disable_order_confirmation_send_action,
                               'is_more_then_one_order_exists_for_the_same_place': is_more_then_one_order_exists_for_the_same_place,
                               'uncomplete_orders_exists': uncomplete_orders_exists})


    return render(request, 'supplies/orders/orders_new.html',
                  {'title': title, 
                   'orders': orders, 
                   'orderFilter': orderFilter,
                   'isOrders': True, 
                   'totalCount': totalCount,
                   'isOrdersTab': True, 
                   'disable_order_confirmation_send_action': disable_order_confirmation_send_action,
                   'pinned_orders_exists': pinned_orders_exists, 
                   'is_more_then_one_order_exists_for_the_same_place': is_more_then_one_order_exists_for_the_same_place,
                   'uncomplete_orders_exists': uncomplete_orders_exists})


@login_required(login_url='login')
def orders_analytics(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    ordersObj, is_client = _orders_base_queryset(request.user)
    orderFilter = OrderFilter(request.POST, queryset=ordersObj)
    return JsonResponse(
        build_orders_analytics(
            orderFilter.qs, include_top_places=not is_client, for_user=request.user
        )
    )





def _preorders_list_select_related(qs):
    """Картки списку звертаються до userCreated, place та place.city_ref — без цього сотні N+1."""
    return qs.select_related('userCreated', 'place', 'place__city_ref')


def _preorder_state_priority_qs(qs):
    return qs.annotate(
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
    )


def _preorders_analytics_base_queryset(user):
    is_client = user.groups.filter(name='client').exists()
    if is_client:
        return PreOrder.objects.filter(place__user=user), is_client
    return PreOrder.objects.all(), is_client


def _preorders_list_queryset(user, *, is_archive):
    is_client = user.groups.filter(name='client').exists()
    if is_client:
        qs = PreOrder.objects.filter(place__user=user)
    else:
        qs = PreOrder.objects.all()
    qs = qs.filter(isClosed=is_archive)
    qs = _preorder_state_priority_qs(qs)
    if is_client:
        return qs.order_by('isComplete', 'state_priority', '-id')
    return qs.order_by('-isPinned', 'isComplete', 'state_priority', '-id')


def _auto_close_completed_preorders(qs, *, staff_scope=False):
    if staff_scope:
        done_q = Q(state_of_delivery='Complete') | Q(state_of_delivery='Complete_Handle')
        qs.filter(done_q).update(isClosed=True, isComplete=True, isPinned=False)
    else:
        qs.filter(state_of_delivery='Complete').update(isClosed=True, isComplete=True)


@login_required(login_url='login')
def preorders(request):
    isArchiveChoosed = 'get_archive_preorders' in request.POST
    isClient = request.user.groups.filter(name='client').exists()

    orders = _preorders_list_queryset(request.user, is_archive=isArchiveChoosed)
    if not isArchiveChoosed:
        _auto_close_completed_preorders(orders, staff_scope=not isClient)

    if isClient:
        title = f'Всі передзамовлення для {request.user.first_name} {request.user.last_name}'
    else:
        title = 'Всі передзамовлення'

    preorderFilter = PreorderFilter(request.POST, queryset=orders)
    orders = _preorders_list_select_related(preorderFilter.qs)

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
                  {'title': title, 'isArchiveChoosed': isArchiveChoosed, 'orders': orders, 'preorderFilter': preorderFilter, 'isOrders': False,
                   'isPreordersTab': True})


@login_required(login_url='login')
def preorders_analytics(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    base, is_client = _preorders_analytics_base_queryset(request.user)
    preorderFilter = PreorderFilter(request.POST, queryset=base)
    return JsonResponse(
        build_preorders_analytics(
            preorderFilter.qs, include_top_places=not is_client, for_user=request.user
        )
    )


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
        orders = _preorders_list_select_related(
            PreOrder.objects.filter(place__user=request.user).order_by('-id')
        )
    else:
        orders = _preorders_list_select_related(PreOrder.objects.all().order_by('-id'))

    return render(request, 'partials/preorders/preorders-list.html',
                  {'orders': orders})


@login_required(login_url='login')
def updatePreorderStatus(request, order_id):
    order = _preorders_list_select_related(PreOrder.objects.filter(pk=order_id)).get()

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
        
    order = _preorders_list_select_related(PreOrder.objects.filter(pk=order_id)).get()
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
    
    order = _order_singleton_for_card(order_id)
    if order is None:
        return HttpResponseForbidden('Order not found')
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
    
    preorder_from_supply = None
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
                    
                    # Fix None values
                    if supp.countOnHold is None:
                        supp.countOnHold = 0
                    if supp.count is None:
                        supp.count = 0
                    
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
                        
                        # Fix None values
                        if supply_in_booked_order.countOnHold is None:
                            supply_in_booked_order.countOnHold = 0
                        if supply_in_booked_order.count_in_order is None:
                            supply_in_booked_order.count_in_order = 0
                        
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
                        
                        # Fix None values
                        if genSupInPreorder.count_in_order is None:
                            genSupInPreorder.count_in_order = 0
                        if genSupInPreorder.count_in_order_current is None:
                            genSupInPreorder.count_in_order_current = 0
                        
                        genSupInPreorder.count_in_order_current += el.count_in_order
                        
                        if genSupInPreorder.count_in_order - genSupInPreorder.count_in_order_current <= 0:
                           genSupInPreorder.state_of_delivery = 'Complete'
                        else:
                            genSupInPreorder.state_of_delivery = 'Partial'
                        
                        genSupInPreorder.save()
                        
                        if order.for_preorder is None and genSupInPreorder.supply_for_order is not None:
                            if preorder_from_supply != genSupInPreorder.supply_for_order:
                                preorder_from_supply = genSupInPreorder.supply_for_order
                                preorder_from_supply.update_order_state_of_delivery_status()
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
            
        update_order_status_core(order_id, request.user)
        order = _order_singleton_for_card(order_id)
        if order is None:
            raise ValueError('Замовлення не знайдено після оновлення')
        
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
            'message': f'№{order_id}: ' + str(e)
        }, status=400)


@login_required(login_url='login')
def ordersForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    orders = place.order_set.all().order_by('-id')
    orderFilter = OrderFilter(request.GET, queryset=orders)
    order_filtered = orderFilter.qs
    paginator = Paginator(order_filtered, 20)
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)
    page_ids = [o.pk for o in orders_page.object_list]
    if page_ids:
        annotated_by_id = {
            o.pk: o for o in _orders_list_queryset(Order.objects.filter(pk__in=page_ids))
        }
        orders_page.object_list = [annotated_by_id[pk] for pk in page_ids if pk in annotated_by_id]
    title = f'Всі замовлення для клієнта: \n {place.name}, {place.city_ref.name}'
    if not order_filtered.exists():
        title = f'В клієнта "{place.name}, {place.city_ref.name}" ще немає замовлень'

    return render(request, 'supplies/orders/orders_new.html', {
        'title': title,
        'orders': orders_page,
        'orderFilter': orderFilter,
        'isClients': True,
        'client_id': client_id,
    })


@login_required(login_url='login')
def orders_for_client_analytics(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    orders = place.order_set.all().order_by('-id')
    orderFilter = OrderFilter(request.GET, queryset=orders)
    return JsonResponse(
        build_orders_analytics(
            orderFilter.qs, include_top_places=False, for_user=request.user
        )
    )


@login_required(login_url='login')
def agreementsForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    title = f'Всі передзамовлення для клієнта: \n {place.name}, {place.city_ref.name}'
    isArchiveChoosed = 'get_archive_preorders' in request.POST
    if isArchiveChoosed:
        orders = place.preorder_set.filter(isClosed=True).order_by('-state_of_delivery', '-id')
    else:
        orders = _preorder_state_priority_qs(
            place.preorder_set.filter(isClosed=False)
        ).order_by('isComplete', 'state_priority', '-id')

    preorderFilter = PreorderFilter(request.GET, queryset=orders)
    orders = _preorders_list_select_related(preorderFilter.qs)

    if request.method == 'POST':
        selected_orders = request.POST.getlist('xls_preorder_print_buttons')
        if 'print_choosed' in request.POST:
            return generate_list_of_xls_from_preorders_list(selected_orders)
        if 'print_choosed_and_status_updated' in request.POST:
            return generate_list_of_xls_from_preorders_list(selected_orders, True)
        if 'mark_as_delivery_completed' in request.POST:
            generate_list_of_xls_from_preorders_list(selected_orders, False, True)

    return render(request, 'supplies/orders/preorders.html',
           {'title': title, 'orders': orders, 'preorderFilter': preorderFilter,
            'isOrders': True,
            'isArchiveChoosed': isArchiveChoosed,
            'isPreordersTab': True, 'fromClientList': True,
            'client_id': client_id})


@login_required(login_url='login')
def agreements_for_client_analytics(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    preorderFilter = PreorderFilter(request.GET, queryset=place.preorder_set.all())
    return JsonResponse(
        build_preorders_analytics(
            preorderFilter.qs, include_top_places=False, for_user=request.user
        )
    )


@login_required(login_url='login')
def devicesForClient(request, client_id):
    place = get_object_or_404(Place.objects.select_related('city_ref'), pk=client_id)
    devices = devices_list_queryset(place.device_set.all())
    title = f'Всі прилади для клієнта: \n {place.name}, {place.city_ref.name}'
    if not devices:
        title = f'В клієнта "{place.name}, {place.city_ref.name}" ще немає замовлень'

    return render(request, 'supplies/devices/devices.html',
                  {'title': title, 'devices': devices, 'isClients': True})


def devicesList(request):
    devices = devices_list_queryset(Device.objects.all().order_by('-id'))
    devFilters = DeviceFilter(request.GET, queryset=devices)
    devices = devFilters.qs
    title = f'Вcі прилади'
    return render(request, 'supplies/devices/devices.html',
                  {'title': title, 'devices': devices, 'filter': devFilters,
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

    place = get_object_or_404(Place.objects.select_related('city_ref'), pk=client_id)
    serviceNotes = servicenotes_list_queryset(place.servicenote_set.all())
    title = f'Всі сервісні замітки для клієнта: \n {place.name}, {place.city}'
    return render(request, 'supplies/service/serviceNotes.html',
                  {'title': title, 'serviceNotes': serviceNotes, 'form': form,
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
    return render(request, 'supplies/service/createNote.html',
                  {'title': f'Створити новий запис', 'form': form,
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
    return render(request, 'supplies/service/createNote.html',
                  {'title': f'Створити новий запис', 'form': form,
                   'isHiddenPlace': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'engineer'])
def updateNote(request, note_id):
    note = ServiceNote.objects.get(id=note_id)
    form = ServiceNoteForm(instance=note)
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST, instance=note)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = CustomUser.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    return render(request, 'supplies/service/createNote.html',
                  {'title': f'Редагувати запис №{note_id}', 'form': form,
                   'isService': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateSupply(request, supp_id):
    note = Supply.objects.get(id=supp_id)
    generalSupp = note.general_supply
    form = SupplyForm(instance=note)
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
                  {'form': form,
                   'title': 'Редагувати LOT товара',
                   'suppId': supp_id, 'editMode': True, 'generalSupp': generalSupp})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def addSupplyToExistOrder(request, supp_id):
    supp = Supply.objects.get(id=supp_id)
    orderForm = OrderForm(request.POST or None)
    supply = SupplyInOrderInCart(count_in_order=1, supply=supp, lot=supp.supplyLot, date_expired=supp.expiredDate)
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
                  {'form': orderForm, 'supplies': [supply], 'placeExist': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl', 'client'])
def addSupplyToExistPreOrder(request, supp_id):
    supp = Supply.objects.get(id=supp_id)
    orderForm = PreOrderForm(request.POST or None)
    supply = SupplyInOrderInCart(count_in_order=1, supply=supp, lot=supp.supplyLot, date_expired=supp.expiredDate)
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
                  {'form': orderForm, 'supplies': [supply], 'placeExist': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl', 'client'])
def addSupplyToExistPreOrderGeneral(request, supp_id):
    general_supp = GeneralSupply.objects.get(id=supp_id)
    orderForm = PreOrderForm(request.POST or None)
    supply = SupplyInPreorderInCart(count_in_order=1, supply_for_order=None, general_supply=general_supp)
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
                  {'form': orderForm, 'supplies': [supply]})


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
    generalSupp = GeneralSupply.objects.select_related('category').get(id=supp_id)
    # supplies = generalSupp.supplyforhistory_set.all().order_by('-id')
    in_orders = (
        generalSupp.inGeneralSupp.all()
        .order_by('-id')
        .select_related('supply_for_order__place__city_ref')
    )
    total_count_in_orders = in_orders.aggregate(total_count=Sum('count_in_order'))['total_count']

    in_preorders = (
        generalSupp.supplyinpreorder_set.all()
        .order_by('-id')
        .select_related('supply_for_order__place__city_ref')
    )
    total_count_in_preorders = in_preorders.aggregate(total_count=Sum('count_in_order'))['total_count']

    in_deliveries = (
        generalSupp.deliverysupplyincart_set.all()
        .order_by('-id')
        .select_related('delivery_order')
    )
    total_count_in_deliveries = in_deliveries.aggregate(total_count=Sum('count'))['total_count']

    in_booked_sup = (
        generalSupp.supplyinbookedorder_set.all()
        .order_by('-id')
        .select_related('supply_for_place__city_ref', 'supply')
    )
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
                   'total_count_in_deliveries': total_count_in_deliveries})



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
                  {'title': f'Додати новий товар', 'form': form})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def addNewCity(request):
    form = NewCityForm()
    if request.method == 'POST':
        form = NewCityForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Місто додано')
            return redirect('add-new-city')

    cities = City.objects.annotate(
        place_count=Count('place', distinct=True),
    ).order_by('name')
    for city in cities:
        city.device_count = Device.objects.filter(in_city_id=city.id).count()
    return render(request, 'supplies/supplies/add_city.html', {
        'title': 'Міста',
        'form': form,
        'cities': cities})


def _annotate_city_counts(city):
    city.place_count = Place.objects.filter(city_ref=city).count()
    city.device_count = Device.objects.filter(in_city=city).count()
    return city


def _cascade_delete_city(city):
    Place.objects.filter(city_ref=city).delete()
    Device.objects.filter(in_city=city).delete()
    city.delete()


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def update_city(request, city_id):
    city = get_object_or_404(City, id=city_id)
    name = (request.POST.get('name') or '').strip()
    if name:
        city.name = name
        city.save()
    return render(request, 'partials/supplies/city_row.html', {
        'city': _annotate_city_counts(city)})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
@transaction.atomic
def delete_city(request, city_id):
    city = get_object_or_404(City, id=city_id)
    _cascade_delete_city(city)
    return HttpResponse('')


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def addNewCategory(request):
    form = NewCategoryForm()
    if request.method == 'POST':
        form = NewCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категорію додано')
            return redirect('add-new-supply-category')

    categories = Category.objects.annotate(
        general_supply_count=Count('generalsupply', distinct=True),
    ).order_by('name')
    for category in categories:
        category.supply_lot_count = Supply.objects.filter(
            Q(category_id=category.id) | Q(general_supply__category_id=category.id)
        ).distinct().count()
    return render(request, 'supplies/supplies/add_supply_category.html', {
        'title': 'Категорії товарів',
        'form': form,
        'categories': categories})


def _annotate_category_counts(category):
    category.general_supply_count = GeneralSupply.objects.filter(category=category).count()
    category.supply_lot_count = Supply.objects.filter(
        Q(category_id=category.id) | Q(general_supply__category_id=category.id)
    ).distinct().count()
    return category


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def update_supply_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    name = (request.POST.get('name') or '').strip()
    if name:
        category.name = name
        category.save()
    return render(request, 'partials/supplies/category_row.html', {
        'category': _annotate_category_counts(category)})


def _cascade_delete_category(category):
    general_supplies = GeneralSupply.objects.filter(category=category)
    gs_ids = list(general_supplies.values_list('pk', flat=True))

    if gs_ids:
        SupplyInPreorder.objects.filter(generalSupply_id__in=gs_ids).delete()
        SupplyInOrder.objects.filter(generalSupply_id__in=gs_ids).delete()
        general_supplies.delete()

    Supply.objects.filter(category=category).delete()
    category.delete()


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
@transaction.atomic
def delete_supply_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    _cascade_delete_category(category)
    return HttpResponse('')



@login_required(login_url='login')
def addgeneralSupplyOnly(request):
    form = NewGeneralSupplyForm()
    if request.method == 'POST':
        form = NewGeneralSupplyForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Назву товару додано')
            return redirect('add-general-supply')

    return render(request, 'supplies/supplies/add_general_supply.html', {
        'title': 'Назви товарів',
        'form': form})


ADD_CLIENT_TEMPLATE = 'supplies/clients/add_client.html'


def _render_add_client_page(request, form):
    return render(request, ADD_CLIENT_TEMPLATE, {
        'title': 'Додати нового клієнта',
        'form': form})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def addNewClient(request):
    form = CreateClientForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        name = form.cleaned_data['name']
        city_ref = form.cleaned_data['city_ref']
        address = form.cleaned_data['address']
        link = form.cleaned_data['link']
        organization_code = form.cleaned_data['organization_code']
        isPrivatePlace = form.cleaned_data['isPrivatePlace']

        org = Place(name=name, city_ref=city_ref, address=address, link=link, isPrivatePlace=isPrivatePlace)

        if organization_code:
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

            if data.get("errors"):
                for error in data["errors"]:
                    messages.error(request, error)
                return _render_add_client_page(request, form)

        org.save()
        allowed_categories = form.cleaned_data.get('allowed_categories')
        if allowed_categories:
            org.allowed_categories.set(allowed_categories)
        messages.success(request, 'Клієнта додано')
        return redirect('/clientsInfo')

    return _render_add_client_page(request, form)


@login_required(login_url='login')
def addNewDeviceForClient(request, client_id):
    client = Place.objects.get(id=client_id)
    form = DeviceForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            form_to_save = form.save(commit=False)  # gives you the instance without saving it
            form_to_save.in_city = client.city_ref
            form_to_save.in_place = client
            form_to_save.save()
            return redirect('/clientsInfo')

    return render(request, 'supplies/supplies/createSupply.html',
                  {'title': f'Додати прилад для: \n {client.name}, {client.city_ref.name}', 'form': form})


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
                    refNP = settings.NOVA_POSHTA_SENDER_DMDX_REF_PRIVATE_COUNTERAGENT

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
        
        place_for_card = _place_singleton_for_client_card(place.id) or place
        html = render_to_string('partials/clients/client_card.html', {
            'client': place_for_card,
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
                  {'title': f'Редагувати клієнта: {client.name}, {client.city_ref.name}',
                   'title_icon': 'bi-pencil-square',
                   'place': client, 'form': form, 'workersSetExist': workersSetExist, 'adressSetExist': adressSetExist,
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
            place_for_card = _place_singleton_for_client_card(place.id) or place
            html = render_to_string('partials/clients/client_card.html', {
                'client': place_for_card,
                'request': request})
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
    if not getattr(settings, 'ENABLE_WKHTMLTOPDF', True):
        return HttpResponse('PDF (xhtml2pdf) вимкнено (LIGHTWEIGHT_MODE)', status=503)

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



@login_required(login_url='login')
def orderDetail_add_comment(request):
    order_id = request.POST.get("order_id")
    comment = ""
    if order_id:
        try:
            order = Order.objects.get(pk=order_id)
            comment = order.comment or ""
        except (Order.DoesNotExist, ValueError):
            pass
    return render(request, 'partials/common/comment_input_textfield_area.html', {'order_id': order_id, 'comment': comment})


@login_required(login_url='login')
def orderDetail_save_comment(request):
    order_id = request.POST.get("order_id")
    comment_textfield = request.POST.get("comment_textfield")
    if isinstance(comment_textfield, str):
        comment_textfield = comment_textfield.replace("\r\n", "\n").replace("\r", "\n")
    order = Order.objects.get(id=order_id)
    order.comment = comment_textfield
    order.save(update_fields=["comment"])

    print("order_id = ", order_id)
    print("comment_textfield = ", comment_textfield)
    return render(request, 'partials/common/comment_textfield_area.html', {'order': order})


@login_required(login_url='login')
def home_general_supply_info(request, supp_id):
    if not (request.user.groups.filter(name='empl').exists() or request.user.is_staff):
        return HttpResponseForbidden('Немає доступу')
    general_supp = get_object_or_404(
        GeneralSupply.objects.select_related('category'),
        pk=supp_id,
    )
    return render(
        request,
        'partials/supplies/home_general_supply_info_modal.html',
        {'generalSupp': general_supp},
    )


@login_required(login_url='login')
def order_detail_general_supply_info(request, order_id, supp_id):
    if not (request.user.groups.filter(name='empl').exists() or request.user.is_staff):
        return HttpResponseForbidden('Немає доступу')
    order = get_object_or_404(_order_detail_single(order_id), pk=order_id)
    general_supp = get_object_or_404(
        GeneralSupply.objects.select_related('category'),
        pk=supp_id,
    )
    order_lines = (
        SupplyInOrder.objects.filter(
            supply_for_order_id=order_id,
            generalSupply_id=supp_id,
        )
        .select_related(
            'supply',
            'supply_in_preorder',
            'supply_in_preorder__supply_for_order',
        )
        .order_by('lot', 'id')
    )
    return render(
        request,
        'partials/orders/orderDetail_general_supply_info_modal.html',
        {
            'generalSupp': general_supp,
            'order': order,
            'order_lines': order_lines,
        },
    )


def _order_detail_print_sheet_data(order_id):
    order = _order_detail_single(order_id).filter(pk=order_id).first()
    if not order:
        return None
    supplies_qs = SupplyInOrder.objects.filter(supply_for_order_id=order_id).select_related(
        'generalSupply',
        'generalSupply__category',
        'supply',
        'supply_in_preorder',
        'supply_in_preorder__supply_for_order',
    )
    supply_groups = _group_order_supplies_for_display(supplies_qs)
    total_supply_rows = sum(len(g['items']) for g in supply_groups)
    return {
        'order': order,
        'supply_groups': supply_groups,
        'total_supply_rows': total_supply_rows,
    }


@login_required(login_url='login')
def orderDetail_print_bulk(request):
    ids_raw = request.GET.get('ids', '')
    order_ids = []
    for part in ids_raw.split(','):
        part = part.strip()
        if part.isdigit():
            order_ids.append(int(part))

    seen = set()
    print_orders = []
    for order_id in order_ids:
        if order_id in seen or len(print_orders) >= 50:
            continue
        seen.add(order_id)
        sheet = _order_detail_print_sheet_data(order_id)
        if sheet:
            print_orders.append(sheet)

    return render(
        request,
        'supplies/orders/orderDetail_print_bulk.html',
        {
            'title': f'Друк — {len(print_orders)} замовлень',
            'print_orders': print_orders,
            'is_print': True,
        },
    )


@login_required(login_url='login')
def orderDetail_print(request, order_id):
    sheet = _order_detail_print_sheet_data(order_id)
    if not sheet:
        raise Http404

    return render(
        request,
        'supplies/orders/orderDetail_print.html',
        {
            'title': f'Друк — Замовлення № {order_id}',
            'order': sheet['order'],
            'supply_groups': sheet['supply_groups'],
            'total_supply_rows': sheet['total_supply_rows'],
            'is_print': True,
        },
    )


@login_required(login_url='login')
def orderDetail(request, order_id, sup_id):
    order = get_object_or_404(_order_detail_single(order_id), pk=order_id)
    supplies_qs = SupplyInOrder.objects.filter(supply_for_order_id=order_id).select_related(
        'generalSupply',
        'generalSupply__category',
        'supply',
        'supply_in_preorder',
        'supply_in_preorder__supply_for_order',
    )
    supply_groups = _group_order_supplies_for_display(supplies_qs)
    next = request.POST.get('next')

    if request.method == 'POST':
        if 'delete' in request.POST:
            next = request.POST.get('next')
            if not order.isComplete:
                supps = supplies_qs
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
                  {'title': f'Замовлення № {order_id}', 'order': order, 'supply_groups': supply_groups,
                   'isOrders': True, 'highlighted_sup_id': sup_id})

@login_required(login_url='login')
@transaction.atomic
def order_add_to_preorder(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    # Get all general supplies from the order
    order_general_supplies = order.supplyinorder_set.values_list('generalSupply', flat=True).distinct()
    # Get preorders and annotate with hasSupsInOrder
    preorders = order.place.preorder_set.filter(
        Q(state_of_delivery='Awaiting') | 
        Q(state_of_delivery='Partial') | 
        Q(state_of_delivery='accepted_by_customer')
    ).annotate(
        hasSupsInOrder=Exists(
            SupplyInPreorder.objects.filter(
                supply_for_order=OuterRef('pk'),
                generalSupply__in=order_general_supplies
            )
        )
    )
    if request.method == 'POST':
        next = request.POST.get('next')
        if 'save' in request.POST:
            selected_preorder_id = request.POST.get('selectedPreorder')
            if selected_preorder_id:
                selectedPreorder = PreOrder.objects.get(id=selected_preorder_id)
                sups_in_preorder = selectedPreorder.supplyinpreorder_set.all()
                sups_in_order = order.supplyinorder_set.all()
                order.for_preorder = selectedPreorder
                order.save(update_fields=['for_preorder'])
                for supp in sups_in_order:
                    if not supp.supply_in_preorder:
                        try:
                            supp.supply_in_preorder = sups_in_preorder.get(generalSupply=supp.generalSupply)
                            supp.save(update_fields=['supply_in_preorder'])
                        except:
                            pass
                        
                if order.isComplete:
                    for supp in sups_in_order:
                        genSupInPreorder = supp.supply_in_preorder
                        genSupInPreorder.count_in_order_current += supp.count_in_order
                        if genSupInPreorder.count_in_order - genSupInPreorder.count_in_order_current <= 0:
                            genSupInPreorder.state_of_delivery = 'Complete'
                        else:
                            genSupInPreorder.state_of_delivery = 'Partial'
                        genSupInPreorder.save(update_fields=['count_in_order_current', 'state_of_delivery'])
                    selectedPreorder.update_order_state_of_delivery_status()
                        
            return JsonResponse({
            'success': True
        })            
    
    return render(request, 'supplies/orders/order_add_to_preorder.html',
                  {'title': f'Додати до передзамовлення', 'order': order, 'preorders': preorders})

@login_required(login_url='login')
def preorderDetail(request, order_id, sup_id=None):
    order = get_object_or_404(PreOrder.objects.select_related('place'), pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.select_related(
        'generalSupply',
        'generalSupply__category'
    ).prefetch_related('supplyinorder_set').all()
    # Optimize the related orders query
    all_related_orders = _orders_list_queryset(
        Order.objects.filter(
            Q(for_preorder=order) | Q(related_preorders=order)
        ).distinct()
    ).order_by('-id')
    
    if order.isPreorder:
        title = f'Передзамовлення № {order_id}'
    else:
        title = f'Договір № {order_id}'

    return render(request, 'supplies/orders/preorderDetail.html',
                  {'title': title, 'order': order, 'supplies': supplies_in_order, 'isOrders': True, 'all_related_orders': all_related_orders,
                   'highlighted_sup_id': sup_id})


@login_required(login_url='login')
def preorder_detail_status_oob(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    return render(request, 'partials/preorders/preorder_detail_oob_refresh.html', {'order': order})
    
@login_required(login_url='login')
def preorderDetailModal(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all()
    return render(request, 'supplies/orders/preorderDetailModal.html',
                  {'title': f'Передзамовлення № {order_id}', 'order': order, 'supplies': supplies_in_order})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
@transaction.atomic
def preorderDetail_generateOrder(request, order_id):
    order = get_object_or_404(PreOrder, pk=order_id)
    supplies_in_order = order.supplyinpreorder_set.all().order_by('id')
    orderForm = OrderInCartForm(request.POST or None)
    uncompleted_orders = order.place.order_set.filter(isComplete=False)

    if request.method == 'POST':
        checkBoxSuppIdList = request.POST.getlist('flexCheckDefault')
        count_list = request.POST.getlist('count_list')
        count_list_id = request.POST.getlist('count_list_id')
        booked_items_id = request.POST.getlist('booked_items_id')
        comment_for_order = request.POST.get('comment_for_order')
        count_for_id_dict = dict(zip(count_list_id, count_list))
        result = {k: v for k, v in count_for_id_dict.items() if k in checkBoxSuppIdList}

        # Get the selected action and order
        order_action = request.POST.get('orderAction')
        selected_order_id = request.POST.get('uncompleted_orders')

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
                is_new_order = not (order_action == 'existing' and selected_order_id)
                # If adding to existing order
                if order_action == 'existing' and selected_order_id:
                    new_order = Order.objects.get(id=selected_order_id)
                    if orderForm.is_valid():
                        comment = orderForm.cleaned_data['comment']
                        dateToSend = orderForm.cleaned_data['dateToSend']
                        if comment:
                           old_comment = new_order.comment or ""
                           new_order.comment = old_comment + f"\n{comment}"
                        new_order.dateToSend = dateToSend
                else:
                    # Create new order
                    new_order = Order(userCreated=request.user, place=order.place,
                                    comment=comment_for_order)
                    if orderForm.is_valid():
                        comment = orderForm.cleaned_data['comment']
                        dateToSend = orderForm.cleaned_data['dateToSend']
                        new_order.comment = comment
                        new_order.dateToSend = dateToSend
                new_order.save()
                new_order.add_preorder_to_related(order)
                
                sups_for_preorder = []
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
                            sups_for_preorder.append(suppInOrder)
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
                            sups_for_preorder.append(supInOrder)
                            s.countOnHold += s.count
                            s.save(update_fields=['countOnHold'])
                            
                if order_action == 'existing' and selected_order_id:
                    print("start merging")
                    merged_sups = []
                    existing_sups_in_order = new_order.supplyinorder_set.all()
                    sups_for_preorder.extend(existing_sups_in_order)
                    preorders_by_key = defaultdict(list)
                    sups_for_preorder = [sio for sio in sups_for_preorder if sio.supply_in_preorder is not None]
                    for sio in sups_for_preorder:
                        # Get the PreOrder associated with this SupplyInPreorder
                        key = (sio.supply_in_preorder, sio.supply)  # Create a tuple as composite key
                        preorders_by_key[key].append(sio)
                        
                    for (preorder, supply), sio_list in preorders_by_key.items():
                        total_count = sum(sio.count_in_order for sio in sio_list)
                        template_sio = sio_list[0]
                        print("sup: ", supply.general_supply.name)
                        print("total_count: ", total_count)
                        merged_sup = SupplyInOrder(
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
                        merged_sups.append(merged_sup)
                    for sup in sups_for_preorder:
                        if sup.id is not None:  # Only delete if the object has been saved to DB
                            sup.delete()
                    for sio in merged_sups:
                        sio.save()
                else:
                    for sio in sups_for_preorder:
                        sio.save()
                                
                if is_new_order:
                    sendPushMsgCart(new_order)
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
                  {'title': f'Передзамовлення № {order_id}', 'order': order, 'orderForm': orderForm, 'supplies': supplies_in_order, 'isOrders': True, 'uncompleted_orders': uncompleted_orders})


def _place_list_for_client_cards(place_qs):
    """Список організацій для карток /clientsInfo: анотації замість N+1 .count() у шаблоні."""
    return (
        place_qs.select_related('city_ref', 'worker_NP')
        .prefetch_related('workers')
        .annotate(
            card_preorder_count=related_count_subquery(PreOrder, 'place_id'),
            card_order_count=related_count_subquery(Order, 'place_id'),
            card_workers_count=related_count_subquery(Workers, 'for_place_id'),
            card_booked_count=related_count_subquery(SupplyInBookedOrder, 'supply_for_place_id'),
            card_servicenote_count=related_count_subquery(ServiceNote, 'for_place_id'),
            card_device_count=related_count_subquery(Device, 'in_place_id'),
        )
        .order_by('-id')
    )


def _place_singleton_for_client_card(place_id):
    """Один Place з тими ж анотаціями — для render_to_string після збереження працівника."""
    return _place_list_for_client_cards(Place.objects.filter(pk=place_id)).first()


def _clients_info_filtered_places(request):
    placeFilter = PlaceFilter(request.GET, queryset=Place.objects.all().order_by('-id'))
    return placeFilter, placeFilter.qs.order_by('-id')


CLIENTS_LIST_PAGE_SIZE = 10


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def clientsInfo(request):
    placeFilter, place_filtered = _clients_info_filtered_places(request)
    paginator = Paginator(place_filtered, CLIENTS_LIST_PAGE_SIZE)
    page_number = request.GET.get('page')
    place_page = paginator.get_page(page_number)
    page_ids = [p.pk for p in place_page.object_list]
    if page_ids:
        annotated_by_id = {
            p.pk: p for p in _place_list_for_client_cards(Place.objects.filter(pk__in=page_ids))
        }
        place_page.object_list = [annotated_by_id[pk] for pk in page_ids if pk in annotated_by_id]
    return render(request, 'supplies/clients/clientsList.html',
                  {'title': f'Клієнти', 'clients': place_page, 'placeFilter': placeFilter,
                   'isClients': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'empl'])
def clientsInfo_analytics(request):
    _, place_filtered = _clients_info_filtered_places(request)
    return JsonResponse(build_clients_info_analytics(place_filtered))


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

    serviceFilters = ServiceNotesFilter(request.GET, queryset=ServiceNote.objects.all().order_by('-id'))
    serviceNotes = servicenotes_list_queryset(serviceFilters.qs)
    return render(request, 'supplies/service/serviceNotes.html',
                  {'title': f'Сервiсні записи', 'serviceNotes': serviceNotes,
                   'form': form, 'serviceFilters': serviceFilters, 'isService': True})
    
    
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
    
        

@login_required
@allowed_users(allowed_roles=['admin', 'empl'])
def analytics_report(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    # Отримуємо аналітичний звіт
    report = PreorderAnalytics(place).get_analytics_report()
    
    context = {
        'title': f'Аналітика передзамовлень для:\n{ place.get_place_name() }',
        'report': report}
    return render(request, 'supplies/analytics_report.html', context)

@login_required
@allowed_users(allowed_roles=['admin', 'empl'])

@login_required
def analytics_preorders_list_for_client(request):
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
        'place_id': place_id,
        'booked_list_exist': booked_list_exist,
        'isAnalytics': True,
        'isAll': False,
        'isBookedList': False}
    return render(request, 'supplies/clients/analytics_preorders_list.html', context)


def teams_reminders_task():
    from .push_notifications import notify_staff_reminder

    order_to_send_today = Order.objects.filter(dateToSend=date.today(), isComplete=False)
    order_to_send_today_count = order_to_send_today.count()
    if order_to_send_today_count > 0:
        title = f'Відправити замовлень сьогодні: {order_to_send_today_count} шт.'
        order_info = ''
        for order in order_to_send_today:
            order_info += f'№{order.id}: {order.place.name}, {order.place.city_ref.name}\n'
        notify_staff_reminder(title, order_info.strip(), 'reminder_orders')

    current_date = timezone.now().date()
    places_with_preorders = Place.objects.filter(preorder__isnull=False, preorder__isPreorder=True).distinct()
    place_ids = list(places_with_preorders.values_list('pk', flat=True))
    predictions = bulk_predict_next_order_dates(place_ids)
    places_needing_order = [
        pid for pid, predicted in predictions.items()
        if predicted == current_date
    ]
    place_need_preorder_today = Place.objects.filter(id__in=places_needing_order)
    place_need_preorder_today_count = place_need_preorder_today.count()
    if place_need_preorder_today_count > 0:
        title = f'Рекомендовані передзамовлення сьогодні: {place_need_preorder_today_count}'
        place_info = ''
        for place in place_need_preorder_today:
            place_info += f'{place.name}, {place.city_ref.name}\n'
        notify_staff_reminder(title, place_info.strip(), 'reminder_preorders')

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
        orders_with_booked = [sio for sio in supply_in_orders if sio.supply_in_booked_order is not None and sio.supply_in_preorder is None]
        
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
            key = (sio.supply_in_preorder, sio.supply)  # Create a tuple as composite key
            preorders_by_key[key].append(sio)
            
        for (preorder, supply), sio_list in preorders_by_key.items():
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
        sendPushMsgCart(new_order)
        for order in orders:
            order.delete()
    
    return merged_orders

@login_required
@allowed_users(allowed_roles=['admin', 'empl'])
def preorder_items_table(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    
    # Отримуємо всі передзамовлення для цього місця
    preorders = PreOrder.objects.filter(place=place).order_by('-dateCreated')
    
    # Отримуємо всі товари з передзамовлень, згруповані за generalSupply
    preorder_items = SupplyInPreorder.objects.filter(
        supply_for_order__in=preorders
    ).values(
        'generalSupply',
        'generalSupply__name',
        'generalSupply__ref',
        'generalSupply__SMN_code',
        'generalSupply__package_and_tests',
        'generalSupply__category__name'
    ).annotate(
        total_quantity=Sum('count_in_order'),
        avg_quantity=Avg('count_in_order'),
        last_order_date=Max('supply_for_order__dateCreated'),
        order_count=Count('supply_for_order', distinct=True)  # Count of unique orders for each item
    ).order_by('-total_quantity')
    
    context = {
        'title': f'Статистика всіх замовлених товарів в передзамовленнях для:\n{place.get_place_name()}',
        'place': place,
        'preorder_items': preorder_items}
    return render(request, 'supplies/preorder_items_table.html', context)

@login_required
@allowed_users(allowed_roles=['admin', 'empl'])


@login_required
def staff_users_last_seen(request):
    if not request.user.is_staff:
        return HttpResponseForbidden('Доступ лише для staff.')
    ordering = (F('last_seen').desc(nulls_last=True), 'username')
    client_users = CustomUser.objects.filter(groups__name='client').distinct().order_by(*ordering)
    staff_users = CustomUser.objects.exclude(groups__name='client').order_by(*ordering)
    return render(request, 'supplies/staff/users_last_seen.html', {
        'title': 'Остання активність користувачів',
        'client_users': client_users,
        'staff_users': staff_users,
    })

