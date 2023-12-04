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


def search_results_for_manual_add_in_delivery_order(request, delivery_order_id):
    search_text = request.POST.get('search')
    results = None
    if search_text != "":
        results = GeneralSupply.objects.filter(Q(name__icontains=search_text) | Q(ref__icontains=search_text) | Q(SMN_code__icontains=search_text))
    context = {"results": results, 'delivery_order_id': delivery_order_id}
    return render(request, 'partials/search_results_for_manual_add_in_delivery_order.html', context)


def add_gen_sup_in_delivery_order_manual_list(request):
    if request.method == 'POST':
        gen_sup_id = request.POST.get('gen_sup_id')
        delivery_order_id = request.POST.get('delivery_order_id')
        gen_sup = GeneralSupply.objects.get(id=gen_sup_id)
        context = {"item": gen_sup, 'delivery_order_id': delivery_order_id}
        return render(request, 'partials/search_results_for_results_choosed_gen_supps.html', context)


def add_gen_sup_in_delivery_order_manual_list_delete_action(request):
    del_sup_id = request.POST.get('del_sup_id')
    print(del_sup_id)

    return HttpResponse(status=200)


def add_gen_sup_in_delivery_order_manual_list_edit_action(request):
    if request.method == 'POST':
        deliverySupplyInCart_id = request.POST.get('item_id')
        del_sup = DeliverySupplyInCart.objects.get(id=deliverySupplyInCart_id)
        gen_sup = del_sup.general_supply

        context = {"item": gen_sup, 'delivery_order_id': del_sup.delivery_order_id, 'del_sup': del_sup}
        return render(request, 'partials/search_results_for_results_choosed_gen_supps.html', context)


def add_gen_sup_in_delivery_order_manual_list_save_action(request):
    if request.method == 'POST':
        delivery_order_id = request.POST.get('delivery_order_id')
        del_sup_id = request.POST.get('del_sup_id')
        gen_sup_id = request.POST.get('gen_sup_id')
        input_lot = request.POST.get(f'lot_input_field_{gen_sup_id}').strip()
        input_expired = request.POST.get(f'expired_input_field_{gen_sup_id}').strip()
        input_count = request.POST.get(f'count_input_field_{gen_sup_id}').strip()

        date_expired_date = datetime.datetime.strptime(input_expired, '%Y%m%d')
        delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
        gen_sup = GeneralSupply.objects.get(id=gen_sup_id)

        try:
            sup_delivery = delivery_order.deliverysupplyincart_set.get(id=del_sup_id)
            sup_delivery.supplyLot = input_lot
            sup_delivery.expiredDate = input_expired
            prev_count = sup_delivery.count
            new_count = int(input_count) - int(prev_count)
            sup = sup_delivery.supply
            sup.count += new_count
            sup_delivery.count = input_count
            print("NEW COUNT", new_count)
            print("input_count", input_count)
            print("prev_count", prev_count)
            try:
                sup = gen_sup.general.get(supplyLot=input_lot, expiredDate=date_expired_date)
                sup.count += new_count
            except:
                sup_delivery.supply.count -= int(prev_count)
                if sup_delivery.supply.count == 0:
                    sup_delivery.supply.delete()
                else:
                    sup_delivery.supply.save()
                sup = Supply(name=gen_sup.name,
                             general_supply=gen_sup,
                             category=gen_sup.category,
                             ref=gen_sup.ref,
                             supplyLot=input_lot,
                             count=int(input_count),
                             expiredDate=date_expired_date)
                sup_delivery.supply = sup

        except:
            try:
                sup = gen_sup.general.get(supplyLot=input_lot, expiredDate=date_expired_date)
                sup.count += int(input_count)
            except:
                sup = Supply(name=gen_sup.name,
                             general_supply=gen_sup,
                             category=gen_sup.category,
                             ref=gen_sup.ref,
                             supplyLot=input_lot,
                             count=input_count,
                             expiredDate=date_expired_date)
            sup_delivery = DeliverySupplyInCart(
                general_supply=gen_sup,
                SMN_code=gen_sup.SMN_code,
                supplyLot=input_lot,
                count=input_count,
                expiredDate=input_expired,
                delivery_order=delivery_order,
                isRecognized=True,
                isHandleAdded=True,
                supply=sup)
        sup.save()
        sup_delivery.save()
        context = {"item": sup_delivery}
        return render(request, 'partials/saved_instance_of_manual_added_sup_in_delivery.html', context)


def delivery_order_export_to_excel(request, delivery_order_id):
    del_order = DeliveryOrder.objects.get(id=delivery_order_id)
    supplies = del_order.deliverysupplyincart_set.filter(isRecognized=True)
    date_created = del_order.date_created.strftime("%d.%m.%Y")
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Delivery_{del_order.id}_{date_created}.xlsx"

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet(f'Delivery_{del_order.id}_{date_created}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)

    columns_table = [{'header': '№'},
                     {'header': 'ACTION'},
                     {'header': 'Назва товару'},
                     {'header': 'REF'},
                     {'header': 'LOT'},
                     {'header': 'К-ть'},
                     {'header': 'Тер.прид.'},
                     {'header': 'Категорія'},
                     {'header': 'Оновлено'},
                     ]

    ws.write(0, 0, f'Загальний список товарів поставки #{del_order.id} від {date_created}', format)

    format = wb.add_format({'num_format': 'dd.mm.yyyy'})
    format.set_font_size(12)

    row_num = 3

    for row in supplies:
        row_num += 1
        action = ''
        name = ''
        ref = ''
        lot = ''
        category = ''
        if row.isHandleAdded:
            action = 'Вручну'
        else:
            action = 'Скан'

        if row.general_supply:
            name = row.general_supply.name
            ref = row.general_supply.ref
            category = row.general_supply.category.name

        if row.supply:
            lot = row.supply.supplyLot
        count = row.count
        date_expired = row.supply.expiredDate.strftime("%d.%m.%Y")
        date_created = row.supply.dateCreated.strftime("%d.%m.%Y")

        val_row = [action, name, ref, lot, count, date_expired, category, date_created]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 15)
    ws.set_column(2, 2, 35)
    ws.set_column(3, 4, 15)
    ws.set_column(5, 6, 10)
    ws.set_column(7, 8, 12)

    ws.add_table(3, 0, row_num, len(columns_table) - 1, {'columns': columns_table})
    wb.close()
    return response