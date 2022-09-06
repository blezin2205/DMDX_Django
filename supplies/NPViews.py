
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from .NPModels import *
from .forms import *
import json
from django.contrib import messages
import requests
from django_htmx.http import trigger_client_event


def httpRequest(request):

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
    user = request.user
    data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(param)).json()
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
    return render(request, 'supplies/nova_poshta_registers.html', {'registers': registers})



def get_register_for_orders(request):
    cheked = False
    if request.method == 'POST':
        selected_orders = request.POST.getlist('flexCheckDefault')
        cheked = len(selected_orders) > 0
    return render(request, 'partials/register_print_orders_chekbox_buttons.html', {'cheked': cheked})


def create_np_document_for_order(request, order_id):

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
        print(inputForm.is_valid())
        if inputForm.is_valid() and placeForm.is_valid():
            dateSend = inputForm.cleaned_data['dateDelivery'].strftime('%d.%m.%Y')
            sender_np_place = inputForm.cleaned_data['sender_np_place']
            payment_money_type = inputForm.cleaned_data['payment_money_type']
            payment_user_type = inputForm.cleaned_data['payment_user_type']
            width = inputForm.cleaned_data['width']
            length = inputForm.cleaned_data['length']
            height = inputForm.cleaned_data['height']
            weight = inputForm.cleaned_data['weight']
            seatsAmount = inputForm.cleaned_data['seatsAmount']
            description = inputForm.cleaned_data['description']
            cost = inputForm.cleaned_data['cost']
            sender_ref = "3b0e7317-2a6b-11eb-8513-b88303659df5"

            volumeGeneral = float(width / 100) * float(length / 100) * float(height / 100)

            sender_place = inputForm.cleaned_data['sender_np_place']
            recipient_address = placeForm.cleaned_data['address_NP']
            recipient_worker = placeForm.cleaned_data['worker_NP']


            params = {
                "apiKey": "99f738524ca3320ece4b43b10f4181b1",
                "modelName": "InternetDocument",
                "calledMethod": "save",
                "methodProperties": {
                    "PayerType": payment_user_type,
                    "PaymentMethod": payment_money_type,
                    "DateTime": dateSend,
                    "CargoType": "Parcel",
                    "VolumeGeneral": str(volumeGeneral),
                    "Weight": str(weight),
                    "ServiceType": f'{sender_place.deliveryType}{deliveryType}',
                    "SeatsAmount": str(seatsAmount),
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
                    "RecipientsPhone": recipient_worker.telNumber
                }
            }
            data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
            print(data)
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
                detailInfo = NPDeliveryCreatedDetailInfo(document_id=id_number, ref=ref, cost_on_site=cost, estimated_time_delivery=estimated_date, recipient_worker=worker_name, recipient_address=address_name, for_order=order)
                detailInfo.save()
                user.np_last_choosed_delivery_place_id = sender_place.id
                user.save()
                print(list)
                if 'save_and_print' in request.POST:
                    url = f'https://my.novaposhta.ua/orders/printMarking85x85/orders[]/{ref}/type/pdf8/apiKey/99f738524ca3320ece4b43b10f4181b1'
                    return redirect(url)
                elif 'save_and_add' in request.POST:
                    messages.info(request, "Add Succesfully")
                    return redirect(f'/create-np_document-for-order/{order_id}')
                else:
                    next = request.POST.get('next')
                    return redirect('/orders')

            elif data["success"] is False and data["errors"] is not None:
                errors = data["errors"]
                print(errors)
                for error in errors:
                    messages.info(request, error)
                return render(request, 'supplies/create_new_np_order_doc.html', {'inputForm': inputForm})

    return render(request, 'supplies/create_new_np_order_doc.html', {'inputForm': inputForm, 'placeForm': placeForm, 'title': title})


def address_getCities(request):

    getListOfCitiesParams = {
        "apiKey": "99f738524ca3320ece4b43b10f4181b1",
        "modelName": "Address",
        "calledMethod": "getCities",
        "methodProperties": {
            "Page" : "0"
        }
    }

    npCities = NPCity.objects.all()
    npCities.delete()

    cityData = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(getListOfCitiesParams)).json()
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

    return render(request, "supplies/http_response.html", {'data': "Updated"})


def search_city(request):
    search_text = request.POST.get('search')
    results = None
    if search_text != "":
        results = NPCity.objects.filter(name__istartswith=search_text.capitalize())
    context = {"results": results}
    return render(request, 'partials/search-city-results.html', context)

def search_street(request):

    search_text = request.POST.get('search')
    cityRef = request.POST.get('np-cityref')
    params = {
           "apiKey": "99f738524ca3320ece4b43b10f4181b1",
           "modelName": "Address",
           "calledMethod": "getStreet",
           "methodProperties": {
               "CityRef" : cityRef,
               "FindByString" : search_text.capitalize(),
               "Page" : "1",
               "Limit" : "25"
                  }
                }

    data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
    context = {"results": data["data"]}

    print(cityRef)

    return render(request, 'partials/search-streets-results.html', context)


def search_warehouse(request):
    search_text = request.POST.get('search')
    cityRef = request.POST.get('np-cityref')

    params = {
        "apiKey": "99f738524ca3320ece4b43b10f4181b1",
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityRef": cityRef,
            "Page": "1",
            "Limit": "25",
            "Language": "UA",
            "WarehouseId": search_text.capitalize()
        }
    }
    data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
    context = {"results": data["data"]}
    return render(request, 'partials/search-streets-results.html', context)


def choosed_city(request):
    cityName = request.POST.get('cityName')
    cityRef = request.POST.get('cityRef')
    cityType = request.POST.get('cityType')
    recipientType = request.POST.get('recipientType')
    if recipientType == 'Warehouse':
        renderPage = 'partials/choosed-city-and-warehouse.html'
    else:
        renderPage = 'partials/choosed-city.html'

    return render(request, renderPage, {'cityName': cityName, 'cityRef': cityRef, 'cityType': cityType})


def choosed_street(request):
    streetName = request.POST.get('streetName')
    streetType = request.POST.get('streetType')
    streetRef = request.POST.get('streetRef')

    recipientType = request.POST.get('recipientType')
    if recipientType == 'Warehouse':
        ifStreet = False
    else:
        ifStreet = True
    return render(request, 'partials/choosed-street.html', {'streetName': streetName, 'streetType': streetType, 'streetRef': streetRef, 'street': ifStreet})

def radioAddClientTONP(request):

    isCheked = request.POST.get('checkIfAddToNP')
    isShow = isCheked
    orgRefExistJson = request.POST.get('orgRefExist')
    orgExist = bool(orgRefExistJson == 'True')

    return render(request, 'partials/radioButtonsWorkerTypeGroup.html', {'cheked': isShow, 'orgRefExist': orgExist})



def np_delivery_detail_info_for_order(request, order_id):

    order = Order.objects.get(id=order_id)
    userCreated = order.userCreated
    documentsIdList = order.npdeliverycreateddetailinfo_set.all()
    documents = []

    noMoreUpdate = False

    if order.statusnpparselfromdoucmentid_set.exists():
        statusCode = int(order.statusnpparselfromdoucmentid_set.first().status_code)
        print(statusCode)
        noMoreUpdate = statusCode == 2 or statusCode == 9

    if not noMoreUpdate:
        for docu in documentsIdList:
            documents.append({'DocumentNumber': docu.document_id,
                              'Phone': userCreated.mobNumber})

        objList = []

        params = {
            "apiKey": "99f738524ca3320ece4b43b10f4181b1",
            "modelName": "TrackingDocument",
            "calledMethod": "getStatusDocuments",
            "methodProperties": {
                "Documents": documents
            }
        }
        data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
        print(data)
        status_parsel_code = 1
        if data["data"]:
            for obj in data["data"]:
                number = obj["Number"]
                status_code = obj["StatusCode"]
                status = obj["Status"]
                status_parsel_code = int(status_code)
                try:
                    status_parsel_model = Order.objects.get(id=order_id).statusnpparselfromdoucmentid_set.get(
                        docNumber=number, for_order_id=order_id)
                    status_parsel_model.status_desc = status
                    status_parsel_model.status_code = status_code
                    status_parsel_model.docNumber = number
                    status_parsel_model.save()
                except:
                    status_parsel_model = StatusNPParselFromDoucmentID(status_code=status_code, status_desc=status,
                                                                       docNumber=number, for_order_id=order_id)
                    status_parsel_model.save()

        parsels_status_data = Order.objects.get(id=order_id).statusnpparselfromdoucmentid_set.all()
        response = render(request, 'partials/np_delivery_info_in_list_of_orders.html',
                          {'parsels_status_data': parsels_status_data})
        trigger_client_event(response, f'np_create_ID_button_subscribe{order_id}', {})

    else:
        parsels_status_data = Order.objects.get(id=order_id).statusnpparselfromdoucmentid_set.all()
        response = render(request, 'partials/np_delivery_info_in_list_of_orders.html',
                          {'parsels_status_data': parsels_status_data})
        trigger_client_event(response, f'np_create_ID_button_subscribe{order_id}', {})


    return response


def np_create_ID_button_subscribe(request, order_id):
    print("np_create_ID_button_subscribe")
    order = Order.objects.get(id=order_id)
    return render(request, 'partials/np_create_ID_button.html', {'order': order})


