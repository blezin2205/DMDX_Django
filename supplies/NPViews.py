import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse

from .decorators import unauthenticated_user, allowed_users
from .models import *
from .NPModels import *
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
        results = NPCity.objects.filter(name__istartswith=search_text)
    context = {"results": results}
    return render(request, 'partials/search-city-results.html', context)

def search_street(request):

    search_text = request.POST.get('search')
    cityRef = request.POST.get('np-cityref')


    # params = {
    #       "apiKey": "99f738524ca3320ece4b43b10f4181b1",
    #       "modelName": "Address",
    #       "calledMethod": "searchSettlementStreets",
    #       "methodProperties": {
    #           "StreetName" : search_text,
    #           "SettlementRef" : cityRef,
    #           "Limit" : "50"
    #             }
    #           }

    params = {
           "apiKey": "99f738524ca3320ece4b43b10f4181b1",
           "modelName": "Address",
           "calledMethod": "getStreet",
           "methodProperties": {
               "CityRef" : cityRef,
               "FindByString" : search_text,
               "Page" : "1",
               "Limit" : ""
                  }
                }

    data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(params)).json()
    context = {"results": data["data"]}

    print(cityRef)

    return render(request, 'partials/search-streets-results.html', context)

def choosed_city(request):
    cityName = request.POST.get('cityName')
    cityRef = request.POST.get('cityRef')
    print(cityRef)
    return render(request, 'partials/choosed-city.html', {'cityName': cityName, 'cityRef': cityRef})

def choosed_street(request):
    streetName = request.POST.get('streetName')
    streetType = request.POST.get('streetType')
    streetRef = request.POST.get('streetRef')
    return render(request, 'partials/choosed-street.html', {'streetName': streetName, 'streetType': streetType, 'streetRef': streetRef})

def radioAddClientTONP(request):

    isCheked = request.POST.get('checkIfAddToNP')
    isShow = isCheked
    orgRefExistJson = request.POST.get('orgRefExist')
    orgExist = bool(orgRefExistJson == 'True')

    return render(request, 'partials/radioButtonsWorkerTypeGroup.html', {'cheked': isShow, 'orgRefExist': orgExist})