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
from .views import *
from celery_progress.backend import Progress
from celery.result import AsyncResult


# @login_required(login_url='login')
# @allowed_users(allowed_roles=['admin'])
# def receive_and_load_new_supplies_order(request):

def celery_test(request):
    task = go_to_sleep.delay(1)
    return render(request, 'supplies/celery-test.html', {'task_id': task.task_id})


def get_progress(request, task_id, for_delivery_order_id):
    progress = Progress(AsyncResult(task_id))
    percent_complete = int(progress.get_info()['progress']['percent'])
    if percent_complete == 100:
        cartCountData = countCartItemsHelper(request)
        delivery_order = DeliveryOrder.objects.get(id=for_delivery_order_id)
        supplies = delivery_order.deliverysupplyincart_set.all()
        form = NewDeliveryForm()
        form.fields['description'].label = "Коментар"

        supDict = {}
        for d in supplies:
            t = supDict.setdefault(d.isRecognized, [])
            t.append(d)
        supDict = dict(sorted(supDict.items(), key=lambda x: not x[0]))
        return render(request, 'supplies/delivery_cart.html', {'cartCountData': cartCountData, 'supDict': supDict, 'delivery_order': delivery_order, 'form': form})

    print(task_id)
    print(percent_complete)
    context = {'task_id': task_id, 'for_delivery_order_id': for_delivery_order_id, 'value': percent_complete}
    return render(request, 'partials/progress-bar.html', context)


def upload_supplies_for_new_delivery(request):
    form = NewDeliveryForm()
    if request.method == 'POST':
        form = NewDeliveryForm(request.POST)
        if form.is_valid():
            string_data = form.cleaned_data['description']
            for_delivery_order = DeliveryOrder(from_user=request.user)
            for_delivery_order.save()
            task = makeDataUpload.delay(string_data, for_delivery_order.id)
            context = {'task_id': task.task_id, 'value': 0, 'for_delivery_order_id': for_delivery_order.id}
            return render(request, 'supplies/upload_supplies_new_delivery_progress.html', context)

    return render(request, 'supplies/upload_supplies_for_new_delivery.html', {'form': form})


def save_delivery(request, delivery_order_id):
    if request.method == 'POST':
        delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
        form = NewDeliveryForm(request.POST)
        if form.is_valid():
            string_data = form.cleaned_data['description']
            delivery_order.comment = string_data
            delivery_order.save()
        return redirect("/all_deliveries")


def all_deliveries(request):
    cartCountData = countCartItemsHelper(request)
    deliveries = DeliveryOrder.objects.all().order_by('-id')

    return render(request, 'supplies/all_deliveries_list.html', {'cartCountData': cartCountData, 'deliveries': deliveries})


def delete_delivery_action(request, delivery_order_id):
    if request.method == 'POST':
        delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
        sups_for_delivery_order = delivery_order.deliverysupplyincart_set.all()
        if 'delete_delivery' in request.POST:
            delivery_order.delete()
            print('delete_delivery')

        if 'delete_all' in request.POST:
            for item in sups_for_delivery_order.exclude(supply=None):
                count_in_delivery = item.count
                org_sup = item.supply
                org_sup.count -= count_in_delivery
                if org_sup.count == 0:
                    org_sup.delete()
                else:
                    org_sup.save()
            delivery_order.delete()
            print('delete_all')

        return redirect("/all_deliveries")


def delivery_detail(request, delivery_id):
    cartCountData = countCartItemsHelper(request)
    delivery_order = DeliveryOrder.objects.get(id=delivery_id)
    supplies = delivery_order.deliverysupplyincart_set.all()
    form = NewDeliveryForm()
    form.initial['description'] = delivery_order.comment
    form.fields['description'].label = "Коментар"

    supDict = {}
    for d in supplies:
        t = supDict.setdefault(d.isRecognized, [])
        t.append(d)
    supDict = dict(sorted(supDict.items(), key=lambda x: not x[0]))
    return render(request, 'supplies/delivery_detail.html', {'cartCountData': cartCountData, 'supDict': supDict, 'delivery_order': delivery_order, 'form': form})


def search_results_for_manual_add_in_delivery_order(request):
    search_text = request.POST.get('search')
    results = None
    if search_text != "":
        results = GeneralSupply.objects.filter(Q(name__icontains=search_text) | Q(ref__icontains=search_text) | Q(SMN_code__icontains=search_text))
    context = {"results": results}
    return render(request, 'partials/search_results_for_manual_add_in_delivery_order.html', context)