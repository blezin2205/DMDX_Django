from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from django.urls import reverse
from django.db.models import Prefetch, prefetch_related_objects
from supplies.models import *
from datetime import date
from dateutil.relativedelta import relativedelta
from django.contrib.auth import authenticate, login, logout
from supplies.filters import *
from supplies.forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.core.paginator import Paginator
from django.db.models import Count, Sum, F, Q
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


def generate_list_of_xls_from_preorders_list(preorders_list, withChangedStatus = False):
    selected_ids = map(int, preorders_list)
    fileteredOredrs = PreOrder.objects.filter(Q(state_of_delivery='accepted_by_customer') | Q(state_of_delivery='Awaiting') | Q(state_of_delivery='Partial'))
    if withChangedStatus:
        for ord in fileteredOredrs:
            if ord.state_of_delivery == 'accepted_by_customer':
                ord.state_of_delivery = 'Awaiting'
                ord.save()

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Preorders_List_{datetime.datetime.now().strftime('%d.%m.%Y  %H:%M')}.xlsx"
    wb = Workbook(response, {'in_memory': True})
    for preorder in fileteredOredrs:
        preorder_render_to_xls_by_preorder(response, preorder, wb)
    wb.close()
    return response




def preorder_render_to_xls_by_preorder(response, order: PreOrder, wb: Workbook):
    order_id = order.id
    supplies_in_order_all = order.supplyinpreorder_set.all()
    supplies_in_order = []
    for sup in supplies_in_order_all:
        if sup.count_in_order - sup.count_in_order_current > 0:
            supplies_in_order.append(sup)
    row_num = 4
    init_row_num = row_num


    ws = wb.add_worksheet(f'Order №{order_id}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)

    columns_table = [{'header': '№'},
                     {'header': 'Name'},
                     {'header': 'Category'},
                     {'header': 'REF'},
                     {'header': 'SMN code'},
                     {'header': 'Awaiting count'},
                     # {'header': 'Index'}
                     ]

    ws.write(0, 0,
             f'Замов. №{order_id} для {order.place.name[:30]}, {order.place.city_ref.name} від {order.dateCreated.strftime("%d-%m-%Y")}',
             format)

    format = wb.add_format()
    format.set_font_size(14)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 35)
    ws.set_column(2, 4, 20)
    ws.set_column(4, 5, 15)
    # ws.set_column(8, 8, 5)

    ws.add_table(row_num, 0, len(supplies_in_order) + row_num, len(columns_table) - 1, {'columns': columns_table})

    if order.comment:
        ws.write(1, 0, f'Коммент.: {order.comment}', format)
        ws.write(2, 0, f'Всього: {len(supplies_in_order)} шт.', format)
    else:
        ws.write(1, 0, f'Всього: {len(supplies_in_order)} шт.', format)



    for row in supplies_in_order:
        row_num += 1
        name = row.generalSupply.name
        ref = ''
        if row.generalSupply.ref:
            ref = row.generalSupply.ref
        smn = ''
        if row.generalSupply.SMN_code:
            smn = row.generalSupply.SMN_code
        category = ''
        if row.generalSupply.category:
            category = row.generalSupply.category
        count_in_order = row.count_in_order
        current_delivery_count = row.count_in_order_current
        count_borg = row.count_in_order - row.count_in_order_current
        date_expired = ''

        val_row = [name, category, ref, smn, count_borg]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - init_row_num)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)