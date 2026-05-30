"""Excel export/import views and helpers extracted from views.py."""
import datetime
from collections import OrderedDict, defaultdict

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, ExpressionWrapper, F, IntegerField, Max, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from googletrans import Translator
from xlsxwriter.workbook import Workbook

from supplies.analytics import PreorderAnalytics
from supplies.decorators import allowed_users
from supplies.models import (
    Category,
    City,
    Device,
    GeneralSupply,
    Order,
    Place,
    PreOrder,
    Supply,
    SupplyInOrder,
    SupplyInPreorder,
)
from supplies.query_utils import devices_list_queryset


def _group_order_supplies_for_display(supplies_qs):
    """Групує SupplyInOrder за generalSupply для вкладеної таблиці (як home)."""
    buckets = OrderedDict()
    for item in supplies_qs.order_by('generalSupply__category_id', 'generalSupply__name'):
        key = item.generalSupply_id if item.generalSupply_id else -item.pk
        buckets.setdefault(key, []).append(item)

    return [{'counter': idx, 'items': items} for idx, items in enumerate(buckets.values(), start=1)]


def export_child_supplies_xlsx(supplies, title, table_row_count, use_available_count=False):
    """Export child supplies list to Excel."""
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = "attachment; filename=Supply_List.xlsx"

    row_num = 3
    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet('Supply-List')
    title_format = wb.add_format({'bold': True})
    title_format.set_font_size(16)

    columns_table = [
        {'header': '№'},
        {'header': 'Назва товару'},
        {'header': 'Пакування/Тести'},
        {'header': 'SMN Code'},
        {'header': 'REF'},
        {'header': 'LOT'},
        {'header': 'К-ть'},
        {'header': 'Тер.прид.'},
        {'header': 'Категорія'},
        {'header': 'Оновлено'},
    ]

    ws.write(0, 0, title, title_format)

    cell_format = wb.add_format({'num_format': 'dd.mm.yyyy'})
    cell_format.set_font_size(12)

    for row in supplies:
        row_num += 1
        name = ''
        smn = ''
        package = ''
        ref = ''
        lot = ''
        category = ''
        if row.name:
            name = row.name
        if row.general_supply:
            name = row.general_supply.name
            category = row.general_supply.category.name
            package = row.general_supply.package_and_tests
            if row.general_supply.ref:
                ref = row.general_supply.ref
            if row.general_supply.SMN_code:
                smn = row.general_supply.SMN_code
            if row.general_supply.package_and_tests:
                package = row.general_supply.package_and_tests

        if row.supplyLot:
            lot = row.supplyLot
        count = (row.count - row.countOnHold) if use_available_count else row.count
        date_expired = row.expiredDate.strftime("%d.%m.%Y")
        date_created = row.dateCreated.strftime("%d.%m.%Y")

        val_row = [name, package, smn, ref, lot, count, date_expired, category, date_created]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), cell_format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 35)
    ws.set_column(2, 5, 15)
    ws.set_column(6, 7, 10)
    ws.set_column(7, 8, 12)

    ws.add_table(3, 0, table_row_count + 3, len(columns_table) - 1, {'columns': columns_table})
    wb.close()
    return response


def export_selected_orders_to_xlsx(selected_orders):
    """Build Excel workbook for selected orders grouped by place."""
    orders_by_place = defaultdict(list)
    for order in selected_orders:
        orders_by_place[order.place].append(order)

    supply_in_order_list = defaultdict(list)
    for place, sel_orders in orders_by_place.items():
        supply_in_order_dict = defaultdict(int)
        sel_orders_ids = []
        for sel_order in sel_orders:
            sel_orders_ids.append(str(sel_order.id))
            supply_in_orders = SupplyInOrder.objects.filter(supply_for_order=sel_order)
            for supply_in_order in supply_in_orders:
                key = supply_in_order.supply
                supply_in_order_dict[key] += supply_in_order.count_in_order

        sel_orders_ids = ",".join(sel_orders_ids)
        for key, count in supply_in_order_dict.items():
            supply_in_order = key
            supply_in_order.count = count
            supply_in_order_list[(place, sel_orders_ids)].append(supply_in_order)
    return get_selected_xls_orders_sups(supply_in_order_list.items())


def register_exls_selected_buttons(request):
    cheked = False
    merge_button_available = False
    if request.method == 'POST':
        selected_orders = request.POST.getlist('register_exls_selected_buttons')
        cheked = len(selected_orders) > 0
        merge_button_available = len(selected_orders) > 1
    return render(request, 'partials/register_butons_for_seelcted_orders.html', {'cheked': cheked, 'merge_button_available': merge_button_available})
def get_selected_xls_orders_sups(supply_in_order_list: defaultdict):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Selected_Orders_List_{datetime.datetime.now().strftime('%d.%m.%Y  %H:%M')}.xlsx"
    wb = Workbook(response, {'in_memory': True})

    for order_list_info in supply_in_order_list:
        print(order_list_info)
        render_to_xls_selected_order(order_list_info[0][1], order_list_info[0][0], order_list_info[1], wb)
    wb.close()
    return response


def render_to_xls_selected_order(table_header, place, supplies_in_order, wb):
    counts_by_id = {supply.id: supply.count for supply in supplies_in_order}
    supplies_in_order = list(
        Supply.objects.filter(id__in=counts_by_id).select_related(
            'general_supply',
            'general_supply__category',
        )
    )
    for supply in supplies_in_order:
        supply.count = counts_by_id[supply.id]

    supply_groups = _group_selected_supplies_for_display(supplies_in_order)
    total_rows = len(supplies_in_order)

    ws = wb.add_worksheet(f'№{place.id}')
    for col_num, width in enumerate(ORDER_DETAIL_XLS_COLUMN_WIDTHS):
        ws.set_column(col_num, col_num, width)

    city = _order_detail_xls_place_city(place)
    row_num = _write_xls_meta_header_block(ws, wb, [
        ('title', f'{place.name}, {city}. Замовлення №: {table_header}'),
        ('info', f'Всього: {total_rows} шт.'),
    ])

    columns_table = [
        '№', 'Назва товару', 'Пакування / Тести', 'Категорія', 'REF', 'SMN Code', 'LOT', 'К-ть', 'Тер.прид.',
    ]
    header_format = wb.add_format({
        'bold': True,
        'font_size': 11,
        'font_color': '#FFFFFF',
        'bg_color': '#4F6D9A',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1,
        'border_color': '#3D5678',
    })
    for col_num, header in enumerate(columns_table):
        ws.write(row_num, col_num, header, header_format)

    ws.outline_settings(True, False, False, True)
    table_header_row = row_num
    group_formats = _order_detail_xls_data_formats(wb)
    row_num = _write_grouped_supply_rows_to_xls(
        ws,
        supply_groups,
        row_num,
        group_formats,
        _selected_supply_xls_product_fields,
        _selected_supply_xls_lot_fields,
    )
    ws.autofilter(table_header_row, 0, row_num, ORDER_DETAIL_XLS_LAST_COL)
    ws.freeze_panes(table_header_row + 1, 0)
def generate_list_of_xls_from_preorders_list(preorders_list, withChangedStatus = False, set_complete_ctatus = False, set_is_closed=False, all_items=False):
    selected_ids = map(int, preorders_list)
    fileteredOredrs = PreOrder.objects.filter(pk__in=selected_ids)
    if withChangedStatus:
        for ord in fileteredOredrs:
            if ord.state_of_delivery == 'accepted_by_customer':
                ord.state_of_delivery = 'Awaiting'
                ord.save(update_fields=['state_of_delivery'])
    if set_complete_ctatus:
        for ord in fileteredOredrs:
            ord.state_of_delivery = 'Complete_Handle'
            ord.save(update_fields=['state_of_delivery'])
        return
    if set_is_closed:
        for ord in fileteredOredrs:
            ord.isClosed = True
            ord.isComplete = True
            if ord.state_of_delivery != 'Complete':
                ord.state_of_delivery = 'Complete_Handle'
            ord.save(update_fields=['isClosed', 'isComplete', 'state_of_delivery'])
        return


    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Preorders_List_{datetime.datetime.now().strftime('%d.%m.%Y  %H:%M')}.xlsx"
    wb = Workbook(response, {'in_memory': True})
    for preorder in fileteredOredrs:
        preorder_render_to_xls_by_preorder(response, preorder, wb, all_items)
    wb.close()
    return response




def preorder_render_to_xls_by_preorder(response, order: PreOrder, wb: Workbook, all_items: bool):
    order_id = order.id
    supplies_in_order_all = order.supplyinpreorder_set.all()
    supplies_in_order = []
    if all_items:
        supplies_in_order = supplies_in_order_all
    else:
        for sup in supplies_in_order_all:
            count_in_order = sup.count_in_order if sup.count_in_order is not None else 0
            count_in_order_current = sup.count_in_order_current if sup.count_in_order_current is not None else 0
            booked_count = sup.get_booked_count() if sup.get_booked_count() is not None else 0
            if count_in_order - count_in_order_current - booked_count > 0:
                supplies_in_order.append(sup)
    row_num = 4
    init_row_num = row_num


    ws = wb.add_worksheet(f'Order №{order_id}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)
    if all_items:
        columns_table = [{'header': '№'},
                     {'header': 'Name'},
                     {'header': 'Category'},
                     {'header': 'Package / Tests'},
                     {'header': 'REF'},
                     {'header': 'SMN code'},
                     {'header': 'Count'},
                     # {'header': 'Index'}
                     ]
    else:
        columns_table = [{'header': '№'},
                     {'header': 'Name'},
                     {'header': 'Category'},
                     {'header': 'Package / Tests'},
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
    ws.set_column(2, 5, 20)
    ws.set_column(5, 6, 15)
    # ws.set_column(8, 8, 5)

    ws.add_table(row_num, 0, len(supplies_in_order) + row_num, len(columns_table) - 1, {'columns': columns_table})

    if order.comment:
        ws.write(1, 0, f'Коммент.: {order.comment}', format)
        ws.write(2, 0, f'Всього: {len(supplies_in_order)} шт.', format)
    else:
        ws.write(1, 0, f'Всього: {len(supplies_in_order)} шт.', format)



    for row in supplies_in_order:
        row_num += 1
        name = ''
        ref = ''
        smn = ''
        category = ''
        pckg_and_tests = ''
        if row.generalSupply:
            if row.generalSupply.name:
                name = row.generalSupply.name
            if row.generalSupply.ref:
                ref = row.generalSupply.ref
            if row.generalSupply.SMN_code:
                smn = row.generalSupply.SMN_code
            if row.generalSupply.category:
                category = row.generalSupply.category
            if row.generalSupply.package_and_tests:
                pckg_and_tests = row.generalSupply.package_and_tests

        count_in_order = row.count_in_order
        current_delivery_count = row.count_in_order_current
        if all_items:
            count_borg = count_in_order
        else:
            count_borg = row.count_in_order - row.count_in_order_current - row.get_booked_count()
        date_expired = ''

        val_row = [name, category, pckg_and_tests, ref, smn, count_borg]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - init_row_num)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)
def render_to_xls(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related(
            'place',
            'place__city_ref',
            'userCreated',
            'userSent',
            'for_preorder',
        ).prefetch_related(
            'related_preorders',
            'npdeliverycreateddetailinfo_set',
            'statusnpparselfromdoucmentid_set',
        ),
        pk=order_id,
    )
    supplies_qs = order.supplyinorder_set.select_related(
        'generalSupply',
        'generalSupply__category',
    )
    supply_groups = _group_order_supplies_for_display(supplies_qs)
    total_supply_rows = sum(len(g['items']) for g in supply_groups)
    place_city = _order_detail_xls_place_city(order.place)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = (
        f"attachment; filename=Order-{order_id}-{order.place.name}-{place_city}.xlsx"
    )

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet(f'№{order_id}')

    columns_table = ['№', 'Назва товару', 'Пакування / Тести', 'Категорія', 'REF', 'SMN Code', 'LOT', 'К-ть', 'Тер.прид.']

    row_num = _write_order_detail_xls_header_block(ws, wb, order, total_supply_rows)

    header_format = wb.add_format({
        'bold': True,
        'font_size': 11,
        'font_color': '#FFFFFF',
        'bg_color': '#4F6D9A',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1,
        'border_color': '#3D5678',
    })
    for col_num, header in enumerate(columns_table):
        ws.write(row_num, col_num, header, header_format)

    ws.outline_settings(True, False, False, True)
    table_header_row = row_num
    group_formats = _order_detail_xls_data_formats(wb)
    row_num = _write_grouped_order_supplies_to_xls(ws, supply_groups, row_num, group_formats)
    ws.autofilter(table_header_row, 0, row_num, ORDER_DETAIL_XLS_LAST_COL)
    ws.freeze_panes(table_header_row + 1, 0)

    for col_num, width in enumerate(ORDER_DETAIL_XLS_COLUMN_WIDTHS):
        ws.set_column(col_num, col_num, width)
    wb.close()

    return response

def preorder_render_to_xls(request, order_id):
    return generate_list_of_xls_from_preorders_list([order_id])

def preorder_render_to_xls_all_items(request, order_id):
    return generate_list_of_xls_from_preorders_list([order_id], all_items=True)

@login_required(login_url='login')
def devices_render_to_xls(request):
    """
    Export devices to Excel in Ukrainian language (default)
    """
    return _devices_render_to_xls(request, language='uk')

@login_required(login_url='login')
def devices_render_to_xls_en(request):
    """
    Export devices to Excel in English language
    """
    return _devices_render_to_xls(request, language='en')

def _devices_render_to_xls(request, language='uk'):
    """
    Helper function to export devices to Excel in the specified language
    """
    devices = devices_list_queryset(Device.objects.all())

    # Define language-specific strings
    if language == 'en':
        filename = "Devices-List.xlsx"
        worksheet_name = "Devices-List"
        title = "Devices List DIAMEDIX Ukraine"
        headers = ['№', 'Name', 'S/N', 'Customer City', 'Customer Name', 'Date Installed']
    else:  # Ukrainian (default)
        filename = "Список-Пристроїв.xlsx"
        worksheet_name = "Список пристроїв"
        title = "Список пристроїв DIAMEDIX Ukraine"
        headers = ['№', 'Назва', 'Серійний номер', 'Місто клієнта', 'Назва клієнта', 'Дата встановлення']

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename={filename}"

    row_num = 3

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet(worksheet_name)
    format = wb.add_format({'bold': True})
    format.set_font_size(24)

    columns_table = [{'header': header} for header in headers]

    ws.write(0, 0, title, format)

    format = wb.add_format({'text_wrap': True})
    format.set_font_size(22)
    
    # Translate customer city names if English version
    translator = None
    if language == 'en':
        try:
            translator = Translator()
        except Exception:
            translator = None
    
    for row in devices:
        row_num += 1
        name = row.general_device.name
        
        # Get customer name - use English version if available for English language
        if language == 'en':
            customer = row.in_place.get_place_name_en()
        else:
            customer = row.in_place.name
        
        # Translate city name for English version
        customer_city = row.in_place.city
        if language == 'en' and translator and customer_city:
            try:
                customer_city = translator.translate(customer_city, src='uk', dest='en').text
            except Exception:
                pass  # Use original if translation fails
        
        serial_number = ''
        if row.serial_number:
            serial_number = row.serial_number
        date_installed = ''
        if row.date_installed:
            date_installed = row.date_installed.strftime("%d-%m-%Y")

        val_row = [name, serial_number, customer_city, customer, date_installed]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3, format)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 30)
    ws.set_column(2, 2, 20)
    ws.set_column(3, 3, 25)
    ws.set_column(4, 4, 65)
    ws.set_column(5, 5, 20)

    ws.add_table(3, 0, devices.count() + 3, len(columns_table) - 1, {'columns': columns_table})
    wb.close()

    return response
def _supply_in_order_xls_product_fields(row):
    name = ref = smn = category = packtests = ''
    if row.generalSupply:
        name = row.generalSupply.name or ''
        ref = row.generalSupply.ref or ''
        smn = row.generalSupply.SMN_code or ''
        if row.generalSupply.category:
            category = row.generalSupply.category.name
        packtests = row.generalSupply.package_and_tests or ''
    else:
        name = row.internalName or '—'
        ref = row.internalRef or ''
    return name, packtests, category, ref, smn


def _supply_in_order_xls_lot_fields(row):
    lot = row.lot or ''
    count = row.count_in_order
    date_expired = row.date_expired.strftime("%d-%m-%Y") if row.date_expired else ''
    return lot, count, date_expired


def _selected_supply_xls_product_fields(supply):
    name = ref = smn = category = packtests = ''
    if supply.general_supply:
        general_supply = supply.general_supply
        name = general_supply.name or ''
        ref = general_supply.ref or ''
        smn = general_supply.SMN_code or ''
        if general_supply.category:
            category = general_supply.category.name
        packtests = general_supply.package_and_tests or ''
    else:
        name = supply.name or '—'
        ref = supply.ref or ''
    return name, packtests, category, ref, smn


def _selected_supply_xls_lot_fields(supply):
    lot = supply.supplyLot or ''
    count = supply.count
    date_expired = supply.expiredDate.strftime("%d-%m-%Y") if supply.expiredDate else ''
    return lot, count, date_expired


def _group_selected_supplies_for_display(supplies_list):
    """Групує агреговані Supply за general_supply для вкладеного відображення LOT."""
    buckets = OrderedDict()
    for item in sorted(
        supplies_list,
        key=lambda supply: (
            supply.general_supply.category_id if supply.general_supply and supply.general_supply.category_id else 0,
            (supply.general_supply.name if supply.general_supply else None) or supply.name or '',
        ),
    ):
        key = item.general_supply_id if item.general_supply_id else -item.pk
        buckets.setdefault(key, []).append(item)

    return [{'counter': idx, 'items': items} for idx, items in enumerate(buckets.values(), start=1)]


ORDER_DETAIL_XLS_COLUMN_WIDTHS = (5, 35, 15, 15, 20, 20, 15, 5, 12)
ORDER_DETAIL_XLS_LAST_COL = len(ORDER_DETAIL_XLS_COLUMN_WIDTHS) - 1


def _order_detail_xls_table_width_chars():
    return sum(ORDER_DETAIL_XLS_COLUMN_WIDTHS)


def _order_detail_xls_user_name(user):
    if not user:
        return ''
    return ' '.join(part for part in (user.first_name or '', user.last_name or '') if part).strip()


def _order_detail_xls_place_city(place):
    if not place:
        return ''
    if place.city_ref_id and place.city_ref:
        return place.city_ref.name
    return place.city or ''


def _write_order_detail_xls_merged_line(ws, row_num, text, cell_format, last_col=ORDER_DETAIL_XLS_LAST_COL):
    ws.merge_range(row_num, 0, row_num, last_col, text, cell_format)
    ws.set_row(row_num, _order_detail_xls_row_height((text, _order_detail_xls_table_width_chars())))
    return row_num + 1


def _order_detail_xls_header_lines(order, total_supply_rows):
    lines = []
    place = order.place
    city = _order_detail_xls_place_city(place)
    place_name = place.name if place else ''
    created = order.dateCreated.strftime('%d.%m.%Y') if order.dateCreated else ''
    lines.append(('title', f'Замов. №{order.id} — {place_name}, {city} від {created}'))

    creator = _order_detail_xls_user_name(order.userCreated)
    if creator:
        lines.append(('info', f'Створив: {creator}'))

    if order.isMerged:
        lines.append(('info', "Об'єднане замовлення"))

    if order.for_preorder_id:
        preorder = order.for_preorder
        preorder_text = f'Передзамовлення: №{preorder.id}'
        if preorder.comment:
            preorder_text += f' ({preorder.comment})'
        lines.append(('info', preorder_text))

    related_preorders = list(order.related_preorders.all())
    if related_preorders:
        related_ids = ', '.join(f'№{preorder.id}' for preorder in related_preorders)
        lines.append(('info', f"Пов'язані передзамовлення: {related_ids}"))

    if order.isComplete:
        status = 'Статус: виконано'
        if order.dateSent:
            status += f' ({order.dateSent.strftime("%d.%m.%Y")})'
        lines.append(('info', status))
        sender = _order_detail_xls_user_name(order.userSent)
        if sender:
            lines.append(('info', f'Відправив: {sender}'))
    else:
        lines.append(('info', 'Статус: в очікуванні'))
        if order.dateToSend:
            lines.append(('info', f'Дата відправки: {order.dateToSend.strftime("%d.%m.%Y")}'))

    if order.comment:
        lines.append(('info', f'Коментар: {order.comment}'))

    lines.append(('info', f'Всього позицій: {total_supply_rows} шт.'))

    np_created = list(order.npdeliverycreateddetailinfo_set.all())
    np_status = list(order.statusnpparselfromdoucmentid_set.all())
    if np_created or np_status:
        lines.append(('blank', ''))

    for delivery in np_created:
        lines.append(('np', f'Номер накладної НП: {delivery.document_id}'))
        if delivery.recipient_address:
            lines.append(('np', f'Адреса отримувача: {delivery.recipient_address}'))
        if delivery.recipient_worker:
            lines.append(('np', f'Контактна особа-отримувач: {delivery.recipient_worker}'))
        if delivery.estimated_time_delivery:
            lines.append(('np', f'Розрахункова дата доставки: {delivery.estimated_time_delivery}'))
        if delivery.cost_on_site is not None:
            lines.append(('np', f'Вартість доставки: {delivery.cost_on_site} грн.'))

    for index, document in enumerate(np_status):
        if index > 0:
            lines.append(('blank', ''))
        lines.append(('np', f'Накладна НП №{document.docNumber} — {document.status_desc}'))
        recipient = ', '.join(filter(None, [
            document.counterpartyRecipientDescription,
            document.recipientAddress,
            document.recipientFullNameEW,
        ]))
        if recipient:
            lines.append(('np', f'Отримувач: {recipient}'))
        if document.phoneRecipient:
            lines.append(('np', f'Тел.: {document.phoneRecipient}'))
        if document.warehouseSender:
            lines.append(('np', f'Відправник: {document.warehouseSender}'))
        delivery_dates = ', '.join(filter(None, [
            f'план: {document.scheduledDeliveryDate}' if document.scheduledDeliveryDate else None,
            f'факт: {document.actualDeliveryDate}' if document.actualDeliveryDate else None,
            f'отримано: {document.recipientDateTime}' if document.recipientDateTime else None,
        ]))
        if delivery_dates:
            lines.append(('np', f'Дати доставки: {delivery_dates}'))
        weight = ', '.join(filter(None, [
            f"об'ємна {document.documentWeight}" if document.documentWeight else None,
            f'фактична {document.factualWeight}' if document.factualWeight else None,
        ]))
        if weight:
            lines.append(('np', f'Вага: {weight}'))
        cost_parts = []
        if document.documentCost:
            cost_parts.append(f'{document.documentCost} грн.')
        if document.paymentMethod:
            cost_parts.append(f'оплата: {document.paymentMethod}')
        if document.payerType:
            cost_parts.append(f'платник: {document.payerType}')
        if cost_parts:
            lines.append(('np', 'Вартість доставки: ' + ', '.join(cost_parts)))
        if document.seatsAmount:
            lines.append(('np', f'Кількість місць: {document.seatsAmount}'))
        if document.announcedPrice:
            lines.append(('np', f'Оціночна вартість: {document.announcedPrice} грн.'))
        if document.cargoDescriptionString:
            lines.append(('np', f'Опис: {document.cargoDescriptionString}'))

    return lines


def _write_xls_meta_header_block(ws, wb, lines, start_row=0):
    title_format = wb.add_format({'bold': True, 'font_size': 16, 'text_wrap': True, 'valign': 'top'})
    info_format = wb.add_format({'font_size': 14, 'text_wrap': True, 'valign': 'top'})
    np_format = wb.add_format({'font_size': 13, 'text_wrap': True, 'valign': 'top'})
    blank_format = wb.add_format({'font_size': 13, 'text_wrap': True})
    format_by_kind = {'title': title_format, 'info': info_format, 'np': np_format, 'blank': blank_format}

    row_num = start_row
    for kind, text in lines:
        if kind == 'blank':
            ws.merge_range(row_num, 0, row_num, ORDER_DETAIL_XLS_LAST_COL, '', blank_format)
            ws.set_row(row_num, 8)
            row_num += 1
            continue
        row_num = _write_order_detail_xls_merged_line(ws, row_num, text, format_by_kind[kind])
    return row_num


def _write_order_detail_xls_header_block(ws, wb, order, total_supply_rows):
    return _write_xls_meta_header_block(ws, wb, _order_detail_xls_header_lines(order, total_supply_rows))


def _order_detail_xls_data_formats(wb):
    base = {
        'font_size': 14,
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1,
        'border_color': '#D4DCE8',
    }
    return (
        wb.add_format({**base, 'bg_color': '#FFFFFF'}),
        wb.add_format({**base, 'bg_color': '#E9EEF5'}),
    )


def _order_detail_xls_row_height(*text_width_pairs, min_height=15, line_height=15):
    """Оцінка висоти рядка для переносу тексту в комірці (text, width_chars)."""
    lines = 1
    for text, width in text_width_pairs:
        if not text:
            continue
        width = max(width, 1)
        for part in str(text).splitlines():
            lines = max(lines, max(1, (len(part) + width - 1) // width))
    return min(max(lines * line_height, min_height), 150)


def _order_detail_xls_set_group_row_heights(ws, group_start, group_end, name, packtests, category, ref, smn):
    wrap_height = _order_detail_xls_row_height(
        (name, 35),
        (packtests, 15),
        (category, 15),
        (ref, 20),
        (smn, 20),
    )
    row_count = group_end - group_start + 1
    per_row = max(wrap_height / row_count, 15)
    for row in range(group_start, group_end + 1):
        ws.set_row(row, per_row)


def _write_grouped_supply_rows_to_xls(ws, supply_groups, row_num, group_formats, product_fields_fn, lot_fields_fn):
    """Один товар — один №/назва; кожен LOT — окремий рядок з однаковим фоном групи."""
    fmt_a, fmt_b = group_formats

    for group_idx, group in enumerate(supply_groups):
        cell_format = fmt_a if group_idx % 2 == 0 else fmt_b
        name, packtests, category, ref, smn = product_fields_fn(group['items'][0])
        items = group['items']
        multi_lot = len(items) > 1
        group_start = row_num + 1
        group_end = row_num + len(items)

        if multi_lot:
            ws.merge_range(group_start, 0, group_end, 0, group['counter'], cell_format)
            ws.merge_range(group_start, 1, group_end, 1, name, cell_format)
            ws.merge_range(group_start, 2, group_end, 2, packtests, cell_format)
            ws.merge_range(group_start, 3, group_end, 3, category, cell_format)
            ws.merge_range(group_start, 4, group_end, 4, ref, cell_format)
            ws.merge_range(group_start, 5, group_end, 5, smn, cell_format)

        for idx, row in enumerate(items):
            row_num += 1
            lot, count, date_expired = lot_fields_fn(row)

            if not multi_lot:
                ws.write(row_num, 0, group['counter'], cell_format)
                ws.write(row_num, 1, name, cell_format)
                ws.write(row_num, 2, packtests, cell_format)
                ws.write(row_num, 3, category, cell_format)
                ws.write(row_num, 4, ref, cell_format)
                ws.write(row_num, 5, smn, cell_format)

            ws.write(row_num, 6, str(lot), cell_format)
            ws.write(row_num, 7, count, cell_format)
            ws.write(row_num, 8, str(date_expired), cell_format)

            if multi_lot and idx > 0:
                ws.set_row(row_num, None, None, {'level': 1})

        _order_detail_xls_set_group_row_heights(ws, group_start, group_end, name, packtests, category, ref, smn)

    return row_num


def _write_grouped_order_supplies_to_xls(ws, supply_groups, row_num, group_formats):
    return _write_grouped_supply_rows_to_xls(
        ws,
        supply_groups,
        row_num,
        group_formats,
        _supply_in_order_xls_product_fields,
        _supply_in_order_xls_lot_fields,
    )
def import_general_supplies_from_excel(request):
    if request.method == 'POST':
        if 'excel_file' in request.FILES:
            try:
                excel_file = request.FILES['excel_file']
                # Get column mappings from form
                name_col = int(request.POST.get('name_column', 0))
                ref_col = request.POST.get('ref_column') or None
                smn_code_col = request.POST.get('smn_code_column') or None
                package_tests_col = request.POST.get('package_tests_column')
                category_id = request.POST.get('category')
                
                # Read excel file
                import pandas as pd
                df = pd.read_excel(excel_file, header=None)  # Add header=None to read first row as data
                
                success_count = 0
                update_count = 0
                error_count = 0
                error_messages = []
                
                # Get the selected category
                category = Category.objects.get(id=category_id)
                
                for index, row in df.iterrows():
                    try:
                        # Prepare data dictionary with required fields
                        supply_data = {
                            'name': row[name_col],
                            'category': category
                        }
                        
                        # Add optional fields only if they exist and are not empty
                        if ref_col and ref_col.strip() != '':
                            ref_col_num = int(ref_col)
                            if pd.notna(row[ref_col_num]):
                                supply_data['ref'] = str(row[ref_col_num])
                            
                        if smn_code_col and smn_code_col.strip() != '':
                            smn_code_col_num = int(smn_code_col)
                            if pd.notna(row[smn_code_col_num]):
                                supply_data['SMN_code'] = str(row[smn_code_col_num])
                            
                        if package_tests_col and package_tests_col.strip() != '':
                            package_tests_col_num = int(package_tests_col)
                            if pd.notna(row[package_tests_col_num]):
                                supply_data['package_and_tests'] = str(row[package_tests_col_num])
                        
                        # Check if GeneralSupply with this name exists
                        existing_supply = GeneralSupply.objects.filter(name=row[name_col], category=category).first()
                        
                        if existing_supply:
                            # Update existing supply
                            for key, value in supply_data.items():
                                setattr(existing_supply, key, value)
                            existing_supply.save()
                            update_count += 1
                        else:
                            # Create new supply
                            general_supply = GeneralSupply(**supply_data)
                            general_supply.save()
                            success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        error_messages.append(f"Row {index + 1}: {str(e)}")
                        print(f"Error on row {index}: {str(e)}")
                        continue

                if success_count > 0 or update_count > 0:
                    message = []
                    if success_count > 0:
                        message.append(f'Created {success_count} new items')
                    if update_count > 0:
                        message.append(f'Updated {update_count} existing items')
                    messages.success(request, ' | '.join(message))
                if error_count > 0:
                    messages.warning(request, f'Failed to process {error_count} items. Check the console for details.')
                return redirect('import_general_supplies_from_excel')
                
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
                return redirect('import_general_supplies_from_excel')
    
    # Get all categories for the dropdown
    categories = Category.objects.all().order_by('name')
    
    return render(request, 'supplies/supplies/import_general_supplies.html', {
        'title': 'Import General Supplies',
        'categories': categories
    })
    
    
@login_required(login_url='login')
@transaction.atomic
def import_new_preorder_from_excel(request):
    isClient = request.user.isClient() and not request.user.is_staff
    cities = City.objects.all()
    place = None
    title = 'Імпорт нових передзамовлень'
    if isClient:
        place = Place.objects.get(user=request.user)
        title = f'Імпорт нових передзамовлень для {place.get_place_name()}'
    
    
    if request.method == 'POST':
        if 'excel_file' in request.FILES:
            try:
                excel_file = request.FILES['excel_file']
                ref_col = request.POST.get('ref_column') or None
                smn_code_col = request.POST.get('smn_code_column') or None
                count_col = request.POST.get('count_column')
                print("ref_col: ", ref_col)
                print("smn_code_col: ", smn_code_col)
                print("count_col: ", count_col)
                if ref_col:
                    ref_col = int(ref_col.strip()) - 1
                    print("ref_col: ", ref_col)
                if smn_code_col:
                    smn_code_col = int(smn_code_col.strip()) - 1
                    print("smn_code_col: ", smn_code_col)
                if count_col:
                    count_col = int(count_col.strip()) - 1
                    print("count_col: ", count_col)
                # Read excel file
                import pandas as pd
                df = pd.read_excel(excel_file, header=None) 
                
                success_count = 0
                update_count = 0
                error_count = 0
                error_messages = []
                failed_rows = []
                message = []
                if not isClient:
                    place_id = request.POST.get('place_id')
                    place = Place.objects.get(id=place_id)
                dateSent = timezone.now().date()
                sups_dict = {}
                
                for index, row in df.iterrows():
                    ref = None
                    smn_code = None
                    if ref_col is not None:
                        ref = str(row[ref_col]).strip()
                    if smn_code_col is not None:
                        smn_code = str(row[smn_code_col]).strip().split('.')[0] if pd.notna(row[smn_code_col]) else None
                        
                    try:
                        general_supply = None
                        print("ref: ", ref)
                        print("smn_code: ", smn_code)
                        if ref and smn_code:
                            print("---1---")
                            try:
                                general_supply = GeneralSupply.objects.get(
                                    ref=ref,
                                    SMN_code=smn_code
                                )
                                print("---1exists---")
                            except GeneralSupply.DoesNotExist:
                                pass
                        
                        if ref and not general_supply:
                            print("---2---")
                            try:
                                general_supply = GeneralSupply.objects.get(ref=ref)
                                print("---2exists---")
                            except GeneralSupply.DoesNotExist:
                                pass
                                
                        # If not found by ref, try SMN_code
                        if smn_code and not general_supply:
                            print("---3---")
                            try:
                                general_supply = GeneralSupply.objects.get(SMN_code=smn_code)
                                print("---3exists---")
                            except GeneralSupply.DoesNotExist:
                                pass
                              
                        if not general_supply:
                            error_count += 1
                            error_messages.append(f"Row {index + 1}: Could not find GeneralSupply with provided ref, SMN_code, or name")
                            failed_rows.append({
                                    'row': index + 1,  # Excel rows start at 1, and we have header
                                    'ref': ref,
                                    'smn_code': smn_code,
                                    'reason': 'Товар не знайдено'
                                })
                            continue
                        else:
                            count_in_order_row = row[count_col]
                            try:
                                # First try to clean the string and extract only digits
                                if isinstance(count_in_order_row, str):
                                    # Remove any non-digit characters except decimal point
                                    cleaned_str = ''.join(c for c in count_in_order_row if c.isdigit() or c == '.')
                                    if cleaned_str:
                                        count_in_order_row = int(float(cleaned_str))
                                    else:
                                        raise ValueError("No valid number found")
                                elif isinstance(count_in_order_row, (int, float)):
                                    count_in_order_row = int(float(count_in_order_row))
                                else:
                                    raise ValueError("Invalid data type")
                                
                                if count_in_order_row <= 0:
                                    raise ValueError("Count must be positive")
                                    
                                if sups_dict.get(general_supply):
                                    sups_dict[general_supply] += count_in_order_row
                                else:
                                    sups_dict[general_supply] = count_in_order_row
                                    
                            except (ValueError, TypeError) as e:
                                error_count += 1
                                error_messages.append(f"Row {index + 1}: Неможливо визначити кількість")
                                failed_rows.append({
                                    'row': index + 1,
                                    'ref': ref,
                                    'smn_code': smn_code,
                                    'reason': f'Неможливо визначити кількість! Error: {str(e)}'
                                })
                            

                    except Exception as e:
                        print("--4--")
                        print(e)
                        error_count += 1
                        error_messages.append(f"Row {index + 1}: {str(e)}")
                        failed_rows.append({
                                    'row': index + 1,  # Excel rows start at 1, and we have header
                                    'ref': ref,
                                    'smn_code': smn_code,
                                    'reason': 'Помилка при імпорті. Error: ' + str(e)
                                })
                        continue
                if len(sups_dict) > 0:
                    preorder = PreOrder(userCreated=request.user, place=place, dateSent=dateSent,
                                    isComplete=True, isPreorder=True, state_of_delivery='accepted_by_customer')
                    preorder.save()    
                    message.append(f'Створено передзамовлення №{preorder.id} для {place.get_place_name()}')
                    for general_supply, count_in_order in sups_dict.items():
                        supply_in_preorder = SupplyInPreorder(
                                    generalSupply=general_supply,
                                    count_in_order=count_in_order,
                                    supply_for_order=preorder
                                )
                        success_count += 1 
                        supply_in_preorder.save()
                else:
                    message.append(f'Не вдалося створити передзамовлення для {place.get_place_name()} тому що не було знайдено жодного товару')

                if success_count > 0 or update_count > 0:
                    
                    if success_count > 0:
                        message.append(f'Додано успішно {success_count} позицій')
                    messages.success(request, '\n'.join(message))
                if error_count > 0:
                    error_details = "\n".join([
                        f"Row {row['row']}: Ref: {row['ref']}, SMN: {row['smn_code']} - {row['reason']}"
                        for row in failed_rows
                    ])
                    messages.warning(
                        request,
                        f'Не вдалося обробити {error_count} позицій:\n{error_details}'
                    )
                return redirect('import_new_preorder_from_excel')
                
            except Exception as e:
                error_message = f'Помилка при імпорті: {str(e)}'
                if isinstance(e, (ValueError, TypeError)):
                    error_message = f'Помилка при обробці даних: {str(e)}'
                elif isinstance(e, FileNotFoundError):
                    error_message = 'Файл не знайдено'
                elif isinstance(e, pd.errors.EmptyDataError):
                    error_message = 'Excel файл порожній'
                elif isinstance(e, pd.errors.ParserError):
                    error_message = 'Помилка при читанні Excel файлу. Перевірте формат файлу'
                print(f"Debug - Exception type: {type(e)}, Message: {str(e)}")  # Add debug logging
                messages.error(request, error_message)
                return redirect('import_new_preorder_from_excel')
            
    return render(request, 'supplies/supplies/import_new_preorder.html', {
        'title': title,
        'cities': cities,
        'isClient': isClient
    })
def analytics_report_to_xls(request, place_id):
    place = get_object_or_404(Place, id=place_id)
    analytics = PreorderAnalytics(place)
    report = analytics.get_analytics_report()
    
    # Отримуємо всі передзамовлення для цього місця
    preorders = PreOrder.objects.filter(place=place).order_by('-dateCreated')
    
    # Отримуємо всі товари з передзамовлень, згруповані за generalSupply
    preorder_items = SupplyInPreorder.objects.filter(
        supply_for_order__in=preorders
    ).values(
        'generalSupply',
        'generalSupply__name',
        'generalSupply__package_and_tests',
        'generalSupply__category__name'
    ).annotate(
        total_quantity=Sum('count_in_order'),
        last_order_date=Max('supply_for_order__dateCreated')
    ).order_by('-total_quantity')
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Analytics-{place.name}-{place.city}.xlsx"
    
    wb = Workbook(response, {'in_memory': True})
    
    # Create Summary worksheet
    ws_summary = wb.add_worksheet('Загальна статистика')
    format_title = wb.add_format({'bold': True, 'font_size': 18})
    format_header = wb.add_format({'bold': True, 'font_size': 16})
    format_normal = wb.add_format({'font_size': 14})
    
    ws_summary.write(0, 0, f'Аналітика передзамовлень для {place.name}, {place.city_ref.name}', format_title)
    ws_summary.write(2, 0, 'Загальна статистика', format_header)
    ws_summary.write(3, 0, 'Всього передзамовлень:', format_normal)
    ws_summary.write(3, 1, report['total_orders'], format_normal)
    ws_summary.write(4, 0, 'Останнє передзамовлення:', format_normal)
    ws_summary.write(4, 1, report['last_order_date'].strftime("%d-%m-%Y") if report['last_order_date'] else '', format_normal)
    ws_summary.write(5, 0, 'Середня частота (днів):', format_normal)
    ws_summary.write(5, 1, report['order_frequency'] or 0, format_normal)
    
    ws_summary.write(7, 0, 'Прогноз наступного передзамовлення', format_header)
    ws_summary.write(8, 0, 'Очікувана дата:', format_normal)
    ws_summary.write(8, 1, report['next_predicted_order'].strftime("%d-%m-%Y") if report['next_predicted_order'] else '', format_normal)
    
    ws_summary.set_column(0, 0, 30)
    ws_summary.set_column(1, 1, 20)
    
    # Create Recommendations worksheet
    ws_recommendations = wb.add_worksheet('Рекомендовані товари')
    
    # Write headers
    headers = [
        {'header': '№'},
        {'header': 'Назва товару'},
        {'header': 'Пакування / Тести'},
        {'header': 'Категорія'},
        {'header': 'Рекомендована кількість'},
        {'header': 'Середня кількість'},
        {'header': 'Загальна кількість'},
        {'header': 'Кількість замовлень'}
    ]
    
    # Write data
    row = 1
    for suggestion in report['suggestions']:
        product = suggestion['product']
        ws_recommendations.write(row, 0, row, format_normal)
        ws_recommendations.write(row, 1, product.name, format_normal)
        ws_recommendations.write(row, 2, product.package_and_tests or '', format_normal)
        ws_recommendations.write(row, 3, product.category.name if product.category else '', format_normal)
        ws_recommendations.write(row, 4, suggestion['suggested_quantity'], format_normal)
        ws_recommendations.write(row, 5, int(suggestion['avg_quantity']), format_normal)  # Convert to integer
        ws_recommendations.write(row, 6, suggestion['total_quantity'], format_normal)
        ws_recommendations.write(row, 7, suggestion['total_orders'], format_normal)
        row += 1
    
    # Add table with styling
    if report['suggestions']:
        ws_recommendations.add_table(0, 0, len(report['suggestions']), len(headers) - 1, {
            'columns': headers,
            'style': 'Table Style Medium 2',
            'first_column': True
        })
    
    # Set column widths
    ws_recommendations.set_column(0, 0, 5)   # №
    ws_recommendations.set_column(1, 1, 35)  # Назва товару
    ws_recommendations.set_column(2, 2, 20)  # Пакування / Тести
    ws_recommendations.set_column(3, 3, 15)  # Категорія
    ws_recommendations.set_column(4, 7, 15)  # Numeric columns
    
    # # Create Preorder Items worksheet
    # ws_items = wb.add_worksheet('Товари в передзамовленнях')
    
    # # Write headers
    # item_headers = [
    #     {'header': '№'},
    #     {'header': 'Назва товару'},
    #     {'header': 'Пакування / Тести'},
    #     {'header': 'Категорія'},
    #     {'header': 'Загальна кількість'},
    #     {'header': 'Дата останнього замовлення'}
    # ]
    
    # # Write data
    # row = 1
    # for item in preorder_items:
    #     ws_items.write(row, 0, row, format_normal)
    #     ws_items.write(row, 1, item['generalSupply__name'], format_normal)
    #     ws_items.write(row, 2, item['generalSupply__package_and_tests'] or '', format_normal)
    #     ws_items.write(row, 3, item['generalSupply__category__name'] or '', format_normal)
    #     ws_items.write(row, 4, item['total_quantity'], format_normal)
    #     ws_items.write(row, 5, item['last_order_date'].strftime("%d-%m-%Y") if item['last_order_date'] else '', format_normal)
    #     row += 1
    
    # # Add table with styling
    # if preorder_items:
    #     ws_items.add_table(0, 0, len(preorder_items), len(item_headers) - 1, {
    #         'columns': item_headers,
    #         'style': 'Table Style Medium 2',
    #         'first_column': True
    #     })
    
    # # Set column widths
    # ws_items.set_column(0, 0, 5)   # №
    # ws_items.set_column(1, 1, 35)  # Назва товару
    # ws_items.set_column(2, 2, 20)  # Пакування / Тести
    # ws_items.set_column(3, 3, 15)  # Категорія
    # ws_items.set_column(4, 4, 15)  # Загальна кількість
    # ws_items.set_column(5, 5, 20)  # Дата останнього замовлення
    
    wb.close()
    return response
def preorder_items_table_to_xls(request, place_id):
    """
    Export preorder items to Excel in Ukrainian language
    """
    return _preorder_items_table_to_xls(request, place_id, language='uk')

@login_required
@allowed_users(allowed_roles=['admin', 'empl'])
def preorder_items_table_to_xls_en(request, place_id):
    """
    Export preorder items to Excel in English language
    """
    return _preorder_items_table_to_xls(request, place_id, language='en')

def _preorder_items_table_to_xls(request, place_id, language='uk'):
    """
    Helper function to export preorder items to Excel in the specified language
    """
    place = get_object_or_404(Place, id=place_id)
    
    # Отримуємо всі передзамовлення для цього місця
    preorders = PreOrder.objects.filter(place=place).order_by('-dateCreated')
    
    # Отримуємо всі товари з передзамовлень, згруповані за generalSupply
    preorder_items = SupplyInPreorder.objects.filter(
        supply_for_order__in=preorders
    ).values(
        'generalSupply',
        'generalSupply__name',
        'generalSupply__ref',
        'generalSupply__SMN_code',
        'generalSupply__package_and_tests',
        'generalSupply__category__name'
    ).annotate(
        total_quantity=Sum('count_in_order'),
        avg_quantity=Avg('count_in_order'),
        last_order_date=Max('supply_for_order__dateCreated'),
        order_count=Count('supply_for_order', distinct=True)  # Count of unique orders for each item
    ).order_by('-total_quantity')
    
    # Define language-specific strings
    if language == 'en':
        # Get translated place name
        place_name = place.get_place_name_en()
        # Sanitize filename - remove special characters and limit length
        safe_place_name = ''.join(c for c in place_name if c.isalnum() or c in ' -_').strip()
        safe_place_name = safe_place_name[:50]  # Limit length to 50 characters
        
        filename = f"PreorderItems-{safe_place_name}.xlsx"
        worksheet_name = "Preorder Items"
        title = f"Preorder Items for: {place_name}"
        city_label = "City:"
        address_label = "Address:"
        type_label = "Type:"
        private_type = "Private Organization"
        public_type = "Public Organization"
        headers = [
            "Item Name", "REF", "SMN Code", "Package/Tests", "Category", 
            "Total Quantity", "Average Quantity", "Number of Orders", "Last Order Date"
        ]
        empty_message = "No items in preorders"
        
        # Translate city name and address for English version
        try:
            translator = Translator()
            city_name = translator.translate(place.city_ref.name, src='uk', dest='en').text
            address = translator.translate(place.address, src='uk', dest='en').text if place.address else ""
        except Exception:
            # If translation fails, use original values
            city_name = place.city_ref.name
            address = place.address or ""
    else:  # Ukrainian (default)
        # Sanitize filename - remove special characters and limit length
        safe_place_name = ''.join(c for c in place.name if c.isalnum() or c in ' -_').strip()
        safe_place_name = safe_place_name[:50]  # Limit length to 50 characters
        
        filename = f"ТовариПередзамовлень-{safe_place_name}.xlsx"
        worksheet_name = "Товари передзамовлень"
        title = f"Товари передзамовлень для: {place.get_place_name()}"
        city_label = "Місто:"
        address_label = "Адреса:"
        type_label = "Тип:"
        private_type = "Приватна організація"
        public_type = "Державна організація"
        headers = [
            "Назва товару", "REF", "SMN code", "Упаковка/тести", "Категорія", 
            "Загальна кількість", "Середня кількість", "Кількість замовлень", "Останнє замовлення"
        ]
        empty_message = "Немає товарів у передзамовленнях"
        city_name = place.city_ref.name
        address = place.address or ""
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename={filename}"
    
    wb = Workbook(response, {'in_memory': True})
    
    # Create worksheet
    ws = wb.add_worksheet(worksheet_name)
    
    # Define formats
    format_title = wb.add_format({'bold': True, 'font_size': 18})
    format_header = wb.add_format({'bold': True, 'font_size': 14, 'bg_color': '#D9E1F2', 'border': 1})
    format_normal = wb.add_format({'font_size': 12})
    format_date = wb.add_format({'font_size': 12, 'num_format': 'dd-mm-yyyy'})
    format_number = wb.add_format({'font_size': 12, 'num_format': '#,##0'})
    
    # Write place information in header
    ws.write(0, 0, title, format_title)
    ws.write(1, 0, f"{city_label} {city_name}", format_normal)
    ws.write(2, 0, f"{address_label} {address}", format_normal)
    ws.write(3, 0, f"{type_label} {private_type if place.isPrivatePlace else public_type}", format_normal)
    
    # Write table headers
    for col, header in enumerate(headers):
        ws.write(6, col, header, format_header)
    
    # Write data
    for row, item in enumerate(preorder_items, start=7):
        ws.write(row, 0, item['generalSupply__name'], format_normal)
        ws.write(row, 1, item['generalSupply__ref'], format_normal)
        ws.write(row, 2, item['generalSupply__SMN_code'], format_normal)
        ws.write(row, 3, item['generalSupply__package_and_tests'], format_normal)
        ws.write(row, 4, item['generalSupply__category__name'], format_normal)
        ws.write(row, 5, item['total_quantity'], format_number)
        ws.write(row, 6, round(item['avg_quantity'], 2), format_number)
        ws.write(row, 7, item['order_count'], format_number)  # Number of orders for this item
        ws.write(row, 8, item['last_order_date'], format_date)
    
    # Set column widths
    ws.set_column(0, 0, 40)  # Name
    ws.set_column(1, 1, 15)  # Ref
    ws.set_column(2, 2, 15)  # SMN code
    ws.set_column(3, 3, 20)  # Package/tests
    ws.set_column(4, 4, 20)  # Category
    ws.set_column(5, 5, 15)  # Total quantity
    ws.set_column(6, 6, 15)  # Avg quantity
    ws.set_column(7, 7, 15)  # Order count
    ws.set_column(8, 8, 15)  # Last order date
    
    wb.close()
    return response
