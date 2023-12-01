from celery import shared_task
from celery_progress.backend import ProgressRecorder

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
from django.db.models import *
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
from django.core.mail import send_mail

import os
from xlsxwriter.workbook import Workbook
from django_htmx.http import trigger_client_event
from django.contrib import messages
import requests
import pandas
import csv
import pymsteams
import plotly.express as px
from django.db.models import Sum, F

from time import sleep

@shared_task(bind=True)
def go_to_sleep(self, duration):
    progress_recorder = ProgressRecorder(self)
    for i in range(5):
        sleep(duration)
        progress_recorder.set_progress(i + 1, 5, f'On iteration {i}')
    return HttpResponse("DONE!")

@shared_task(bind=True)
def makeDataUpload(self, string_data):
    result_array = string_data.split()
    for item in result_array:
        arr_item = item.split(',')
        if len(arr_item) == 1:
            barcode_str = arr_item[0]
            smn = barcode_str[32:-6]
            smn = smn[-8:]
            lot = barcode_str[18:-25]
            date_expired = barcode_str[23:-17]
            date_expired = date_expired[-6:]
            create_supply_objects(item, smn, lot, date_expired)
        if len(arr_item) == 3:
            smn = arr_item[0]
            lot = arr_item[1]
            date_expired = arr_item[2]
            create_supply_objects(item, smn, lot, date_expired, True)


def create_supply_objects(barcode, smn, lot, date_expired, search_by_ref=False):

    try:
        date_expired_date = datetime.datetime.strptime(date_expired, '%y%m%d')
        if search_by_ref:
            gen_sup = GeneralSupply.objects.get(ref=smn)
        else:
            gen_sup = GeneralSupply.objects.get(SMN_code=smn)

        try:
            sup = Supply.objects.get(general_supply=gen_sup,
                                     supplyLot=lot,
                                     expiredDate=date_expired_date)
            sup.count += 1
        except:
            sup = Supply(name=gen_sup.name,
                         general_supply=gen_sup,
                         category=gen_sup.category,
                         ref=gen_sup.ref,
                         supplyLot=lot,
                         count=1,
                         expiredDate=date_expired_date)

        try:
            sup_delivery = DeliverySupplyInCart.objects.get(general_supply=gen_sup, supply=sup)
            sup_delivery.count += 1
        except:
            sup_delivery = DeliverySupplyInCart(
                barcode=barcode,
                supplyLot=lot,
                count=1,
                expiredDate=date_expired)

        sup_delivery.general_supply = gen_sup
        sup_delivery.isRecognized = True
        sup_delivery.supply = sup
        sup.save()
        sup_delivery.save()

    except:
        try:
            sup_delivery = DeliverySupplyInCart.objects.get(barcode=barcode)
            sup_delivery.count += 1
        except:
            sup_delivery = DeliverySupplyInCart(
                barcode=barcode,
                supplyLot=lot,
                count=1,
                expiredDate=date_expired)
        sup_delivery.save()


