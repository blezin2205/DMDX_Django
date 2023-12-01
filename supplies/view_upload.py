import asyncio
import datetime

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
from .tasks import *
from celery_progress.backend import Progress
from celery.result import AsyncResult


# @login_required(login_url='login')
# @allowed_users(allowed_roles=['admin'])
# def receive_and_load_new_supplies_order(request):

def celery_test(request):
    task = go_to_sleep.delay(1)
    return render(request, 'supplies/celery-test.html', {'task_id': task.task_id})


def get_progress(request, task_id):
    print("GET PROgRESS")
    progress = Progress(AsyncResult(task_id))
    percent_complete = int(progress.get_info()['progress']['percent'])
    if percent_complete == 100:
        return redirect('/')
    print(task_id)
    print(percent_complete)
    context = {'task_id': task_id, 'value': percent_complete}
    return render(request, 'partials/progress-bar.html', context)


def upload_supplies_for_new_delivery(request):
    form = NewDeliveryForm()
    if request.method == 'POST':
        form = NewDeliveryForm(request.POST)
        if form.is_valid():
            string_data = form.cleaned_data['description']
            makeDataUpload(string_data)

    # task = go_to_sleep.delay(1)
    # context = {'task_id': task.task_id, 'value': 0}
    return render(request, 'supplies/upload_supplies_for_new_delivery.html', {'form': form})


def makeDataUpload(string_data):
    result_array = string_data.split()
    for item in result_array:
        arr_item = item.split(',')
        if len(arr_item) == 1:
            barcode_str = arr_item[0]
            smn = barcode_str[32:-6]
            lot = barcode_str[18:-25]
            date_expired = barcode_str[23:-17]
            print('---------------')
            print(smn)
            print(lot)
            print(date_expired)