from celery import shared_task
from celery_progress.backend import ProgressRecorder
from django.http import HttpResponse
from .models import *
from .serializers import *
from .filters import *
from .forms import *
from django.db.models import *
from django.http import HttpResponse
from django.db.models import QuerySet

from time import sleep

@shared_task(bind=True)
def go_to_sleep(self, duration):
    progress_recorder = ProgressRecorder(self)
    for i in range(5):
        sleep(duration)
        progress_recorder.set_progress(i + 1, 5, f'On iteration {i}')
    return HttpResponse("DONE!")

def makeDataUpload_nonCelery(string_data, for_delivery_order, barcode_type):
    i = 0
    result_array = string_data.split()
    total_requests = len(result_array)
    total_sups_delivered = []
    for item in result_array:
        arr_item = item.split(',')
        if barcode_type == 'Siemens':
            if len(arr_item) == 1:
                barcode_str = arr_item[0]
                smn = barcode_str[32:-6]
                smn = smn[-8:]
                lot = barcode_str[18:-25]
                date_expired = barcode_str[23:-17]
                date_expired = date_expired[-6:]
                sup_delivery = create_supply_objects(item, smn, lot, date_expired, for_delivery_order)
                total_sups_delivered.append(sup_delivery)
            elif len(arr_item) == 3:
                smn = arr_item[0]
                lot = arr_item[1]
                date_expired = arr_item[2]
                sup_delivery = create_supply_objects(item, smn, lot, date_expired, for_delivery_order, True)
                total_sups_delivered.append(sup_delivery)
            i += 1
        if barcode_type == 'Alegria':
            if len(arr_item) == 1:
                barcode_str = arr_item[0]
                smn = barcode_str[2:16]
                lot = barcode_str[-7:]
                date_expired = barcode_str[26:-9]
                sup_delivery = create_supply_objects(item, smn, lot, date_expired, for_delivery_order)
                total_sups_delivered.append(sup_delivery)
    return (total_sups_delivered, total_requests)


@shared_task(bind=True)
def makeDataUpload(self, string_data, for_delivery_order, barcode_type):
    i = 0
    result_array = string_data.split()
    total_requests = len(result_array)
    for item in result_array:
        arr_item = item.split(',')
        if barcode_type == 'Siemens':
            if len(arr_item) == 1:
                barcode_str = arr_item[0]
                smn = barcode_str[32:-6]
                smn = smn[-8:]
                lot = barcode_str[18:-25]
                date_expired = barcode_str[23:-17]
                date_expired = date_expired[-6:]
                create_supply_objects(item, smn, lot, date_expired, for_delivery_order)
            elif len(arr_item) == 3:
                smn = arr_item[0]
                lot = arr_item[1]
                date_expired = arr_item[2]
                create_supply_objects(item, smn, lot, date_expired, for_delivery_order, True)
            i += 1
        if barcode_type == 'Alegria':
            if len(arr_item) == 1:
                barcode_str = arr_item[0]
                smn = barcode_str[2:16]
                lot = barcode_str[-7:]
                date_expired = barcode_str[26:-9]
                create_supply_objects(item, smn, lot, date_expired, for_delivery_order)




def create_supply_objects(barcode, smn, lot, date_expired, for_delivery_order, search_by_ref=False):

    try:
        date_expired_date = datetime.datetime.strptime(date_expired, '%y%m%d')
        if search_by_ref:
            gen_sup = GeneralSupply.objects.get(ref=smn)
        else:
            gen_sup = GeneralSupply.objects.get(SMN_code=smn)

        # try:
        #     sup = Supply.objects.get(general_supply=gen_sup,
        #                              supplyLot=lot,
        #                              expiredDate=date_expired_date)
        #     sup.count += 1
        # except:
        #     sup = Supply(name=gen_sup.name,
        #                  general_supply=gen_sup,
        #                  category=gen_sup.category,
        #                  ref=gen_sup.ref,
        #                  supplyLot=lot,
        #                  count=1,
        #                  expiredDate=date_expired_date)
        # sup.save()

        try:
            sup_delivery = for_delivery_order.deliverysupplyincart_set.get(general_supply=gen_sup, supplyLot=lot, expiredDate=date_expired_date)
            sup_delivery.count += 1
        except:
            sup_delivery = DeliverySupplyInCart(
                barcode=barcode,
                SMN_code=smn,
                general_supply=gen_sup,
                supplyLot=lot,
                count=1,
                expiredDate_desc=date_expired_date.strftime('%Y-%m-%d'),
                expiredDate=date_expired_date,
                isRecognized=True,
                delivery_order=for_delivery_order)
        sup_delivery.save()

    except:
        try:
            sup_delivery = for_delivery_order.deliverysupplyincart_set.get(barcode=barcode, delivery_order=for_delivery_order)
            sup_delivery.count += 1
        except:
            sup_delivery = DeliverySupplyInCart(
                barcode=barcode,
                SMN_code=smn,
                supplyLot=lot,
                count=1,
                expiredDate_desc=date_expired,
                delivery_order=for_delivery_order)
        sup_delivery.save()
        
    return sup_delivery    


@shared_task(bind=True)
def gen_sup_and_update_db(self, del_order_id):
    del_order = DeliveryOrder.objects.get(id=del_order_id)
    sup_set = del_order.deliverysupplyincart_set.filter(isRecognized=True)
    progress_recorder = ProgressRecorder(self)
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
        progress_recorder.set_progress(i, total_requests, f'On iteration {i}')
    del_order.isHasBeenSaved = True
    del_order.save()


def gen_sup_and_update_db_async(request, del_order_id):
    del_order = DeliveryOrder.objects.get(id=del_order_id)
    sup_set = del_order.deliverysupplyincart_set.filter(isRecognized=True)
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
    del_order.isHasBeenSaved = True
    del_order.save()

