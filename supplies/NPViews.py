from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse, JsonResponse
from .NPModels import *
from .views import update_order_status_core
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
from typing import List, Dict, Tuple
import time
from django.db.models import QuerySet
from django.utils import timezone
import ssl

logger = logging.getLogger(__name__)


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
    return render(request, 'supplies/nova_poshta/nova_poshta_registers.html', {'registers': registers})



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
        sender_ref = settings.NOVA_POSHTA_SENDER_DMDX_REF

        volumeGeneral = float(width / 100) * float(length / 100) * float(height / 100)

        sender_place = inputForm.cleaned_data['sender_np_place']
        recipient_address = placeForm.cleaned_data['address_NP']
        recipient_worker = placeForm.cleaned_data['worker_NP']

        weight_input_field_list = data.getlist('weight_input_field') or []
        width_input_field_list = data.getlist('width_input_field') or []
        length_input_field_list = data.getlist('length_input_field') or []
        height_input_field_list = data.getlist('height_input_field') or []

        options_seat_list = [
            {
                "volumetricVolume": str(volumeGeneral),
                "volumetricWidth": width,
                "volumetricLength": length,
                "volumetricHeight": height,
                "weight": str(weight)
            }
        ]

        for i in range(len(weight_input_field_list)):
            weight = weight_input_field_list[i]
            width = width_input_field_list[i]
            length = length_input_field_list[i]
            height = height_input_field_list[i]

            volumetric_volume = float(width) / 100 * float(length) / 100 * float(height) / 100

            options_seat = {
                "volumetricVolume": str(volumetric_volume),
                "volumetricWidth": width,
                "volumetricLength": length,
                "volumetricHeight": height,
                "weight": str(weight)
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
                "CargoType": "Parcel",
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
        print("response from NP: ",data)
        
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
            raise Exception(errorsString)
            

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
    """Make request to Nova Poshta API"""
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

def process_status_data(data: Dict, order: Order, userCreatedList: Dict) -> None:
    """Process status data and update database"""
    if not data.get("data"):
        return

    for obj in data["data"]:
        number = obj["Number"]
        user_who_created_document = userCreatedList[number]

        # Format dates
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

        # Prepare status data
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

        # Update or create status model
        try:
            status_parsel_model, created = StatusNPParselFromDoucmentID.objects.update_or_create(
                docNumber=number,
                for_order_id=order.id,
                defaults=status_data
            )
        except Exception as e:
            logger.error(f"Error updating status parcel model for order {order.id}, doc {number}: {str(e)}")

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

def get_np_delivery_details(order: Order) -> Tuple[QuerySet, bool]:
    """Get NP delivery details sequentially"""
    print("Call for order: ", order.id)
    has_status, status_code = get_order_status(order)
    noMoreUpdate = False

    if has_status:
        noMoreUpdate = status_code == 2 or status_code == 9

    if not noMoreUpdate:
        documents, userCreatedList = get_order_documents(order)
        data = fetch_np_status(documents)
        process_status_data(data, order, userCreatedList)

    parsels_status_data = get_parsels_status_data(order)
    return parsels_status_data, noMoreUpdate

def complete_all_orders_with_np_status_code():
    """Process orders sequentially"""
    logger.info("Starting evening task execution")
    
    try:
        # Get orders that need processing
        orders = Order.objects.filter(statusnpparselfromdoucmentid__status_code__gt="3", isComplete=False).distinct()
        logger.info(f"Found {orders.count()} orders with status code greater than 3 to process")
        
        # Process each order sequentially
        for order in orders:
            try:
                logger.info(f"Processing order ID: {order.id}")
                get_np_delivery_details(order)
                
                delivery_info = order.npdeliverycreateddetailinfo_set.first()
                user_sent = delivery_info.userCreated if delivery_info else None
                logger.info(f"Order {order.id} delivery info found - User: {user_sent}")
                
                update_order_status_core(order.id, user_sent)
                logger.info(f"Successfully updated status for order {order.id}")
                
                # Add a small delay between orders to prevent overwhelming the database
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
            
            logger.info("="*100)
        
        current_time = timezone.localtime(timezone.now())
        logger.info(f"Evening task completed at {current_time}")
        logger.info("="*100)
        
    except Exception as e:
        logger.error(f"Error in complete_all_orders_with_np_status_code: {str(e)}")

def np_delivery_detail_info_for_order(request, order_id):
    """
    View function to handle NP delivery detail info requests
    """
    order = Order.objects.get(id=order_id)
    parsels_status_data, noMoreUpdate = get_np_delivery_details(order)
    
    response = render(request, 'partials/delivery/np_delivery_info_in_list_of_orders.html',
                     {'parsels_status_data': parsels_status_data})
    trigger_client_event(response, f'np_create_ID_button_subscribe{order_id}', {})
    
    return response


def np_create_ID_button_subscribe(request, order_id):
    print("np_create_ID_button_subscribe")
    order = Order.objects.get(id=order_id)
    return render(request, 'partials/delivery/np_create_ID_button.html', {'order': order})


def orderCellUpdateNPStatus(request, order_id):
    order = Order.objects.get(id=order_id)
    # Check if user agent is mobile
    if request.user_agent.is_mobile:
        template = 'supplies_mobile/order_cell.html'
    else:
        template = 'partials/orders/order_preview_cel.html'
    return render(request, template, {'order': order})