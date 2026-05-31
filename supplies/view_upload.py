import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django import forms
from .decorators import allowed_users
from .models import *
from .serializers import *
from .filters import *
from .forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.db.models import *
from django.http import HttpResponse
from xlsxwriter.workbook import Workbook
from django.db.models import Sum
from .tasks import (
    makeDataUpload_nonCelery,
    process_single_barcode_scan,
    merge_identifiers_for_delivery_line,
    delivery_line_can_manual_merge,
    apply_merge_identifiers_to_general_supply,
    scan_expiry_for_delivery_line,
)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import threading
from django.core.paginator import Paginator

# @login_required(login_url='login')
# @allowed_users(allowed_roles=['admin'])
# def receive_and_load_new_supplies_order(request):
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def upload_supplies_for_new_delivery_from_js_script(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        barcode_type = data.get('barcode_type', '')
        string_data = data.get('description', '')
        delivery_id = data.get('deliveryOrderId', '')

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
        response_data = threading_create_delivery_async(request, string_data, for_delivery_order, barcode_type, isUpdate)
        return response_data
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

def upload_supplies_for_new_delivery_noncelery(request, delivery_order_id=None):
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
    return render(request, 'supplies/delivery/upload_supplies_for_new_delivery.html', {'form': form, 'title': title, 'delivery_order_id': delivery_order_id})


def _general_supplies_for_live_scan_json():
    return [
        {
            'id': gs.id,
            'name': gs.name or '',
            'ref': gs.ref or '',
            'SMN_code': gs.SMN_code or '',
            'package_and_tests': gs.package_and_tests or '',
            'category': gs.category.name if gs.category_id else '',
        }
        for gs in GeneralSupply.objects.select_related('category').order_by('name')
    ]


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def live_scan_delivery_probe(request, delivery_order_id=None):
    """Тестова сторінка live-скану: приховане поле + пошук по GeneralSupply на клієнті."""
    if delivery_order_id is not None:
        delivery_order = get_object_or_404(DeliveryOrder, pk=delivery_order_id)
        if delivery_order.isHasBeenSaved:
            return redirect('delivery_detail', delivery_id=delivery_order.id)
        title = f'Live-скан · поставка №{delivery_order.id}'
    else:
        delivery_order = None
        title = 'Live-скан · нова поставка'

    return render(
        request,
        'supplies/delivery/live_scan_delivery_probe.html',
        {
            'title': title,
            'delivery_order': delivery_order,
            'general_supplies_json': json.dumps(_general_supplies_for_live_scan_json()),
        },
    )


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def live_scan_delivery_probe_save(request, delivery_order_id=None):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    if delivery_order_id is None:
        delivery_order = DeliveryOrder(from_user=request.user)
        delivery_order.save()
        created = True
    else:
        delivery_order = get_object_or_404(DeliveryOrder, pk=delivery_order_id)
        created = False
    if delivery_order.isHasBeenSaved:
        return JsonResponse({'error': 'Поставка вже закрита'}, status=400)
    data = json.loads(request.body)
    barcode_type = data.get('barcode_type', 'Data Matrix')
    barcode_raw = (data.get('barcode') or '').strip()
    if not barcode_raw:
        if created:
            delivery_order.delete()
        return JsonResponse({'error': 'Порожній штрих-код'}, status=400)
    item = process_single_barcode_scan(barcode_raw, delivery_order, barcode_type)
    if item is None:
        if created:
            delivery_order.delete()
        return JsonResponse({'error': 'Не вдалося розпізнати формат'}, status=400)
    if created:
        _apply_barcode_type_comment(delivery_order, barcode_type)
    recognized = bool(item.general_supply_id)
    payload = {
        'recognized': recognized,
        'line_id': item.id,
        'count': item.count,
        'supply_lot': item.supplyLot or '',
        'smn_code': item.SMN_code or '',
        'barcode': item.barcode or '',
        'expired_date': item.expiredDate.strftime('%Y-%m-%d') if item.expiredDate else (item.expiredDate_desc or ''),
        'delivery_order_id': delivery_order.id,
    }
    if recognized:
        gs = item.general_supply
        payload.update({
            'general_supply_id': gs.id,
            'name': gs.name or '',
            'ref': gs.ref or '',
            'category': gs.category.name if gs.category_id else '',
            'package_and_tests': gs.package_and_tests or '',
        })
    return JsonResponse(payload)


_BARCODE_TYPE_COMMENT_LABELS = {
    'Data Matrix': 'Lifotronic',
    'Siemens': 'Siemens',
}


def _barcode_type_comment_line(barcode_type):
    barcode_type = (barcode_type or '').strip()
    if not barcode_type:
        return None
    return _BARCODE_TYPE_COMMENT_LABELS.get(barcode_type, barcode_type)


def _is_barcode_type_comment_line(line):
    line = line.strip()
    if not line:
        return False
    if line.startswith('Тип штрихкоду:'):
        return True
    return line in _BARCODE_TYPE_COMMENT_LABELS or line in _BARCODE_TYPE_COMMENT_LABELS.values()


def _apply_barcode_type_comment(delivery_order, barcode_type):
    type_line = _barcode_type_comment_line(barcode_type)
    if not type_line:
        return

    existing = (delivery_order.comment or '').strip()
    lines = [
        line for line in existing.splitlines()
        if line.strip() and not _is_barcode_type_comment_line(line)
    ]
    lines.insert(0, type_line)
    delivery_order.comment = '\n'.join(lines)
    delivery_order.save(update_fields=['comment'])


def threading_create_delivery_async(request, string_data, for_delivery_order, barcode_type, isUpdate = False):
    total_sups_delivered, total_requests = makeDataUpload_nonCelery(string_data, for_delivery_order, barcode_type)
    _apply_barcode_type_comment(for_delivery_order, barcode_type)
    delivered_sups_with_general_supply_count = len([x for x in total_sups_delivered if x.general_supply is not None])
    delivered_sups_without_general_supply_count = len([x for x in total_sups_delivered if x.general_supply is None])
    
    message = f'Поставка №{for_delivery_order.id} оновлена успішно!' if isUpdate else f'Поставка №{for_delivery_order.id} створена успішно!\n'
    message += f'\n Всього сторк знайдено: {total_requests} шт.'
    message += f'\n Товарів знайдено: {delivered_sups_with_general_supply_count} шт.'
    message += f'\n Товарів не розпізнано: {delivered_sups_without_general_supply_count} шт.'
    
    response_data = {
            'status': 'success',
            'message': message,
            'delivery_order_id': for_delivery_order.id}
    return JsonResponse(response_data)



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
        comment = (request.POST.get('description') or '').strip()
        del_order.comment = comment or None
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
        return redirect('delivery_detail', delivery_id=delivery_order_id)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def all_deliveries(request):
    deliveries = DeliveryOrder.objects.select_related('from_user').order_by('-id')
    
    paginator = Paginator(deliveries, 20)
    page_number = request.GET.get('page')
    deliveries = paginator.get_page(page_number)
    
    totalCount = deliveries.paginator.count
    title = f'Всі поставки. ({totalCount} шт.)'

    return render(request, 'supplies/delivery/all_deliveries_list.html', {
        'deliveries': deliveries,
        'title': title,
        'totalCount': totalCount
    })

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

def _delivery_cart_line_queryset(delivery_order_id):
    return (
        DeliverySupplyInCart.objects.filter(delivery_order_id=delivery_order_id)
        .select_related(
            'general_supply',
            'general_supply__category',
            'supply',
            'delivery_order',
        )
        .order_by('general_supply__category_id', 'general_supply__name', 'supplyLot', 'id')
    )


def _group_delivery_supplies_for_display(items):
    """Групує рядки поставки за general_supply (як orderDetail)."""
    from collections import OrderedDict

    buckets = OrderedDict()
    for item in items:
        if item.general_supply_id:
            key = ('gs', item.general_supply_id)
        else:
            key = ('unk', item.barcode or '', item.SMN_code or '', item.pk)
        buckets.setdefault(key, []).append(item)
    return [{'counter': idx, 'items': group_items} for idx, group_items in enumerate(buckets.values(), start=1)]


def _delivery_group_for_item(item, *, staging_only=False):
    if item.general_supply_id:
        siblings_qs = _delivery_cart_line_queryset(item.delivery_order_id).filter(
            general_supply_id=item.general_supply_id,
            isRecognized=item.isRecognized,
        )
        if staging_only:
            siblings_qs = siblings_qs.filter(isHandleAdded=True)
        siblings = list(siblings_qs)
    else:
        siblings = [item]
    groups = _group_delivery_supplies_for_display(siblings)
    return groups[0] if groups else None


def _staging_group_header_stub(general_supply):
    """Заголовок групи в staging-таблиці до першого збереженого рядка."""
    class _Header:
        pass

    header = _Header()
    header.general_supply = general_supply
    header.id = 0
    header.barcode = None
    header.SMN_code = None
    return header


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def delivery_detail(request, delivery_id):
    delivery_order = get_object_or_404(
        DeliveryOrder.objects.select_related('from_user'),
        pk=delivery_id,
    )
    supplies = list(_delivery_cart_line_queryset(delivery_id))
    total_count = sum((item.count or 0) for item in supplies)
    # Ручні (isHandleAdded) після reload — у «Знайдено»; секція staging лише для поточної сесії HTMX.
    recognized = [d for d in supplies if d.isRecognized]
    unrecognized = [d for d in supplies if not d.isRecognized]
    recognized_groups = _group_delivery_supplies_for_display(recognized)
    unrecognized_groups = _group_delivery_supplies_for_display(unrecognized)
    staging_groups = []

    form = NewDeliveryForm()
    form.initial['description'] = delivery_order.comment
    form.fields['description'].label = "Коментар"
    comment_widget_attrs = {
        'class': 'form-control form-control-sm delivery-comment-input',
        'placeholder': 'Коментар до поставки',
        'autocomplete': 'off',
    }
    if not delivery_order.isHasBeenSaved:
        comment_widget_attrs['form'] = 'deliveryForm'
    form.fields['description'].widget = forms.TextInput(attrs=comment_widget_attrs)

    user_name = ''
    if delivery_order.from_user:
        user_name = f'{delivery_order.from_user.first_name or ""} {delivery_order.from_user.last_name or ""}'.strip()
    subtitle_parts = []
    if user_name:
        subtitle_parts.append(user_name)
    if delivery_order.date_created:
        subtitle_parts.append(delivery_order.date_created.strftime('%d.%m.%Y'))
    subtitle = ' · '.join(subtitle_parts)

    return render(request, 'supplies/delivery/delivery_detail.html', {
        'title': f'Поставка №{delivery_order.id}',
        'title_icon': 'bi-box-seam',
        'subtitle': subtitle,
        'total_count': total_count,
        'total_group_count': len(recognized_groups) + len(unrecognized_groups),
        'recognized_groups': recognized_groups,
        'unrecognized_groups': unrecognized_groups,
        'staging_groups': staging_groups,
        'delivery_order': delivery_order,
        'form': form,
    })

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def search_results_for_manual_add_in_delivery_order(request, delivery_order_id):
    search_text = (request.POST.get('search') or '').strip()
    results = None
    if search_text:
        results = (
            GeneralSupply.objects.filter(
                Q(name__icontains=search_text)
                | Q(ref__icontains=search_text)
                | Q(SMN_code__icontains=search_text)
            )
            .select_related('category')
            .order_by('name')[:30]
        )
    context = {
        'results': results,
        'delivery_order_id': delivery_order_id,
        'search_attempted': bool(search_text),
    }
    return render(request, 'partials/search_results_for_manual_add_in_delivery_order.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_gen_sup_in_delivery_order_manual_list(request):
    if request.method == 'POST':
        import uuid

        gen_sup_id = request.POST.get('gen_sup_id')
        delivery_order_id = request.POST.get('delivery_order_id')
        create_group = request.POST.get('create_group') == '1'
        gen_sup = GeneralSupply.objects.select_related('category').get(id=gen_sup_id)
        delivery_order = DeliveryOrder.objects.get(id=delivery_order_id)
        try:
            staging_group_count = int(request.POST.get('staging_group_count', 0))
        except (TypeError, ValueError):
            staging_group_count = 0
        context = {
            'item': gen_sup,
            'delivery_order_id': delivery_order_id,
            'delivery_order': delivery_order,
            'draft_uid': uuid.uuid4().hex[:10],
            'group': {'counter': staging_group_count + 1},
        }
        if create_group:
            return render(request, 'partials/delivery/delivery_staging_new_group_row.html', context)
        return render(request, 'partials/delivery/delivery_staging_nested_row_draft.html', context)

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
        del_sup = DeliverySupplyInCart.objects.select_related(
            'general_supply', 'general_supply__category', 'delivery_order',
        ).get(id=deliverySupplyInCart_id)
        gen_sup = del_sup.general_supply

        staging = request.POST.get('context') == 'staging'
        context = {
            'item': gen_sup,
            'delivery_order_id': del_sup.delivery_order_id,
            'del_sup': del_sup,
            'delivery_order': del_sup.delivery_order,
            'line': del_sup,
            'staging': staging,
            'field_errors': {},
        }
        return render(request, 'partials/delivery/delivery_detail_nested_row_edit.html', context)

def _parse_manual_delivery_line_form(request, gen_sup_id):
    """Парсинг полів ручного додавання; повертає (lot, expired_str, expired_date, count, field_errors)."""
    lot = (request.POST.get(f'lot_input_field_{gen_sup_id}') or '').strip()
    expired_str = (request.POST.get(f'expired_input_field_{gen_sup_id}') or '').strip()
    count_raw = (request.POST.get(f'count_input_field_{gen_sup_id}') or '').strip()
    field_errors = {}
    expired_date = None
    count_val = None

    if not expired_str:
        field_errors['expired'] = 'Вкажіть термін (РРРР-ММ-ДД)'
    else:
        try:
            expired_date = datetime.datetime.strptime(expired_str, '%Y-%m-%d').date()
        except ValueError:
            field_errors['expired'] = 'Невірний формат терміну'
    if not count_raw:
        field_errors['count'] = 'Вкажіть кількість'
    else:
        try:
            count_val = int(count_raw)
            if count_val < 1:
                field_errors['count'] = 'Кількість має бути більше 0'
                count_val = None
        except ValueError:
            field_errors['count'] = 'Невірна кількість'
            count_val = None

    return lot, expired_str, expired_date, count_val, field_errors


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def add_gen_sup_in_delivery_order_manual_list_save_action(request):
    if request.method == 'POST':
        import uuid

        delivery_order_id = request.POST.get('delivery_order_id')
        del_sup_id = request.POST.get('del_sup_id')
        if del_sup_id in (None, '', 'None', 'null'):
            del_sup_id = None
        gen_sup_id = request.POST.get('gen_sup_id')
        if not gen_sup_id:
            return HttpResponse('gen_sup_id required', status=400)
        gen_sup = GeneralSupply.objects.get(id=gen_sup_id)
        del_order = DeliveryOrder.objects.get(id=delivery_order_id)
        staging = request.POST.get('save_mode') == 'staging'

        input_lot, input_expired, date_expired_date, input_count, field_errors = _parse_manual_delivery_line_form(
            request, gen_sup_id
        )
        if field_errors:
            if del_sup_id:
                del_sup = DeliverySupplyInCart.objects.select_related(
                    'general_supply', 'general_supply__category', 'delivery_order',
                ).get(id=del_sup_id)
                del_sup.supplyLot = input_lot or None
                del_sup.expiredDate_desc = input_expired
                if request.POST.get(f'count_input_field_{gen_sup_id}', '').strip():
                    try:
                        del_sup.count = int(request.POST.get(f'count_input_field_{gen_sup_id}').strip())
                    except ValueError:
                        pass
                return render(request, 'partials/delivery/delivery_detail_nested_row_edit.html', {
                    'item': gen_sup,
                    'delivery_order_id': delivery_order_id,
                    'del_sup': del_sup,
                    'delivery_order': del_order,
                    'line': del_sup,
                    'staging': staging,
                    'field_errors': field_errors,
                })
            return render(request, 'partials/delivery/delivery_staging_nested_row_draft.html', {
                'item': gen_sup,
                'delivery_order_id': delivery_order_id,
                'delivery_order': del_order,
                'draft_uid': request.POST.get('draft_uid') or uuid.uuid4().hex[:10],
                'field_lot': input_lot,
                'field_expired': input_expired,
                'field_count': request.POST.get(f'count_input_field_{gen_sup_id}', ''),
                'field_errors': field_errors,
            })

        try:
            sup_delivery = DeliverySupplyInCart.objects.get(id=del_sup_id)
            sup_delivery.supplyLot = input_lot or None
            sup_delivery.count = input_count
            sup_delivery.expiredDate = date_expired_date
            sup_delivery.expiredDate_desc = input_expired
        except DeliverySupplyInCart.DoesNotExist:
            sup_delivery = DeliverySupplyInCart(
                general_supply=gen_sup,
                supplyLot=input_lot or None,
                count=input_count,
                expiredDate_desc=input_expired,
                expiredDate=date_expired_date,
                isRecognized=True,
                isHandleAdded=True,
                delivery_order=del_order,
            )
        sup_delivery.save()
        sup_delivery = DeliverySupplyInCart.objects.select_related(
            'general_supply',
            'general_supply__category',
            'delivery_order',
        ).get(pk=sup_delivery.pk)
        return render(request, 'partials/delivery/delivery_detail_nested_row.html', {
            'line': sup_delivery,
            'delivery_order': del_order,
            'staging': staging,
        })


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


def _search_general_supply_by_name(query, *, limit=30):
    search_text = (query or '').strip()
    if not search_text:
        return None
    return (
        GeneralSupply.objects.filter(name__icontains=search_text)
        .select_related('category')
        .order_by('name')[:limit]
    )


def _merge_modal_context(line, **extra):
    scan_smn, scan_ref = merge_identifiers_for_delivery_line(line)
    expiry_date, expiry_iso = scan_expiry_for_delivery_line(line)
    context = {
        'line': line,
        'delivery_order': line.delivery_order,
        'delivery_order_id': line.delivery_order_id,
        'scan_smn': scan_smn,
        'scan_ref': scan_ref,
        'expiry_date': expiry_date,
        'expiry_iso': expiry_iso or '',
        'results': None,
        'search_attempted': False,
    }
    context.update(extra)
    return context


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def unrecognized_line_manual_merge_modal(request, delivery_order_id, line_id):
    line = get_object_or_404(
        DeliverySupplyInCart.objects.select_related('delivery_order'),
        pk=line_id,
        delivery_order_id=delivery_order_id,
        isRecognized=False,
        general_supply__isnull=True,
    )
    if line.delivery_order.isHasBeenSaved:
        return HttpResponse('Поставка закрита', status=400)
    if not delivery_line_can_manual_merge(line):
        return HttpResponse('Немає розпізнаного SMN або REF для привʼязки', status=400)
    return render(
        request,
        'partials/delivery/unrecognized_manual_merge_modal.html',
        _merge_modal_context(line),
    )


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def unrecognized_line_manual_merge_search(request, delivery_order_id, line_id):
    line = get_object_or_404(
        DeliverySupplyInCart,
        pk=line_id,
        delivery_order_id=delivery_order_id,
        isRecognized=False,
        general_supply__isnull=True,
    )
    if line.delivery_order.isHasBeenSaved or not delivery_line_can_manual_merge(line):
        return HttpResponse(status=400)
    search_text = (request.POST.get('search') or '').strip()
    results = _search_general_supply_by_name(search_text) if search_text else None
    return render(request, 'partials/delivery/unrecognized_manual_merge_search_results.html', {
        'results': results,
        'search_attempted': bool(search_text),
        'line_id': line.id,
    })


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def unrecognized_line_manual_merge_save(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    line_id = request.POST.get('line_id')
    gen_sup_id = request.POST.get('gen_sup_id')
    if not line_id or not gen_sup_id:
        return HttpResponse('line_id та gen_sup_id обовʼязкові', status=400)
    line = get_object_or_404(
        DeliverySupplyInCart.objects.select_related('delivery_order'),
        pk=line_id,
        isRecognized=False,
        general_supply__isnull=True,
    )
    if line.delivery_order.isHasBeenSaved:
        return HttpResponse('Поставка закрита', status=400)
    scan_smn, scan_ref = merge_identifiers_for_delivery_line(line)
    if not scan_smn and not scan_ref:
        return HttpResponse('Немає SMN або REF для привʼязки', status=400)
    gen_sup = get_object_or_404(GeneralSupply, pk=gen_sup_id)

    lot = (request.POST.get('lot') or line.supplyLot or '').strip() or None
    count_raw = (request.POST.get('count') or '').strip()
    expired_str = (request.POST.get('expired') or '').strip()
    field_errors = {}

    if not count_raw:
        field_errors['count'] = 'Вкажіть кількість'
        count_val = None
    else:
        try:
            count_val = int(count_raw)
            if count_val < 1:
                field_errors['count'] = 'Кількість має бути більше 0'
                count_val = None
        except ValueError:
            field_errors['count'] = 'Невірна кількість'
            count_val = None

    expiry_date = None
    if not expired_str:
        expiry_date, expired_str = scan_expiry_for_delivery_line(line)
        if not expiry_date:
            field_errors['expired'] = 'Вкажіть термін (РРРР-ММ-ДД)'
    else:
        try:
            expiry_date = datetime.datetime.strptime(expired_str, '%Y-%m-%d').date()
        except ValueError:
            field_errors['expired'] = 'Невірний формат терміну'

    if field_errors:
        return render(
            request,
            'partials/delivery/unrecognized_manual_merge_modal.html',
            _merge_modal_context(
                line,
                selected_gen_sup=gen_sup,
                field_errors=field_errors,
                field_lot=lot or '',
                field_count=count_raw,
                field_expired=expired_str,
            ),
            status=422,
        )

    apply_merge_identifiers_to_general_supply(gen_sup, scan_smn, scan_ref)

    line.general_supply = gen_sup
    line.supplyLot = lot
    line.count = count_val
    line.expiredDate = expiry_date
    line.expiredDate_desc = expired_str
    line.isRecognized = True
    line.save()

    response = HttpResponse(status=200)
    response['HX-Refresh'] = 'true'
    return response