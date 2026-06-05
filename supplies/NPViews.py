from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, FileResponse, JsonResponse
from .NPModels import *
from .views import delete_np_parsel_document, update_order_status_core, _order_singleton_for_card
from .forms import *
import json
from django.contrib import messages
import requests
from django_htmx.http import trigger_client_event
import threading
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
import datetime
import logging
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List, Tuple
import time
from django.db.models import QuerySet
from django.utils import timezone
import ssl
from django.core.paginator import Paginator
from django.core.cache import cache

logger = logging.getLogger(__name__)

from .topbar_cart_counts import queryset_orders_with_uncompleted_np_tracking


def sendTurboSMSRequest(text, recipients):
    auth_token = 'b38b9b168929ecd6568ceede5432f2cd7b12d1c8'
    hed = {'Authorization': 'Bearer ' + auth_token}
    data = {
        "recipients": recipients,
        "sms": {
            "sender": "DIAMEDIX",
            "text": text,
        }
    }

    url = 'https://api.turbosms.ua/message/send.json'
    response = requests.post(url, json=data, headers=hed)
    print(response)
    print(response.json())


def httpRequest(request):


    param = {'apiKey': settings.NOVA_POSHTA_API_KEY,
             'modelName': 'Counterparty',
             'calledMethod': 'getCounterpartyContactPersons',
             'methodProperties': {'Ref': settings.NOVA_POSHTA_SENDER_DMDX_REF}}

    getListOfCitiesParams = {
        "apiKey": settings.NOVA_POSHTA_API_KEY,
        "modelName": "Address",
        "calledMethod": "getCities",
        "methodProperties": {
            "Page" : "0"
        }
    }
    user = request.user
    data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(param)).json()
    #
    # for obj in data["data"]:
    #     if obj["Description"] == 'Степанов Олександр Вячеславович':
    #         print(obj["Ref"], obj["Phones"])
    #         user.np_contact_sender_ref = obj["Ref"]
    #         user.mobNumber = obj["Phones"]
    #         user.save()

    return render(request, "supplies/http_response.html", {'data': data["data"]})


def nova_poshta_registers(request):
    registers = RegisterNPInfo.objects.all().order_by('-id')
    paginator = Paginator(registers, 6)
    page_number = request.GET.get('page')
    registers = paginator.get_page(page_number)
    return render(
        request,
        'supplies/nova_poshta/nova_poshta_registers.html',
        {
            'title': 'Реєстри Нової Пошти',
            'title_icon': 'bi-truck',
            'subtitle': 'Штрихкоди та PDF реєстрів відправлень; номери замовлень у кожному реєстрі.',
            'registers': registers,
        },
    )



def get_register_for_orders(request):
    cheked = False
    if request.method == 'POST':
        selected_orders = request.POST.getlist('register_print_buttons')
        cheked = len(selected_orders) > 0
    return render(request, 'partials/register_print_orders_chekbox_buttons.html', {'cheked': cheked})

def get_print_xls_for_preorders(request):
    cheked = False
    if request.method == 'POST':
        selected_orders = request.POST.getlist('xls_preorder_print_buttons')
        cheked = len(selected_orders) > 0
        print(selected_orders)
        print(cheked)
    return render(request, 'partials/preorders/xls_preorders_print_buttons.html', {'cheked': cheked})


def add_more_np_places_input_group(request):
    print("add_more_np_places_input_group")
    return render(request, 'partials/delivery/add_more_np_places_input_group.html', {})

def minus_add_more_np_places_input_group(request):
    return HttpResponse(status=200)


def copy_np_places_input_group(request):
    width = request.POST.get('width')
    length = request.POST.get('length')
    height = request.POST.get('height')
    weight = request.POST.get('weight')
    data = { 'width': width, 'length': length, 'height': height, 'weight': weight }
    return render(request, 'partials/delivery/add_more_np_places_input_group.html', data)


def threading_create_np_document_async(request, data, order_id, redirect_url=False):
    order = Order.objects.get(id=order_id)
    user = request.user
    for_place = order.place
    deliveryInfo = for_place.address_NP
    deliveryType = deliveryInfo.deliveryType
    sender_places = SenderNPPlaceInfo.objects.filter(for_user=request.user)

    inputForm = CreateNPParselForm(data, instance=order)
    placeForm = ClientFormForParcel(data, instance=for_place)
    inputForm.fields['sender_np_place'].queryset = sender_places
    placeForm.fields['worker_NP'].queryset = for_place.workers.all()
    placeForm.fields['address_NP'].queryset = for_place.delivery_places.all()

    if inputForm.is_valid() and placeForm.is_valid():
        dateSend = inputForm.cleaned_data['dateDelivery'].strftime('%d.%m.%Y')
        sender_np_place = inputForm.cleaned_data['sender_np_place']
        payment_money_type = inputForm.cleaned_data['payment_money_type']
        payment_user_type = inputForm.cleaned_data['payment_user_type']
        width = inputForm.cleaned_data['width']
        length = inputForm.cleaned_data['length']
        height = inputForm.cleaned_data['height']
        weight = inputForm.cleaned_data['weight']
        description = inputForm.cleaned_data['description']
        cost = inputForm.cleaned_data['cost']
        cargo_type = inputForm.cleaned_data['cargo_type']
        sender_ref = settings.NOVA_POSHTA_SENDER_DMDX_REF

        volumeGeneral = float(width / 100) * float(length / 100) * float(height / 100)

        sender_place = inputForm.cleaned_data['sender_np_place']
        recipient_address = placeForm.cleaned_data['address_NP']
        recipient_worker = placeForm.cleaned_data['worker_NP']

        weight_input_field_list = data.getlist('weight_input_field') or []
        width_input_field_list = data.getlist('width_input_field') or []
        length_input_field_list = data.getlist('length_input_field') or []
        height_input_field_list = data.getlist('height_input_field') or []
        
        if cargo_type == CargoType.DOCUMENTS.value:
            print("cargo_type DOCUMENTS: ", cargo_type)
            options_seat_list = [{
                "weight": str(weight)
            }]
        else:
            volumetric_volume = float(width) / 100 * float(length) / 100 * float(height) / 100
            options_seat_list = [{
            "volumetricVolume": str(volumetric_volume),
            "volumetricWidth": str(width),
            "volumetricLength": str(length),
            "volumetricHeight": str(height),
            "weight": str(weight)
            }]
            
        for i in range(len(weight_input_field_list)):
            cell_weight = weight_input_field_list[i]
            cell_width = width_input_field_list[i]
            cell_length = length_input_field_list[i]
            cell_height = height_input_field_list[i]
            if cargo_type == CargoType.DOCUMENTS.value:
                options_seat = {
                "weight": str(cell_weight)
            }
            else:
                volumetric_volume_cell = float(cell_width) / 100 * float(cell_length) / 100 * float(cell_height) / 100
                options_seat = {
                "volumetricVolume": str(volumetric_volume_cell),
                "volumetricWidth": str(cell_width),
                "volumetricLength": str(cell_length),
                "volumetricHeight": str(cell_height),
                "weight": str(cell_weight)
            }
            options_seat_list.append(options_seat)

        params = {
            "apiKey": settings.NOVA_POSHTA_API_KEY,
            "modelName": "InternetDocument",
            "calledMethod": "save",
            "methodProperties": {
                "PayerType": payment_user_type,
                "PaymentMethod": payment_money_type,
                "DateTime": dateSend,
                "CargoType": cargo_type,
                "ServiceType": f'{sender_place.deliveryType}{deliveryType}',
                "Description": description,
                "Cost": str(cost),
                "CitySender": sender_np_place.city_ref_NP,
                "Sender": sender_ref,
                "SenderAddress": sender_np_place.address_ref_NP,
                "ContactSender": request.user.np_contact_sender_ref,
                "SendersPhone": request.user.mobNumber,
                "CityRecipient": recipient_address.city_ref_NP,
                "Recipient": recipient_worker.ref_counterparty_NP,
                "RecipientAddress": recipient_address.address_ref_NP,
                "ContactRecipient": recipient_worker.ref_NP,
                "RecipientsPhone": recipient_worker.telNumber,
                "OptionsSeat": options_seat_list,
            }
        }

        data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
        
        workr_postition = ''
        if recipient_worker.position:
            workr_postition = recipient_worker.position

        worker_name = f'{recipient_worker}, {workr_postition}, телефон: {recipient_worker.telNumber}'
        address_name = f'{recipient_address.cityName}, {recipient_address.addressName}'

        if data["success"] is True and data["data"][0] is not None:
            list = data["data"][0]
            ref = list["Ref"]
            cost = list["CostOnSite"]
            estimated_date = list["EstimatedDeliveryDate"]
            id_number = int(list["IntDocNumber"])
            detailInfo = NPDeliveryCreatedDetailInfo(document_id=id_number,
                                                    ref=ref, cost_on_site=cost,
                                                    estimated_time_delivery=estimated_date,
                                                    recipient_worker=worker_name,
                                                    recipient_address=address_name,
                                                    for_order=order,
                                                    userCreated=user)
            detailInfo.save()
            user.np_last_choosed_delivery_place_id = sender_place.id
            user.save()
            url_to_redirect = None

            if redirect_url:
                url_to_redirect = settings.NOVA_POSHTA_PRINT_MARKING_URL_TEMPLATE.format(
                    ref=ref,
                    api_key=settings.NOVA_POSHTA_API_KEY
                )
            
            return url_to_redirect    
        else:
            errorsString = '\n'.join(f'• {error}' for error in data["errors"])
            if data['info']:
                errorsString += f'\n Info: {data["info"]}'
            if data['warnings']:
                warningsString = '\n'.join(f'• {warning}' for warning in data["warnings"])
                errorsString += f'\n Warnings: {warningsString}'
            raise Exception(errorsString)

    errors = {}
    if not inputForm.is_valid():
        errors['inputForm'] = inputForm.errors
    if not placeForm.is_valid():
        errors['placeForm'] = placeForm.errors
    message_parts = []
    for form_name, form_errors in errors.items():
        for field, field_errors in form_errors.items():
            message_parts.append(f'{field}: {", ".join(field_errors)}')
    raise Exception('Помилка валідації форми: ' + '; '.join(message_parts))


def create_np_document_for_order(request, order_id):
    print("create_np_document_for_order start")
    order = Order.objects.get(id=order_id)
    user = request.user
    for_place = order.place
    deliveryInfo = for_place.address_NP
    deliveryType = deliveryInfo.deliveryType
    sender_places = SenderNPPlaceInfo.objects.filter(for_user=request.user)
    title = f'Cформувати інтернет-документ для:\n- Замовлення №{order.id} \n- {for_place.name}, {for_place.city_ref.name}'
    inputForm = CreateNPParselForm(instance=order)
    placeForm = ClientFormForParcel(instance=for_place)

    inputForm.fields['sender_np_place'].queryset = sender_places
    placeForm.fields['worker_NP'].queryset = for_place.workers
    placeForm.fields['address_NP'].queryset = for_place.delivery_places

    try:
       sendplace = sender_places.get(id=user.np_last_choosed_delivery_place_id)
    except:
       sendplace = None
    inputForm.fields['sender_np_place'].initial = sendplace
    placeForm.fields['worker_NP'].initial = for_place.worker_NP
    placeForm.fields['address_NP'].initial = for_place.address_NP

    if request.method == 'POST':
        inputForm = CreateNPParselForm(request.POST, instance=order)
        placeForm = ClientFormForParcel(request.POST, instance=for_place)
        if inputForm.is_valid() and placeForm.is_valid():
            # Start the async process in a thread
            redirect_url = False
            if 'save_and_print' in request.POST:
                redirect_url = True
            try:
                url_to_redirect = threading_create_np_document_async(request, request.POST, order_id, redirect_url)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
            return JsonResponse({
                    "status": "success",
                    "message": "Накладна успішно створена",
                    "order_id": order_id,
                    "url_to_redirect": url_to_redirect
                })
        else:
            return JsonResponse({'status': 'error', 'message': "Помилка валідації форми"})

    # For GET requests, just render the form
    return render(request, 'supplies/nova_poshta/create_new_np_order_doc.html', {
        'inputForm': inputForm,
        'placeForm': placeForm,
        'order': order,
        'title': title
    })


def address_getCities(request):

    getListOfCitiesParams = {
        "apiKey": settings.NOVA_POSHTA_API_KEY,
        "modelName": "Address",
        "calledMethod": "getCities",
        "methodProperties": {
            "Page" : "0"
        }
    }

    npCities = NPCity.objects.all()
    npCities.delete()

    
    cityData = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(getListOfCitiesParams)).json()
    cityDataCount = cityData["data"]
    cities = []
    for city in cityDataCount:
        cityName = city["Description"]
        ref = city["Ref"]
        area = city["Area"]
        settlementType = city["SettlementType"]
        cityID = city["CityID"]
        settlementTypeDescription = city["SettlementTypeDescription"]
        areaDescription = city["AreaDescription"]
        newCity = NPCity(name=cityName, ref=ref, area=area, settlementType=settlementType, cityID=cityID, settlementTypeDescription=settlementTypeDescription, areaDescription=areaDescription)
        newCity.save()
    description = f'Міста Нової пошти були оновлені. Всього записів: {NPCity.objects.count()}'

    return render(request, "partials/any_response.html", {'description': description})


def search_city(request):
    search_text = request.POST.get('search')
    results = None
    if search_text != "":
        results = NPCity.objects.filter(name__istartswith=search_text.capitalize())
    context = {"results": results}
    return render(request, 'partials/search/search-city-results.html', context)

def search_street(request):

    search_text = request.POST.get('search')
    cityRef = request.POST.get('np-cityref')
    params = {
           "apiKey": settings.NOVA_POSHTA_API_KEY,
           "modelName": "Address",
           "calledMethod": "getStreet",
           "methodProperties": {
               "CityRef" : cityRef,
               "FindByString" : search_text.capitalize(),
               "Page" : "1",
               "Limit" : "25"
                  }
                }

    data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
    context = {"results": data["data"]}

    print(cityRef)

    return render(request, 'partials/search/search-streets-results.html', context)


def search_warehouse(request):
    search_text = request.POST.get('search')
    cityRef = request.POST.get('np-cityref')

    params = {
        "apiKey": settings.NOVA_POSHTA_API_KEY,
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityRef": cityRef,
            "Page": "1",
            "Limit": "25",
            "Language": "UA",
            # "WarehouseId": search_text.capitalize(),
            "FindByString": search_text.capitalize()
        }
    }
    data = requests.get(settings.NOVA_POSHTA_API_URL, data=json.dumps(params)).json()
    print("WAREHOUSES")
    print(data['data'])
    context = {"results": data["data"]}
    return render(request, 'partials/search/search-streets-results.html', context)


def choosed_city(request):
    cityName = request.POST.get('cityName')
    cityRef = request.POST.get('cityRef')
    cityType = request.POST.get('cityType')
    recipientType = request.POST.get('recipientType')
    if recipientType == 'Warehouse':
        renderPage = 'partials/search/choosed-city-and-warehouse.html'
    else:
        renderPage = 'partials/search/choosed-city.html'

    return render(request, renderPage, {'cityName': cityName, 'cityRef': cityRef, 'cityType': cityType})


def choosed_street(request):
    streetName = request.POST.get('streetName')
    streetType = request.POST.get('streetType')
    streetRef = request.POST.get('streetRef')

    recipientType = request.POST.get('recipientType')

    print("--------------------------------------")
    print(streetName)
    print(streetType)
    print(streetRef)
    print(recipientType)
    print("--------------------------------------")
    if recipientType == 'Warehouse':
        ifStreet = False
    else:
        ifStreet = True
    return render(request, 'partials/search/choosed-street.html', {'streetName': streetName, 'streetType': streetType, 'streetRef': streetRef, 'street': ifStreet})

def radioAddClientTONP(request):

    isCheked = request.POST.get('checkIfAddToNP')
    isShow = isCheked
    orgRefExistJson = request.POST.get('orgRefExist')
    orgExist = bool(orgRefExistJson == 'True')

    return render(request, 'partials/common/radioButtonsWorkerTypeGroup.html', {'cheked': isShow, 'orgRefExist': orgExist})

def delete_my_np_sender_place(request):
    del_sender_place_id = request.POST.get('del_sender_place_id')
    sup_info = SenderNPPlaceInfo.objects.get(id=del_sender_place_id)
    sup_info.delete()
    return HttpResponse(status=200)

def fetch_np_status(documents: List[Dict]) -> Dict:
    """
    Запит до API Нової Пошти TrackingDocument.getStatusDocuments.

    `documents` — список елементів виду ``{'DocumentNumber': '…', 'Phone': '…'}``
    (одне замовлення або багато накладних за один HTTP-запит).
    """
    params = {
        "apiKey": settings.NOVA_POSHTA_API_KEY,
        "modelName": "TrackingDocument",
        "calledMethod": "getStatusDocuments",
        "methodProperties": {
            "Documents": documents
        }
    }

    try:
        response = requests.post(settings.NOVA_POSHTA_API_URL, json=params)
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching NP status: {str(e)}")
        return {"data": []}


def _apply_np_tracking_row(obj: Dict, order: Order, user_who_created_document) -> None:
    """Один рядок відповіді getStatusDocuments → оновлення StatusNPParselFromDoucmentID."""
    number = obj["Number"]

    scheduledDeliveryDate = obj.get("ScheduledDeliveryDate", "")
    if scheduledDeliveryDate:
        scheduledDeliveryDate = datetime.datetime.strptime(scheduledDeliveryDate, '%d-%m-%Y %H:%M:%S').strftime('%d.%m.%Y %H:%M')

    dateCreated = datetime.datetime.strptime(obj["DateCreated"], '%d-%m-%Y %H:%M:%S').strftime('%d.%m.%Y %H:%M')

    dateScan = obj.get("DateScan", "")
    if dateScan:
        dateScan = datetime.datetime.strptime(dateScan, '%H:%M %d.%m.%Y').strftime('%d.%m.%Y %H:%M')

    actualDeliveryDate = obj.get("ActualDeliveryDate", "")
    if actualDeliveryDate:
        actualDeliveryDate = datetime.datetime.strptime(actualDeliveryDate, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')

    recipientDateTime = obj.get("RecipientDateTime", "")
    if recipientDateTime:
        recipientDateTime = datetime.datetime.strptime(recipientDateTime, '%d.%m.%Y %H:%M:%S').strftime('%d.%m.%Y %H:%M')

    status_data = {
        "status_code": obj["StatusCode"],
        "status_desc": obj["Status"],
        "docNumber": number,
        "for_order_id": order.id,
        "counterpartyRecipientDescription": obj["CounterpartyRecipientDescription"],
        "documentWeight": obj["DocumentWeight"],
        "factualWeight": obj["FactualWeight"],
        "payerType": obj["PayerType"],
        "seatsAmount": obj["SeatsAmount"],
        "phoneRecipient": obj["PhoneRecipient"],
        "scheduledDeliveryDate": scheduledDeliveryDate,
        "documentCost": obj["DocumentCost"],
        "paymentMethod": obj["PaymentMethod"],
        "warehouseSender": f'{user_who_created_document.first_name}, {user_who_created_document.last_name}, {obj["WarehouseSender"]}',
        "dateCreated": dateCreated,
        "dateScan": dateScan,
        "actualDeliveryDate": actualDeliveryDate,
        "recipientDateTime": recipientDateTime,
        "recipientAddress": obj["RecipientAddress"],
        "recipientFullNameEW": obj["RecipientFullNameEW"],
        "cargoDescriptionString": obj["CargoDescriptionString"],
        "announcedPrice": obj["AnnouncedPrice"]
    }

    try:
        StatusNPParselFromDoucmentID.objects.update_or_create(
            docNumber=number,
            for_order_id=order.id,
            defaults=status_data
        )
    except Exception as e:
        logger.error(f"Error updating status parcel model for order {order.id}, doc {number}: {str(e)}")


def process_status_data(data: Dict, order: Order, userCreatedList: Dict) -> None:
    """Process status data and update database"""
    if not data.get("data"):
        return

    for obj in data["data"]:
        number = obj["Number"]
        user_who_created_document = userCreatedList[number]
        _apply_np_tracking_row(obj, order, user_who_created_document)


def process_status_data_multi(
    data: Dict,
    order_by_document_key: Dict[str, Order],
    user_created_by_document_key: Dict[str, Any],
) -> None:
    """
    Те саме, що process_status_data, але для відповіді, де накладні з різних замовлень.
    Ключі мап — ``str(DocumentNumber)``.
    """
    if not data.get("data"):
        return

    for obj in data["data"]:
        number = obj["Number"]
        sk = str(number)
        order = order_by_document_key.get(sk) or order_by_document_key.get(number)
        if order is None:
            logger.warning("NP batch: немає прив’язки замовлення для накладної %s", number)
            continue
        user_who = user_created_by_document_key.get(sk) or user_created_by_document_key.get(number)
        if user_who is None:
            logger.warning("NP batch: немає userCreated для накладної %s", number)
            continue
        _apply_np_tracking_row(obj, order, user_who)


NP_GET_STATUS_DOCUMENTS_CHUNK_SIZE = 100


def _np_tracking_refresh_cache_key(order_id: int) -> str:
    return f'np_order_tracking_refresh:{order_id}'


def np_tracking_refresh_on_cooldown(order_id: int) -> bool:
    """True, якщо для замовлення нещодавно вже був запит до API НП (lazy HTMX)."""
    return cache.get(_np_tracking_refresh_cache_key(order_id)) is not None


def mark_np_tracking_refreshed(order_id: int) -> None:
    timeout = getattr(settings, 'NP_ORDER_TRACKING_REFRESH_COOLDOWN_SECONDS', 600)
    cache.set(_np_tracking_refresh_cache_key(order_id), 1, timeout=timeout)


def order_needs_np_tracking_api_refresh(order: Order) -> bool:
    """False, якщо вже «фінальний» статус — повторний запит до API не робимо."""
    has_status, status_code = get_order_status(order)
    if has_status and status_code in (2, 9):
        return False
    return True


def _collect_documents_for_orders_batch(
    orders: List[Order],
) -> Tuple[List[Dict], Dict[str, Order], Dict[str, Any]]:
    """
    Зібрати унікальні DocumentNumber + мапи для батч-оновлення.
    Дубль номера накладної (різні замовлення) — береться перше входження.
    """
    documents_out: List[Dict] = []
    order_by_doc: Dict[str, Order] = {}
    user_by_doc: Dict[str, Any] = {}
    seen: set[str] = set()

    for order in orders:
        if not order_needs_np_tracking_api_refresh(order):
            continue
        documents, user_created_list = get_order_documents(order)
        if not documents:
            continue
        for doc in documents:
            raw_num = doc.get('DocumentNumber')
            if raw_num is None:
                continue
            sk = str(raw_num)
            if sk in seen:
                continue
            seen.add(sk)
            documents_out.append(doc)
            order_by_doc[sk] = order
            user_who = user_created_list.get(raw_num)
            if user_who is None:
                user_who = user_created_list.get(sk)
            user_by_doc[sk] = user_who

    return documents_out, order_by_doc, user_by_doc


def refresh_np_tracking_for_orders_batch(orders: Iterable[Order]) -> None:
    """
    Один або кілька викликів ``fetch_np_status`` для набору замовлень (чанки по
    ``NP_GET_STATUS_DOCUMENTS_CHUNK_SIZE``), потім оновлення записів у БД.
    """
    orders_list = list(orders)
    documents, order_by_doc, user_by_doc = _collect_documents_for_orders_batch(orders_list)
    if not documents:
        return

    for start in range(0, len(documents), NP_GET_STATUS_DOCUMENTS_CHUNK_SIZE):
        chunk = documents[start:start + NP_GET_STATUS_DOCUMENTS_CHUNK_SIZE]
        payload = fetch_np_status(chunk)
        process_status_data_multi(payload, order_by_doc, user_by_doc)

def get_order_status(order: Order) -> Tuple[bool, int]:
    """Get order status"""
    if order.statusnpparselfromdoucmentid_set.exists():
        statusCode = int(order.statusnpparselfromdoucmentid_set.first().status_code)
        return True, statusCode
    return False, 0

def get_order_documents(order: Order) -> Tuple[List[Dict], Dict]:
    """Get order documents"""
    documentsIdList = order.npdeliverycreateddetailinfo_set.all()
    documents = []
    userCreatedList = {}
    
    for docu in documentsIdList:
        documents.append({
            'DocumentNumber': docu.document_id,
            'Phone': docu.userCreated.mobNumber
        })
        userCreatedList[docu.document_id] = docu.userCreated
    
    return documents, userCreatedList

def get_parsels_status_data(order: Order) -> QuerySet:
    """Get parsels status data"""
    return order.statusnpparselfromdoucmentid_set.all()

def get_np_delivery_details(
    order: Order,
    *,
    respect_refresh_cooldown: bool = False,
) -> Tuple[QuerySet, bool]:
    """
    Оновити статуси НП у БД (за потреби) і повернути збережені рядки.

    ``respect_refresh_cooldown=True`` — для lazy HTMX: не викликати API НП частіше
    ніж ``NP_ORDER_TRACKING_REFRESH_COOLDOWN_SECONDS`` (за замовчуванням 10 хв)
    на одне замовлення, незалежно від користувача.
    """
    has_status, status_code = get_order_status(order)
    noMoreUpdate = False

    if has_status:
        noMoreUpdate = status_code == 2 or status_code == 9

    should_call_api = not noMoreUpdate
    if should_call_api and respect_refresh_cooldown and np_tracking_refresh_on_cooldown(order.id):
        should_call_api = False
        logger.debug('NP tracking API skipped (cooldown) for order %s', order.id)

    if should_call_api:
        documents, userCreatedList = get_order_documents(order)
        data = fetch_np_status(documents)
        process_status_data(data, order, userCreatedList)
        if respect_refresh_cooldown:
            mark_np_tracking_refreshed(order.id)

    parsels_status_data = get_parsels_status_data(order)
    return parsels_status_data, noMoreUpdate

def complete_all_orders_with_np_status_code():
    """Process orders sequentially"""
    # Create a handler based on environment
    if settings.DEBUG:
        # In development, use a file handler
        handler = logging.FileHandler('np_status_updates.log')
        handler.setLevel(logging.INFO)
        
        # Create a formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(handler)
    
    logger.info("Starting evening task execution")
    
    try:
        # Get orders that need processing
        orders = Order.objects.filter(statusnpparselfromdoucmentid__isnull=False, isComplete=False).distinct()
        logger.info(f"Found {orders.count()} orders with status code greater than 3 to process")
        
        # Create a list to store order details for the final log
        order_details_list = []
        
        # Process each order sequentially
        for order in orders:
            try:
                logger.info(f"Processing order ID: {order.id}")
                get_np_delivery_details(order)
                
                delivery_info = order.npdeliverycreateddetailinfo_set.first()
                user_sent = delivery_info.userCreated if delivery_info else None
                
                # Get the status code for this order
                status_parcel = order.statusnpparselfromdoucmentid_set.first()
                status_code = status_parcel.status_code if status_parcel else "No status"
                
                # Log detailed order information
                logger.info(f"Order {order.id} details:")
                logger.info(f"  - User sent: {user_sent}")
                logger.info(f"  - Status code: {status_code}")
                logger.info(f"  - Order info: {order}")
                
                # Add order details to the list for the final log
                order_details_list.append({
                    "order_id": order.id,
                    "user_sent": str(user_sent),
                    "status_code": status_code,
                    "order_info": str(order)
                })
                if status_parcel and status_code != "No status":
                    code_int = int(status_code)
                    if code_int == 2:
                        try:
                            delete_np_parsel_document(status_parcel)
                            logger.info(
                                "Deleted NP document for order %s (status code 2), parcel id %s",
                                order.id,
                                status_parcel.pk,
                            )
                        except Exception as e:
                            logger.error(
                                "Failed to delete NP document for order %s (status code 2): %s",
                                order.id,
                                e,
                            )
                    elif code_int > 3:
                        update_order_status_core(order.id, user_sent)
                        logger.info(f"Successfully updated status for order {order.id}")
                    else:
                        logger.info(
                            "No action for order %s: status code is %s (not 2 and not > 3)",
                            order.id,
                            status_code,
                        )
                else:
                    logger.info(f"No status code for order {order.id}")
                
                
                # Add a small delay between orders to prevent overwhelming the database
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
            
            logger.info("="*100)
        
        current_time = timezone.localtime(timezone.now())
        logger.info(f"Evening task completed at {current_time}")
        logger.info("="*100)
        
        # Format the order details list for the final log
        order_details_log = "Order Details:\n"
        for detail in order_details_list:
            order_details_log += f"Order {detail['order_id']}:\n"
            order_details_log += f"  - User sent: {detail['user_sent']}\n"
            order_details_log += f"  - Status code: {detail['status_code']}\n"
            order_details_log += f"  - Order info: {detail['order_info']}\n"
            order_details_log += "  " + "="*50 + "\n"
        
        logger.info(
            "NP status update task completed at %s. Processed %s orders.\n%s",
            current_time,
            orders.count(),
            order_details_log,
        )

    except Exception as e:
        logger.error(f"Error in complete_all_orders_with_np_status_code: {str(e)}")
    finally:
        # Remove the handler to avoid duplicate logs in future runs
        if settings.DEBUG and 'handler' in locals():
            logger.removeHandler(handler)

def np_delivery_detail_info_for_order(request, order_id):
    """
    View function to handle NP delivery detail info requests
    """
    order = Order.objects.get(id=order_id)
    parsels_status_data, noMoreUpdate = get_np_delivery_details(
        order,
        respect_refresh_cooldown=True,
    )
    
    response = render(request, 'partials/delivery/np_delivery_info_in_list_of_orders.html',
                     {'parsels_status_data': parsels_status_data})
    trigger_client_event(response, f'np_create_ID_button_subscribe{order_id}', {})
    
    return response


def _user_can_np_uncompleted_modal(request):
    return request.user.is_authenticated and (
        getattr(request.user, 'is_staff', False)
        or request.user.groups.filter(name='empl').exists()
    )


@login_required(login_url='login')
def orders_np_uncompleted_modal_body(request):
    """
    Тіло модалки «незавершені НП».

    Без ``?refresh=1``: лише дані з БД + прапорець ``refresh_pending`` (клієнт показує
    лоадінг згори й одразу таблицю).

    З ``?refresh=1``: батч ``refresh_np_tracking_for_orders_batch``, потім та сама таблиця
    з оновленими статусами (без смуги очікування).
    """
    if not _user_can_np_uncompleted_modal(request):
        return HttpResponse(
            '<p class="text-danger small mb-0">Немає доступу.</p>',
            status=403,
        )

    orders_list = list(
        queryset_orders_with_uncompleted_np_tracking().select_related(
            'place',
            'place__city_ref',
        )
    )

    do_refresh = request.GET.get('refresh') in ('1', 'true', 'yes')
    if do_refresh:
        try:
            refresh_np_tracking_for_orders_batch(orders_list)
        except Exception:
            logger.exception('orders_np_uncompleted_modal_body: batch NP refresh failed')

    rows = []
    for order in orders_list:
        parsels_status_data = get_parsels_status_data(order)
        has_status, status_code = get_order_status(order)
        no_more_update = bool(has_status and status_code in (2, 9))
        rows.append(
            {
                'order': order,
                'parsels': parsels_status_data,
                'no_more_update': no_more_update,
            }
        )

    refresh_pending = not do_refresh

    return render(
        request,
        'partials/np/np_uncompleted_orders_modal_body.html',
        {
            'rows': rows,
            'refresh_pending': refresh_pending,
        },
    )


def np_create_ID_button_subscribe(request, order_id):
    print("np_create_ID_button_subscribe")
    order = _order_singleton_for_card(order_id)
    if order is None:
        return HttpResponse(status=404)
    return render(request, 'partials/delivery/np_create_ID_button.html', {'order': order})


def orderCellUpdateNPStatus(request, order_id):
    order = _order_singleton_for_card(order_id)
    if order is None:
        return HttpResponse(status=404)
    # Check if user agent is mobile
    if request.user_agent.is_mobile:
        template = 'supplies_mobile/order_cell.html'
    else:
        template = 'partials/orders/order_preview_cel.html'
    return render(request, template, {'order': order})