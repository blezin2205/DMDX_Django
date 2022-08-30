
from django.shortcuts import render, get_object_or_404, redirect

from .NPModels import *
from .forms import *
import json
from django.contrib import messages
import requests


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

    data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(param)).json()
    return render(request, "supplies/http_response.html", {'data': data["data"]})

def create_np_document_for_order(request, order_id):

    order = Order.objects.get(id=order_id)
    for_place = order.place
    deliveryInfo = for_place.address_NP
    deliveryType = deliveryInfo.deliveryType
    inputForm = CreateNPParselForm(instance=order)

    if request.method == 'POST':
        inputForm = CreateNPParselForm(request.POST, instance=order)
        print(inputForm.is_valid())
        if inputForm.is_valid():
            dateSend = inputForm.cleaned_data['dateDelivery'].strftime('%d.%m.%Y')
            payment_money_type = inputForm.cleaned_data['payment_money_type']
            payment_user_type = inputForm.cleaned_data['payment_user_type']
            width = inputForm.cleaned_data['width']
            length = inputForm.cleaned_data['length']
            height = inputForm.cleaned_data['height']
            weight = inputForm.cleaned_data['weight']
            seatsAmount = inputForm.cleaned_data['seatsAmount']
            description = inputForm.cleaned_data['description']
            cost = inputForm.cleaned_data['cost']

            volumeGeneral = float(width / 100) * float(length / 100) * float(height / 100)

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
                    "ServiceType": f'Warehouse{deliveryType}',
                    "SeatsAmount": str(seatsAmount),
                    "Description": description,
                    "Cost": str(cost),
                    "CitySender": "8d5a980d-391c-11dd-90d9-001a92567626",
                    "Sender": "3b0e7317-2a6b-11eb-8513-b88303659df5",
                    "SenderAddress": "01ae25f6-e1c2-11e3-8c4a-0050568002cf",
                    "ContactSender": "9993e149-93e5-11ec-b0fd-b88303659df5",
                    "SendersPhone": "380992438918",
                    "CityRecipient": deliveryInfo.city_ref_NP,
                    "Recipient": for_place.worker_NP.ref_counterparty_NP,
                    "RecipientAddress": deliveryInfo.address_ref_NP,
                    "ContactRecipient": for_place.worker_NP.ref_NP,
                    "RecipientsPhone": for_place.worker_NP.telNumber
                }
            }
            data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
            print(data)

            if data["success"] is True and data["data"][0] is not None:
                list = data["data"][0]
                ref = list["Ref"]
                cost = list["CostOnSite"]
                estimated_date = list["EstimatedDeliveryDate"]
                id_number = int(list["IntDocNumber"])
                detailInfo = NPDeliveryCreatedDetailInfo(document_id=id_number, ref=ref, cost_on_site=cost, estimated_time_delivery=estimated_date, for_order=order)
                detailInfo.save()
                print(list)
                url = f'https://my.novaposhta.ua/orders/printMarking85x85/orders[]/{ref}/type/pdf8/apiKey/99f738524ca3320ece4b43b10f4181b1'
                return redirect(url)

            elif data["success"] is False and data["errors"] is not None:
                errors = data["errors"]
                print(errors)
                for error in errors:
                    messages.info(request, error)
                return render(request, 'supplies/create_np_order_doucment.html', {'inputForm': inputForm})

    return render(request, 'supplies/create_np_order_doucment.html', {'inputForm': inputForm})


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
               "Limit" : ""
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
            "Limit": "50",
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
    documentsIdList = Order.objects.get(id=order_id).npdeliverycreateddetailinfo_set.all()
    documents = []

    for docu in documentsIdList:
        documents.append({'DocumentNumber': docu.document_id})

    objList = []


    params = {
                  "apiKey": "99f738524ca3320ece4b43b10f4181b1",
                  "modelName": "TrackingDocument",
                  "calledMethod": "getStatusDocuments",
                  "methodProperties": {
               "Documents" : documents
                  }
              }
    data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
    print(data)
    if data["data"]:

        for obj in data["data"]:
            number = obj["Number"]
            status_code = obj["StatusCode"]
            status = obj["Status"]
            objList.append(StatusNPParselFromDoucmentID(status_code=status_code, status_desc=status, docNumber=number))

    return render(request, 'partials/np_delivery_info_in_list_of_orders.html', {'objList': objList})

