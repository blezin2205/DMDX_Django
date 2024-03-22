import asyncio
import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from django.urls import reverse
from django.db.models import Prefetch, prefetch_related_objects
from ..decorators import unauthenticated_user, allowed_users
from ..models import *
from ..serializers import *
from datetime import date
from dateutil.relativedelta import relativedelta
from django.contrib.auth import authenticate, login, logout
from ..filters import *
from ..forms import *
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
from ..tasks import *
from ..views import *

@login_required(login_url='login')
def booked_supplies_list(request, client_id):
    isClient = request.user.isClient()
    place = Place.objects.get(id=client_id)
    # Prefetch GeneralSupply related to SupplyInBookedOrder to minimize DB queries
    supplies_list = SupplyInBookedOrder.objects.filter(supply_for_place=place) \
        .order_by('id') \
        .order_by('generalSupply__name') \
        .select_related('generalSupply')

    title = f'Всі бронювання для: \n{place.name}, {place.city_ref.name}'
    cartCountData = countCartItemsHelper(request)
    suppFilter = BookedSuppliesFilter(request.GET, queryset=supplies_list)
    supplies_list = suppFilter.qs
    # Group SupplyInBookedOrder objects by GeneralSupply name
    grouped_supplies = {}
    for supply in supplies_list:
        general_supply_name = supply.generalSupply
        if general_supply_name not in grouped_supplies:
            grouped_supplies[general_supply_name] = []
        grouped_supplies[general_supply_name].append(supply)

    general_supply_list = grouped_supplies

    if isClient:
        title = f'Всі ваші заброньовані товари'
        user_places = request.user.place_set.all()
        user_allowed_categories = set()
        for plc in user_places:
            categories = plc.allowed_categories.values_list('id', flat=True)
            # user_allowed_categories.add(categories.values())
            for quer in categories:
                user_allowed_categories.add(quer)
        category = Category.objects.filter(id__in=user_allowed_categories)
        suppFilter.form.fields['category'].queryset = category


    if isClient and place.id != request.user.get_user_place_id():
        title = "Permission denied!"
        supplies_list = ""
        general_supply_list = ''
        place = ""
        cartCountData = ""

    if 'delete_all_sups' in request.GET:
        for booked_sup in supplies_list:
            booked_sup.supply.countOnHold -= booked_sup.count_in_order
            booked_sup.supply.save(update_fields=['countOnHold'])
            booked_sup.delete()

    if 'add_all_sups_to_cart' in request.GET:
        try:
            booked_cart = BookedOrderInCart.objects.get(place=place)
        except:
            booked_cart = BookedOrderInCart(userCreated=request.user,
                                            place=place)
            booked_cart.save()

        for booked_sup in supplies_list:
            count_in_cart = booked_sup.count_in_order - booked_sup.countOnHold
            if count_in_cart > 0:
                try:
                    booked_sup_in_cart = booked_cart.bookedsupplyinorderincart_set.get(supply=booked_sup)
                    booked_sup_in_cart.count_in_order = count_in_cart
                    booked_sup_in_cart.save(update_fields=['count_in_order'])
                except:
                    booked_sup_in_cart = BookedSupplyInOrderInCart(count_in_order=count_in_cart,
                                                                   supply=booked_sup,
                                                                   supply_for_order=booked_cart,
                                                                   lot=booked_sup.lot,
                                                                   date_expired=booked_sup.date_expired)
                    booked_sup_in_cart.save()
        return redirect(f'/booked_cart_details/{booked_cart.id}')

    if 'xls_button' in request.GET:
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f"attachment; filename=Booked_Supplies_List.xlsx"

        row_num = 3

        wb = Workbook(response, {'in_memory': True})
        ws = wb.add_worksheet(f'bkd_sup_list_for_{place.id}')
        format = wb.add_format({'bold': True})
        format.set_font_size(16)

        columns_table = [{'header': '№'},
                         {'header': 'Назва товару'},
                         {'header': 'Пакування/Тести'},
                         {'header': 'SMN Code'},
                         {'header': 'REF'},
                         {'header': 'LOT'},
                         {'header': 'К-ть'},
                         {'header': 'Тер.прид.'},
                         {'header': 'Категорія'}
                         ]

        ws.write(0, 0,
                 f'Загальний список заброньованих товарів для {place.get_place_name()}',
                 format)

        format = wb.add_format({'num_format': 'dd.mm.yyyy'})
        format.set_font_size(12)

        for row in supplies_list:
            row_num += 1
            name = ''
            smn = ''
            package = ''
            ref = ''
            lot = ''
            category = ''
            name = row.generalSupply.name
            category = row.generalSupply.category.name
            if row.generalSupply.ref:
                ref = row.generalSupply.ref
            if row.generalSupply.SMN_code:
                smn = row.generalSupply.SMN_code
            if row.generalSupply.package_and_tests:
                package = row.generalSupply.package_and_tests
            lot = row.supply.supplyLot
            count = row.count_in_order
            date_expired = row.date_expired.strftime("%d.%m.%Y")

            val_row = [name, package, smn, ref, lot, count, date_expired, category]

            for col_num in range(len(val_row)):
                ws.write(row_num, 0, row_num - 3)
                ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 35)
        ws.set_column(2, 5, 15)
        ws.set_column(6, 7, 10)
        ws.set_column(8, 8, 15)

        ws.add_table(3, 0, suppFilter.qs.count() + 3, len(columns_table) - 1, {'columns': columns_table})
        wb.close()
        return response


    return render(request, 'booked_flow/booked_supplies_list.html',
                  {'title': title, 'isBookedList': True, 'isHome': True, 'suppFilter': suppFilter, 'supplies': supplies_list, 'general_supply_list': general_supply_list, 'for_place': place, 'cartCountData': cartCountData},
                  )

@login_required(login_url='login')
def add_sup_to_booked_cart(request, sup_id):
    booked_sup = SupplyInBookedOrder.objects.get(id=sup_id)
    for_place = booked_sup.supply_for_place
    try:
        booked_cart = BookedOrderInCart.objects.get(place=for_place)
    except:
        booked_cart = BookedOrderInCart(userCreated=request.user,
                                        place=for_place)
        booked_cart.save()
    try:
        booked_sup_in_cart = booked_cart.bookedsupplyinorderincart_set.get(supply=booked_sup)
        booked_sup_in_cart.count_in_order += 1
        booked_sup_in_cart.save(update_fields=['count_in_order'])
    except:
        booked_sup_in_cart = BookedSupplyInOrderInCart(count_in_order=1,
                                                       supply=booked_sup,
                                                       supply_for_order=booked_cart,
                                                       lot=booked_sup.lot,
                                                       date_expired=booked_sup.date_expired)
        booked_sup_in_cart.save()

    response = render(request, 'booked_flow/cart_button.html',
                      {'supp': booked_sup, 'booked_sup_in_cart': booked_sup_in_cart})
    trigger_client_event(response, 'subscribe-booked-cart-badge-count', {})
    return response

@login_required(login_url='login')
def booked_cart_badge_count_refresh(request):
    booked_carts = BookedOrderInCart.objects.all()
    carts_count = booked_carts.count()
    if 2 > carts_count > 0:
        is_one_cart = "IS_ONE"
    else:
        is_one_cart = "IS_MANY"
    booked_cart_first = booked_carts.first()
    cartCountData = {'is_one_cart': is_one_cart, 'booked_cart_first': booked_cart_first}
    return render(request, 'booked_flow/booked-cart-badge.html', {'cartCountData': cartCountData})


def booked_cart_details(request, booked_cart_id):
    booked_cart = BookedOrderInCart.objects.get(id=booked_cart_id)
    sups_in_booked_cart = booked_cart.bookedsupplyinorderincart_set.all()
    cartCountData = countCartItemsHelper(request)
    orderForm = OrderInCartForm(request.POST or None)
    if request.method == 'POST':

        if 'delete' in request.POST:
            next = request.POST.get('next')
            booked_cart.delete()
            return HttpResponseRedirect(next)
        else:
            if orderForm.is_valid():
                comment = orderForm.cleaned_data['comment']
                dateToSend = orderForm.cleaned_data['dateToSend']
                order = Order(userCreated=request.user, place=booked_cart.place,
                              comment=comment, dateToSend=dateToSend)
                order.save()
                for sup in sups_in_booked_cart:
                    count = int(request.POST.get(f'count_{sup.id}'))
                    if count > sup.supply.count_in_order:
                        count = sup.supply.count_in_order
                    sup.supply.countOnHold += count
                    suppInOrder = SupplyInOrder(count_in_order=count,
                                                supply=sup.supply.supply,
                                                generalSupply=sup.supply.generalSupply,
                                                supply_for_order=order,
                                                supply_in_preorder=sup.supply.supply_in_preorder,
                                                supply_in_booked_order=sup.supply,
                                                lot=sup.lot,
                                                date_created=sup.date_created,
                                                date_expired=sup.date_expired,
                                                internalName=sup.supply.generalSupply.name,
                                                internalRef=sup.supply.generalSupply.ref)
                    suppInOrder.save()
                    sup.supply.save(update_fields=['countOnHold'])

                t = threading.Thread(target=sendTeamsMsgCart, args=[request, order], daemon=True)
                t.start()
                booked_cart.delete()
                return redirect('/orders')

    return render(request, 'booked_flow/booked_cart.html',
                  {'booked_cart': booked_cart, 'orderForm': orderForm, 'sups_in_booked_cart': sups_in_booked_cart, 'cartCountData': cartCountData})


def booked_carts_list(request):
    booked_carts = BookedOrderInCart.objects.all()
    cartCountData = countCartItemsHelper(request)
    return render(request, 'booked_flow/all_booked_carts_list.html',
                  {'booked_carts': booked_carts, 'cartCountData': cartCountData})


def delete_sup_from_booked_cart_delete_action(request):
    del_sup_id = request.POST.get('del_sup_id')
    cart_id = request.POST.get('booked_cart_id')
    booked_cart = BookedOrderInCart.objects.get(id=cart_id)
    try:
        sup_delivery = BookedSupplyInOrderInCart.objects.get(id=del_sup_id)
        sup_delivery.delete()
    except:
        pass
    if booked_cart.bookedsupplyinorderincart_set.count() == 0:
        booked_cart.delete()
    return HttpResponse(status=200)


def minus_from_booked_supply_list_item(request):
    del_sup_id = request.POST.get('del_sup_id')
    print(del_sup_id)
    sup = SupplyInBookedOrder.objects.get(id=del_sup_id)
    sup.count_in_order -= 1
    sup.supply.countOnHold -= 1
    sup.supply.save(update_fields=['countOnHold'])
    gen_sup = sup.generalSupply
    supply_list = gen_sup.supplyinbookedorder_set.filter(supply_for_place=sup.supply_for_place).order_by('id')
    if sup.count_in_order == 0:
        sup.delete()
        if supply_list.count() == 0:
            return HttpResponse(status=200)
    else:
        sup.save(update_fields=['count_in_order'])

    return render(request, 'booked_flow/booked_supply_list_item.html',
                      {'el': gen_sup, 'supply_list': supply_list})


def plus_from_booked_supply_list_item(request):
    del_sup_id = request.POST.get('del_sup_id')
    print(del_sup_id)
    sup = SupplyInBookedOrder.objects.get(id=del_sup_id)
    sup.count_in_order += 1
    sup.supply.countOnHold += 1
    sup.supply.save(update_fields=['countOnHold'])
    sup.save(update_fields=['count_in_order', 'supply'])
    gen_sup = sup.generalSupply
    supply_list = gen_sup.supplyinbookedorder_set.filter(supply_for_place=sup.supply_for_place).order_by('id')
    return render(request, 'booked_flow/booked_supply_list_item.html',
                  {'el': gen_sup, 'supply_list': supply_list})


def delete_sup_from_booked_sups(request, sup_id):
    booked_sup = SupplyInBookedOrder.objects.get(id=sup_id)
    booked_sup.supply.countOnHold -= booked_sup.count_in_order
    booked_sup.supply.save(update_fields=['countOnHold'])
    booked_sup.delete()
    return HttpResponse(status=200)


def convert_order_to_booked_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()
    for s in supplies_in_order:
        try:
            supInOrder = SupplyInBookedOrder.objects.get(supply=s.supply, supply_in_preorder=s.supply_in_preorder,
                                                         supply_for_place=order.place)
            supInOrder.count_in_order += s.count
        except:
            supInOrder = SupplyInBookedOrder(
                count_in_order=s.count_in_order,
                generalSupply=s.generalSupply,
                supply=s.supply,
                supply_for_place=order.place,
                supply_in_preorder=s.supply_in_preorder,
                lot=s.supply.supplyLot,
                date_expired=s.supply.expiredDate,
                internalName=s.generalSupply.name,
                internalRef=s.generalSupply.ref
            )
        supInOrder.save()
        s.delete()
    if order.supplyinorder_set.count() == 0:
       order.delete()
    return redirect('/orders')
