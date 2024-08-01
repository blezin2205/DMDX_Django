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
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import threading

# @login_required(login_url='login')
# @allowed_users(allowed_roles=['admin'])
# def receive_and_load_new_supplies_order(request):
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def celery_test(request):
    task = go_to_sleep.delay(1)
    return render(request, 'supplies/celery-test.html', {'task_id': task.task_id})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def get_progress(request, task_id, for_delivery_order_id):
    result = AsyncResult(task_id)
    progress = Progress(result)
    percent_complete = int(progress.get_info()['progress']['percent'])
    if percent_complete == 100:
        cartCountData = countCartItemsHelper(request)
        delivery_order = DeliveryOrder.objects.get(id=for_delivery_order_id)
        supplies = delivery_order.deliverysupplyincart_set.all().order_by('general_supply__name')
        total_count = supplies.aggregate(total_count=Sum('count'))['total_count']
        form = NewDeliveryForm()
        form.fields['description'].label = "Коментар"

        supDict = {}
        for d in supplies:
            t = supDict.setdefault(d.isRecognized, [])
            t.append(d)
        supDict = dict(sorted(supDict.items(), key=lambda x: not x[0]))
        status_of_task = result.status
        return render(request, 'supplies/delivery_cart.html', {'cartCountData': cartCountData, 'status_of_task': status_of_task, 'supDict': supDict, 'delivery_order': delivery_order, 'total_count': total_count, 'form': form})

    print(task_id)
    print(percent_complete)
    context = {'task_id': task_id, 'for_delivery_order_id': for_delivery_order_id, 'value': percent_complete}
    return render(request, 'partials/progress-bar.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def upload_supplies_for_new_delivery(request, delivery_order_id=None):
    cartCountData = countCartItemsHelper(request)
    form = NewDeliveryForm()
    if delivery_order_id != None:
        title = f'Додати штрих-коди до поставки № {delivery_order_id}'
    else:
        title = "Створити нову поставку"
    if request.method == 'POST':
        barcode_type = request.POST.get('barcode_type')
        form = NewDeliveryForm(request.POST)
        if form.is_valid():
            string_data = form.cleaned_data['description']
            if delivery_order_id != None:
                for_delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
                title = f'Додати штрих-коди до поставки № {for_delivery_order.id}'
            else:
                for_delivery_order = DeliveryOrder(from_user=request.user)
                for_delivery_order.save()
                title = "Створити нову поставку"
            task = makeDataUpload.delay(string_data, for_delivery_order.id, barcode_type)
            context = {'task_id': task.task_id, 'value': 0, 'for_delivery_order_id': for_delivery_order.id}
            return render(request, 'supplies/upload_supplies_new_delivery_progress.html', context)

    return render(request, 'supplies/upload_supplies_for_new_delivery.html', {'form': form, 'title': title,
                                                                                                            'cartCountData': cartCountData})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def upload_supplies_for_new_delivery_from_js_script(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        barcode_type = data.get('barcode_type', '')
        string_data = data.get('description', '')
        delivery_id = data.get('deliveryOrderId', '')

        # Process the data as needed
        response_data = {
            'status': 'success',
            'barcode_type': barcode_type,
            'description': string_data
        }
        print("delivery_id", delivery_id)
        print(delivery_id == 'None')


        if delivery_id == 'None':
            for_delivery_order = DeliveryOrder(from_user=request.user)
            for_delivery_order.save()
            title = "Створити нову поставку"
            isUpdate = False
        else:
            delivery_id = int(delivery_id)
            for_delivery_order = DeliveryOrder.objects.get(id=delivery_id)
            title = f'Додати штрих-коди до поставки № {for_delivery_order.id}'
            isUpdate = True
        print("START")
        t = threading.Thread(target=threading_create_delivery_async,
                             args=[request, string_data, for_delivery_order.id, barcode_type, isUpdate], daemon=True)
        t.start()
        messages.success(request, 'Обробка даних запущена в фоновому режимі.')

        return JsonResponse(response_data)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

def upload_supplies_for_new_delivery_noncelery(request, delivery_order_id=None):
    cartCountData = countCartItemsHelper(request)
    form = NewDeliveryForm()
    if delivery_order_id is not None:
        title = f'Додати штрих-коди до поставки № {delivery_order_id}'
    else:
        title = "Створити нову поставку"
    if request.method == 'POST':
        barcode_type = request.POST.get('barcode_type')
        form = NewDeliveryForm(request.POST)
        if form.is_valid():
            string_data = form.cleaned_data['description']
            if delivery_order_id is not None:
                for_delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
                title = f'Додати штрих-коди до поставки № {for_delivery_order.id}'

            else:
                for_delivery_order = DeliveryOrder(from_user=request.user)
                for_delivery_order.save()
                title = "Створити нову поставку"
            t = threading.Thread(target=threading_create_delivery_async, args=[request, string_data, for_delivery_order.id, barcode_type], daemon=True)
            t.start()
            return JsonResponse({'success': False, 'message': 'Форма не дійсна.'})
            # return redirect('/all_deliveries')
    return render(request, 'supplies/upload_supplies_for_new_delivery.html', {'form': form, 'cartCountData': cartCountData, 'title': title, 'delivery_order_id': delivery_order_id})

def threading_create_delivery_async(request, string_data, delivery_order_id, barcode_type, isUpdate = False):
    for_delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
    makeDataUpload_nonCelery(string_data, delivery_order_id, barcode_type)
    cartCountData = countCartItemsHelper(request)
    supplies = for_delivery_order.deliverysupplyincart_set.all().order_by('general_supply__name')
    total_count = supplies.aggregate(total_count=Sum('count'))['total_count']
    supDict = {}
    for d in supplies:
        t = supDict.setdefault(d.isRecognized, [])
        t.append(d)
    supDict = dict(sorted(supDict.items(), key=lambda x: not x[0]))

    # Відправити повідомлення про завершення
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'delivery_updates',
        {
            'type': 'delivery_complete',
            'message': f'Поставка №{delivery_order_id} оновлена успішно!' if isUpdate else f'Поставка №{delivery_order_id} створена успішно!',
            'delivery_order_id': delivery_order_id
        }
    )

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_more_scan_to_exist_delivery_order(request, delivery_id):
    return upload_supplies_for_new_delivery_noncelery(request, delivery_id)


# @login_required(login_url='login')
# @allowed_users(allowed_roles=['admin'])
# def upload_sup_from_delivery_order_and_save_db(request, delivery_order_id):
#     task = gen_sup_and_update_db.delay(delivery_order_id)
#     context = {'task_id': task.task_id, 'value': 0, 'for_delivery_order_id': delivery_order_id}
#     return render(request, 'supplies/upload_supplies_new_delivery_progress.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def upload_sup_from_delivery_order_and_save_db(request, delivery_order_id):
    if request.method == 'POST':
        # t = threading.Thread(target=gen_sup_and_update_db_async,
        #                      args=[request, delivery_order_id], daemon=True)
        # t.start()
        del_order = DeliveryOrder.objects.get(id=delivery_order_id)
        sup_set = del_order.deliverysupplyincart_set.filter(isRecognized=True)
        total_requests = len(sup_set)
        i = 0
        for item in sup_set:
            if item.general_supply:
                try:
                    sup = item.general_supply.general.get(supplyLot=item.supplyLot, expiredDate=item.expiredDate)
                    sup.count += item.count
                except:
                    sup = Supply(name=item.general_supply.name,
                                 general_supply=item.general_supply,
                                 category=item.general_supply.category,
                                 ref=item.general_supply.ref,
                                 supplyLot=item.supplyLot,
                                 count=item.count,
                                 expiredDate=item.expiredDate)
                item.supply = sup
                sup.save()
                item.save()
            i += 1
        del_order.isHasBeenSaved = True
        del_order.save()
        response_data = {
            'message': 'Success',
            'delivery_order_id': delivery_order_id,
            'total_count': i
        }
        return JsonResponse(response_data)

    # On failure or if not POST
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def save_delivery(request, delivery_order_id):
    if request.method == 'POST':
        delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
        form = NewDeliveryForm(request.POST)
        if form.is_valid():
            string_data = form.cleaned_data['description']
            delivery_order.comment = string_data
            delivery_order.save()
        return redirect("/all_deliveries")

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def all_deliveries(request):
    cartCountData = countCartItemsHelper(request)
    deliveries = DeliveryOrder.objects.all().order_by('-id')

    return render(request, 'supplies/all_deliveries_list.html', {'cartCountData': cartCountData, 'deliveries': deliveries})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
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

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def delivery_detail(request, delivery_id):
    cartCountData = countCartItemsHelper(request)
    delivery_order = DeliveryOrder.objects.get(id=delivery_id)
    supplies = delivery_order.deliverysupplyincart_set.all().order_by('general_supply__name')
    total_count = supplies.aggregate(total_count=Sum('count'))['total_count']
    form = NewDeliveryForm()
    form.initial['description'] = delivery_order.comment
    form.fields['description'].label = "Коментар"

    supDict = {}
    for d in supplies:
        t = supDict.setdefault(d.isRecognized, [])
        t.append(d)
    supDict = dict(sorted(supDict.items(), key=lambda x: not x[0]))
    return render(request, 'supplies/delivery_detail.html', {'cartCountData': cartCountData, 'total_count': total_count, 'supDict': supDict, 'delivery_order': delivery_order, 'form': form})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def search_results_for_manual_add_in_delivery_order(request, delivery_order_id):
    search_text = request.POST.get('search')
    results = None
    if search_text != "":
        results = GeneralSupply.objects.filter(Q(name__icontains=search_text) | Q(ref__icontains=search_text) | Q(SMN_code__icontains=search_text))
    context = {"results": results, 'delivery_order_id': delivery_order_id}
    return render(request, 'partials/search_results_for_manual_add_in_delivery_order.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_gen_sup_in_delivery_order_manual_list(request):
    if request.method == 'POST':
        gen_sup_id = request.POST.get('gen_sup_id')
        delivery_order_id = request.POST.get('delivery_order_id')
        gen_sup = GeneralSupply.objects.get(id=gen_sup_id)
        context = {"item": gen_sup, 'delivery_order_id': delivery_order_id}
        return render(request, 'partials/search_add_manual_results_for_results_choosed_gen_supps.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_gen_sup_in_delivery_order_manual_list_delete_action(request):
    del_sup_id = request.POST.get('del_sup_id')
    try:
        sup_delivery = DeliverySupplyInCart.objects.get(id=del_sup_id)
        sup_delivery.delete()
    except:
        pass
    return HttpResponse(status=200)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_gen_sup_in_delivery_order_manual_list_edit_action(request):
    if request.method == 'POST':
        deliverySupplyInCart_id = request.POST.get('item_id')
        del_sup = DeliverySupplyInCart.objects.get(id=deliverySupplyInCart_id)
        gen_sup = del_sup.general_supply

        context = {"item": gen_sup, 'delivery_order_id': del_sup.delivery_order_id, 'del_sup': del_sup}
        return render(request, 'partials/search_results_for_results_choosed_gen_supps.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_gen_sup_in_delivery_order_manual_list_save_action(request):
    if request.method == 'POST':
        delivery_order_id = request.POST.get('delivery_order_id')
        del_sup_id = request.POST.get('del_sup_id') or None
        gen_sup_id = request.POST.get('gen_sup_id')
        input_lot = request.POST.get(f'lot_input_field_{gen_sup_id}').strip()
        input_expired = request.POST.get(f'expired_input_field_{gen_sup_id}').strip()
        input_count = request.POST.get(f'count_input_field_{gen_sup_id}').strip()
        gen_sup = GeneralSupply.objects.get(id=gen_sup_id)
        del_order = DeliveryOrder.objects.get(id=delivery_order_id)

        date_expired_date = datetime.datetime.strptime(input_expired, '%Y-%m-%d').date()
        try:
            sup_delivery = DeliverySupplyInCart.objects.get(id=del_sup_id)
            sup_delivery.supplyLot = input_lot
            sup_delivery.count = input_count
            sup_delivery.expiredDate = date_expired_date
            sup_delivery.expiredDate_desc = input_expired
        except:
            sup_delivery = DeliverySupplyInCart(general_supply=gen_sup,
                                                supplyLot=input_lot,
                                                count=input_count,
                                                expiredDate_desc=input_expired,
                                                expiredDate=date_expired_date,
                                                isRecognized=True,
                                                isHandleAdded=True,
                                                delivery_order=del_order)
        sup_delivery.save()
        context = {"item": sup_delivery}
        return render(request, 'partials/saved_instance_of_manual_added_sup_in_delivery.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def delivery_order_export_to_excel(request, delivery_order_id):
    del_order = DeliveryOrder.objects.get(id=delivery_order_id)
    supplies = del_order.deliverysupplyincart_set.filter(isRecognized=True).order_by('general_supply__name')
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

        lot = row.supplyLot
        count = row.count
        date_expired = row.expiredDate.strftime("%d.%m.%Y")

        val_row = [action, name, ref, lot, count, date_expired, category]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 15)
    ws.set_column(2, 2, 35)
    ws.set_column(3, 4, 15)
    ws.set_column(5, 6, 10)
    ws.set_column(7, 7, 12)

    ws.add_table(3, 0, row_num, len(columns_table) - 1, {'columns': columns_table})
    wb.close()
    return response