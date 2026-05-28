import datetime
import re

from .models import DeliveryOrder, DeliverySupplyInCart, GeneralSupply, Supply


def makeDataUpload_nonCelery(string_data, for_delivery_order, barcode_type):
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
                sup_delivery = create_supply_objects(
                    item, smn, lot, date_expired, for_delivery_order, search_by_ref=True
                )
                total_sups_delivered.append(sup_delivery)

        elif barcode_type == 'Data Matrix':
            if len(arr_item) == 1:
                barcode_str = arr_item[0]
                work_str = barcode_str

                gtin = ""
                date_expired = ""
                lot = ""
                smn = ""

                if work_str.startswith('01'):
                    gtin = work_str[2:16]
                    work_str = work_str[16:]
                else:
                    match_01 = re.search(r'(?:^|\x1d)01(\d{14})', work_str)
                    if match_01:
                        gtin = match_01.group(1)
                        work_str = work_str.replace(match_01.group(0), '|', 1)

                match_11 = re.search(r'11(\d{6})', work_str)
                if match_11:
                    work_str = work_str.replace(match_11.group(0), '|', 1)

                match_17 = re.search(r'17(\d{6})', work_str)
                if match_17:
                    date_expired = match_17.group(1)
                    work_str = work_str.replace(match_17.group(0), '|', 1)

                match_240 = re.search(r'240([A-Za-z0-9]+?)(?:\x1d|\||422|$)', work_str)
                if match_240:
                    smn_found = match_240.group(1)
                    work_str = work_str.replace(match_240.group(0), '|', 1)
                else:
                    smn_found = ""

                match_10 = re.search(r'10([A-Za-z0-9]+?)(?:\x1d|\||$)', work_str)
                if match_10:
                    lot = match_10.group(1)

                smn = smn_found if smn_found else gtin

                sup_delivery = create_supply_objects(item, smn, lot, date_expired, for_delivery_order)
                total_sups_delivered.append(sup_delivery)

    return (total_sups_delivered, total_requests)


def create_supply_objects(barcode, smn, lot, date_expired, for_delivery_order, search_by_ref=False):
    try:
        date_expired_date = datetime.datetime.strptime(date_expired, '%y%m%d')

        if search_by_ref:
            gen_sup = GeneralSupply.objects.get(ref=smn)
        else:
            gen_sup = GeneralSupply.objects.get(SMN_code=smn)

        try:
            sup_delivery = for_delivery_order.deliverysupplyincart_set.get(
                general_supply=gen_sup, supplyLot=lot, expiredDate=date_expired_date
            )
            sup_delivery.count += 1
        except DeliverySupplyInCart.DoesNotExist:
            sup_delivery = DeliverySupplyInCart(
                barcode=barcode,
                SMN_code=smn,
                general_supply=gen_sup,
                supplyLot=lot,
                count=1,
                expiredDate_desc=date_expired_date.strftime('%Y-%m-%d'),
                expiredDate=date_expired_date,
                isRecognized=True,
                delivery_order=for_delivery_order,
            )
        sup_delivery.save()

    except Exception:
        try:
            sup_delivery = for_delivery_order.deliverysupplyincart_set.get(
                barcode=barcode, delivery_order=for_delivery_order
            )
            sup_delivery.count += 1
        except DeliverySupplyInCart.DoesNotExist:
            sup_delivery = DeliverySupplyInCart(
                barcode=barcode,
                SMN_code=smn,
                supplyLot=lot,
                count=1,
                expiredDate_desc=date_expired,
                delivery_order=for_delivery_order,
            )
        sup_delivery.save()

    return sup_delivery


def gen_sup_and_update_db_async(request, del_order_id):
    del_order = DeliveryOrder.objects.get(id=del_order_id)
    sup_set = del_order.deliverysupplyincart_set.filter(isRecognized=True)
    for item in sup_set:
        if item.general_supply:
            try:
                sup = item.general_supply.general.get(
                    supplyLot=item.supplyLot, expiredDate=item.expiredDate
                )
                sup.count += item.count
            except Supply.DoesNotExist:
                sup = Supply(
                    name=item.general_supply.name,
                    general_supply=item.general_supply,
                    category=item.general_supply.category,
                    ref=item.general_supply.ref,
                    supplyLot=item.supplyLot,
                    count=item.count,
                    expiredDate=item.expiredDate,
                )
            item.supply = sup
            sup.save()
            item.save()
    del_order.isHasBeenSaved = True
    del_order.save()
