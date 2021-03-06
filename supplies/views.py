import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, FileResponse

from .decorators import unauthenticated_user, allowed_users
from .models import *
from .serializers import *
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from django.contrib.auth import authenticate, login, logout
from .filters import *
from .forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.core.paginator import Paginator

from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import os
from xlsxwriter.workbook import Workbook
import requests


cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


async def httpRequest(request):

        param = {'apiKey': '99f738524ca3320ece4b43b10f4181b1',
                'modelName': 'Counterparty',
             'calledMethod': 'getCounterpartyContactPersons',
             'methodProperties': {'Ref': '3b0e7317-2a6b-11eb-8513-b88303659df5'}}

        data = requests.get('https://api.novaposhta.ua/v2.0/json/', data=json.dumps(param)).json()

        return  render(request, "supplies/http_response.html", {'data': data})


def countOnHoldMake(request):
    supps = Supply.objects.all()

    for supp in supps:
        if not supp.countOnHold:
            supp.countOnHold = 0
            supp.save(update_fields=['countOnHold'])

    return redirect('/')



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteSupply(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    if action == 'delete':
      supp = Supply.objects.get(id=prodId)
      supp.delete()

    elif action =='delete_general_supply':
      genSupp = GeneralSupply.objects.get(id=prodId)
      genSupp.delete()

    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteSupplyInOrder(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    if action == 'delete':
        suppInOrder = SupplyInOrder.objects.get(id=prodId)
        if suppInOrder.hasSupply():
            supp_for_supp_in_order = suppInOrder.supply
            supp_for_supp_in_order.countOnHold -= suppInOrder.count_in_order
            supp_for_supp_in_order.save(update_fields=['countOnHold'])
        suppInOrder.delete()
        return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateItem(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    print('Action', action)
    print('id', prodId)

    user = request.user
    supply = Supply.objects.get(id=prodId)
    order, created = OrderInCart.objects.get_or_create(userCreated=user, isComplete=False)

    try:
      suppInCart = SupplyInOrderInCart.objects.get(supply=supply, supply_for_order=order, lot=supply.supplyLot, date_expired=supply.expiredDate)
    except:
      suppInCart = SupplyInOrderInCart(
                                        supply=supply,
                                        supply_for_order=order,
                                        lot=supply.supplyLot,
                                        date_expired=supply.expiredDate,
                                        date_created=supply.dateCreated)

    if action == 'add':
        suppInCart.count_in_order = (suppInCart.count_in_order + 1)
    elif action == 'remove':
        suppInCart.count_in_order = (suppInCart.count_in_order - 1)

    suppInCart.save()

    if suppInCart.count_in_order <= 0:
        suppInCart.delete()


    return  JsonResponse('Item was added', safe=False)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def update_order_count(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    print('Action', action)
    print('id', prodId)

    supply = SupplyInOrder.objects.get(id=prodId)

    if action == 'add':
        supply.count_in_order = (supply.count_in_order + 1)
        supply.supply.countOnHold += 1
    elif action == 'remove':
        supply.count_in_order = (supply.count_in_order - 1)
        supply.supply.countOnHold -= 1

    supply.supply.save()
    supply.save()

    if supply.count_in_order <= 0:
        supply.delete()


    return  JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateCartItem(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']

    print('Action', action)
    print('id', prodId)

    user = request.user
    suppInCart = SupplyInOrderInCart.objects.get(id=prodId)
    order, created = OrderInCart.objects.get_or_create(userCreated=user, isComplete=False)

    if action == 'add':
        suppInCart.count_in_order = (suppInCart.count_in_order + 1)
        suppInCart.save()
    elif action == 'remove':
        suppInCart.count_in_order = (suppInCart.count_in_order - 1)
        suppInCart.save()
    elif action == 'delete':
        suppInCart.delete()
        if SupplyInOrderInCart.objects.all().count() == 0:
            redirect('/')

    if suppInCart.count_in_order <= 0:
        suppInCart.delete()


    return  JsonResponse('Item was added', safe=False)


def registerPage(request):
    if request.user.is_authenticated:
        return redirect('/')
    else:
        form = CreateUserForm()
        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                form.save()

        context = {'form': form}
    return render(request, 'auth/register.html', context)


@unauthenticated_user
def loginPage(request):
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
             login(request, user)
             return redirect('/')

        return render(request, 'auth/login.html')


@login_required(login_url='login')
def logoutUser(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def home(request):

    supplies = GeneralSupply.objects.all().order_by('name')
    uncompleteOrdersExist = Order.objects.filter(isComplete=False).exists()
    #
    # for gen in supplies:
    #    for sup in gen.general.all():
    #        sup.name = gen.name
    #        sup.ref = gen.ref
    #        sup.save(update_fields=['name', 'ref'])

    suppFilter = SupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    paginator = Paginator(supplies, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    try:
        orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
        cart_items = orderInCart.get_cart_items
    except:
        orderInCart = None
        cart_items = 0

    if request.method == 'POST':
        supp = supplies.get(id=request.POST.get('supp_id'))
        supp.delete()

    return render(request, 'supplies/home.html', {'title': '?????? ????????????', 'cart_items': cart_items, 'supplies': page_obj,'suppFilter': suppFilter, 'isHome': True, 'isAll': True, 'uncompleteOrdersExist': uncompleteOrdersExist})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def cartDetail(request):

    orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
    cart_items = orderInCart.get_cart_items
    supplies = orderInCart.supplyinorderincart_set.all()
    orderForm = OrderInCartForm(request.POST or None)
    if request.method == 'POST':

        countList = request.POST.getlist('count_list')
        countListId = request.POST.getlist('count_list_id')

        if orderForm.is_valid():
            place = orderForm.cleaned_data['place']
            comment = orderForm.cleaned_data['comment']
            isComplete = orderForm.cleaned_data['isComplete']
            if isComplete:
                dateSent = timezone.now().date()
            else:
                dateSent = None
            order = Order(userCreated=orderInCart.userCreated, place=place, dateSent=dateSent, isComplete=isComplete, comment=comment)
            order.save()

            for index, sup in enumerate(supplies):
                suppInOrder = SupplyInOrder(count_in_order=countList[index],
                                            supply=sup.supply,
                                            generalSupply=sup.supply.general_supply,
                                            supply_for_order=order, lot=sup.lot,
                                            date_created=sup.date_created,
                                            date_expired=sup.date_expired,
                                            internalName=sup.supply.general_supply.name,
                                            internalRef=sup.supply.general_supply.ref)
                suppInOrder.save()
                supply = suppInOrder.supply
                try:
                 countOnHold = int(supply.countOnHold)
                except:
                 countOnHold = 0
                countInOrder = int(suppInOrder.count_in_order)
                if isComplete:
                    supply.count -= countInOrder
                    supply.save(update_fields=['count'])
                else:
                    if supply.countOnHold:
                         supply.countOnHold = countOnHold + countInOrder
                         supply.save(update_fields=['countOnHold'])
                    else:
                        supply.countOnHold = 0
                        supply.save(update_fields=['countOnHold'])
                        supply.countOnHold = countOnHold + countInOrder
                        supply.save(update_fields=['countOnHold'])


        orderInCart.delete()

        return redirect('/orders')


    return render(request, 'supplies/cart.html',
                  {'title': '??????????????', 'order': orderInCart, 'cart_items': cart_items, 'supplies': supplies, 'orderForm': orderForm
                   })



@login_required(login_url='login')
def childSupply(request):
    supplies = Supply.objects.all().order_by('name')
    suppFilter = ChildSupplyFilter(request.GET, queryset=supplies)
    supplies = suppFilter.qs

    try:
        orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
        cart_items = orderInCart.get_cart_items
    except:
        orderInCart = None
        cart_items = 0

    if request.GET.get('xls_button'):

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f"attachment; filename=Supply_List.xlsx"

        row_num = 3

        wb = Workbook(response, {'in_memory': True})
        ws = wb.add_worksheet('Supply-List')
        format = wb.add_format({'bold': True})
        format.set_font_size(16)

        columns_table = [{'header': '???'},
                         {'header': '?????????? ????????????'},
                         {'header': 'REF'},
                         {'header': 'LOT'},
                         {'header': '??-????'},
                         {'header': '??????.????????.'},
                         {'header': '??????????????????'},
                         ]

        ws.write(0, 0,
                 f'?????????????????? ???????????? ??????????????',
                 format)

        format = wb.add_format({'num_format': 'dd.mm.yyyy'})
        format.set_font_size(12)

        for row in supplies:
            row_num += 1
            name = row.general_supply.name
            ref = ''
            if row.general_supply.ref:
                ref = row.general_supply.ref
            lot = ''
            if row.supplyLot:
                lot = row.supplyLot
            count = row.count
            date_expired = row.expiredDate.strftime("%d.%m.%Y")
            category = row.general_supply.category.name

            val_row = [name, ref, lot, count, date_expired, category]

            for col_num in range(len(val_row)):
                ws.write(row_num, 0, row_num - 3)
                ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 35)
        ws.set_column(2, 3, 15)
        ws.set_column(4, 4, 10)
        ws.set_column(5, 5, 10)
        ws.set_column(6, 6, 12)

        ws.add_table(3, 0, suppFilter.qs.count() + 3, len(columns_table) - 1, {'columns': columns_table})
        wb.close()
        return response







    return render(request, 'supplies/homeChild.html',
                  {'title': '?????????????? ????????????', 'supplies': supplies,  'cart_items': cart_items, 'suppFilter': suppFilter, 'isHome': True, 'isChild': True})


@login_required(login_url='login')
def orders(request):

    try:
        orderInCart = OrderInCart.objects.get(userCreated=request.user, isComplete=False)
        cart_items = orderInCart.get_cart_items
    except:
        orderInCart = None
        cart_items = 0

    orders = Order.objects.all().order_by('-id')
    return render(request, 'supplies/orders.html', {'title': '?????? ????????????????????', 'orders': orders, 'cart_items': cart_items, 'isOrders': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def orderUpdateStatus(request):
    data = json.loads(request.body)
    prodId = data['productId']
    action = data['action']
    order = Order.objects.get(id=prodId)
    if action == 'update':
      supps = order.supplyinorder_set.all()
      for el in supps:
          countInOrder = el.count_in_order
          supp = el.supply
          supp.countOnHold -= countInOrder
          supp.count -= countInOrder
          supp.save(update_fields=['countOnHold', 'count'])
          if supp.count == 0:
              supp.delete()

      order.isComplete = True
      order.dateSent = timezone.now().date()
      order.save()

    elif action == 'delete':
        if not order.isComplete:
          supps = order.supplyinorder_set.all()
          for el in supps:
             if el.hasSupply():
               countInOrder = el.count_in_order
               supp = el.supply
               supp.countOnHold -= countInOrder
               supp.save(update_fields=['countOnHold'])
        order.delete()

    return JsonResponse('Item was added', safe=False)


@login_required(login_url='login')
def ordersForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    orders = place.order_set.all()
    title = f'?????? ???????????????????? ?????? ??????????????: \n {place.name}, {place.city_ref.name}'
    if not orders:
        title = f'?? ?????????????? "{place.name}, {place.city_ref.name}" ???? ?????????? ??????????????????'

    return render(request, 'supplies/orders.html', {'title': title, 'orders': orders, 'isClients': True})


@login_required(login_url='login')
def devicesForClient(request, client_id):
    place = get_object_or_404(Place, pk=client_id)
    devices = place.device_set.all()
    title = f'?????? ?????????????? ?????? ??????????????: \n {place.name}, {place.city_ref.name}'
    if not devices:
        title = f'?? ?????????????? "{place.name}, {place.city_ref.name}" ???? ?????????? ??????????????????'

    return render(request, 'supplies/devices.html', {'title': title, 'devices': devices, 'isClients': True})


def devicesList(request):
    devices = Device.objects.all().order_by('general_device__name')
    devFilters = DeviceFilter(request.GET, queryset=devices)
    devices = devFilters.qs
    title = f'??c?? ??????????????'
    return render(request, 'supplies/devices.html', {'title': title, 'devices': devices, 'filter': devFilters, 'isDevices': True})




@login_required(login_url='login')
def serviceNotesForClient(request, client_id):
    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = User.objects.get(pk=request.user.id)
            obj.save()
            return HttpResponseRedirect(request.path_info)

    place = get_object_or_404(Place, pk=client_id)
    serviceNotes = place.servicenote_set.all()
    title = f'?????? ???????????????? ?????????????? ?????? ??????????????: \n {place.name}, {place.city}'
    return render(request, 'supplies/serviceNotes.html',
                  {'title': title, 'serviceNotes': serviceNotes, 'form': form, 'isClients': True})



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def createNote(request):
    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = User.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    return render(request, 'supplies/createNote.html',
                  {'title': f'???????????????? ?????????? ??????????', 'form': form,
                   'isService': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateNote(request, note_id):
    note = ServiceNote.objects.get(id=note_id)
    form = ServiceNoteForm(instance=note)
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST, instance=note)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = User.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    return render(request, 'supplies/createNote.html',
                  {'title': f'???????????????????? ?????????? ???{note_id}', 'form': form,
                    'isService': True})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateSupply(request, supp_id):
    note = Supply.objects.get(id=supp_id)
    form = SupplyForm(instance=note)
    if request.method == 'POST':
        form = SupplyForm(request.POST, instance=note)
        if form.is_valid():
            # obj = form.save(commit=False)
            # obj.from_user = User.objects.get(pk=request.user.id)
            form.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)

    return render(request, 'supplies/createSupply.html',
                  {'title': f'???????????????????? ?????????? ???{supp_id}', 'form': form})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def addSupplyToExistOrder(request, supp_id):
    supp = Supply.objects.get(id=supp_id)
    orderForm = OrderForm(request.POST or None)
    supply = SupplyInOrderInCart(count_in_order=1, supply=supp, lot=supp.supplyLot, date_expired=supp.expiredDate)

    if request.method == 'POST':

        count = int(request.POST.get('count_list'))
        if orderForm.is_valid():
            order = orderForm.cleaned_data['order']

            try:
                suppInOrder = SupplyInOrder.objects.get(supply=supp, generalSupply=supp.general_supply, supply_for_order=order, lot=supp.supplyLot, date_created=supp.dateCreated, date_expired=supp.expiredDate)
                suppInOrder.count_in_order += count
            except:
                suppInOrder = SupplyInOrder(count_in_order=count, supply=supp,
                                        generalSupply=supp.general_supply, supply_for_order=order, lot=supp.supplyLot,
                                        date_created=supp.dateCreated, date_expired=supp.expiredDate,
                                            internalName=supp.general_supply.name,
                                            internalRef=supp.general_supply.ref)
            suppInOrder.save()
            supp.countOnHold += count
            supp.save(update_fields=['countOnHold'])
            next = request.POST.get('next')
            return HttpResponseRedirect(next)


    return render(request, 'supplies/cart.html',
                  {'title': '???????????? ???? ????????????????????',
                   'orderForm': orderForm, 'supplies': [supply],
                   })



@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateGeneralSupply(request, supp_id):
    supp = GeneralSupply.objects.get(id=supp_id)
    form = GeneralSupplyForm(instance=supp)
    if request.method == 'POST':
        form = GeneralSupplyForm(request.POST, instance=supp)
        if form.is_valid():
            # obj = form.save(commit=False)
            # obj.from_user = User.objects.get(pk=request.user.id)
            form.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)

    return render(request, 'supplies/createSupply.html',
                  {'title': f'???????????????????? ?????????? ???{supp_id}', 'form': form})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def addNewLotforSupply(request, supp_id):
    generalSupp = GeneralSupply.objects.get(id=supp_id)
    form = SupplyForm()
    if request.method == 'POST':
        form = SupplyForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.general_supply = generalSupp
            obj.category = generalSupp.category
            obj.save()
            next = request.POST.get('next')
            return HttpResponseRedirect(next)

    return render(request, 'supplies/createSupply.html',
                  {'title': f'???????????? ?????????? LOT ?????? {generalSupp.name}', 'form': form})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def addgeneralSupply(request):
    form = NewSupplyForm()
    if request.method == 'POST':
        form = NewSupplyForm(request.POST)
        if form.is_valid():
            try:
                genSupp = GeneralSupply.objects.get(name=form.cleaned_data['name'].strip())
            except:
                genSupp = GeneralSupply(name=form.cleaned_data['name'].strip(), ref=form.cleaned_data['ref'].strip(), category=form.cleaned_data['category'])
            genSupp.save()
            obj = form.save(commit=False)
            obj.general_supply = genSupp
            obj.save()
            # form.save()
            return redirect('/')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'???????????? ?????????? ?????????? (??????????)', 'form': form})


@login_required(login_url='login')
def addNewClient(request):
    form = ClientForm()
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/clientsInfo')
    return render(request, 'supplies/createSupply.html',
                  {'title': f'???????????? ???????????? ??????????????', 'form': form})



@login_required(login_url='login')
def addNewDeviceForClient(request, client_id):
    client = Place.objects.get(id=client_id)
    form = DeviceForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            device = Device(general_device=form.cleaned_data['general_device'],
                            serial_number=form.cleaned_data['serial_number'],
                            date_installed=form.cleaned_data['date_installed'],
                            in_place=client)
            device.save()
            return redirect('/clientsInfo')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'???????????? ???????????? ??????: \n {client.name}, {client.city}', 'form': form})


@login_required(login_url='login')
def editClientInfo(request, client_id):
    client = Place.objects.get(id=client_id)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('/clientsInfo')

    return render(request, 'supplies/createSupply.html',
                  {'title': f'???????????????????? ??????????????: {client.name}, {client.city}', 'form': form})

@login_required(login_url='login')
def addNewWorkerForClient(request, place_id):
    form = WorkerForm()
    place = Place.objects.get(id=place_id)
    if request.method == 'POST':
        form = WorkerForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.for_place = place
            obj.save()
            return redirect('/clientsInfo')
    return render(request, 'supplies/createSupply.html',
                  {'title': f'???????????? ???????????? ???????????????????? ?????? {place.name}, {place.city}', 'form': form})


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteServiceNote(request, note_id):
    note = ServiceNote.objects.get(id=note_id)
    if request.method == 'POST':
        note.delete()
    return redirect('/serviceNotes')


def orderDetail_pdf(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=orderDetail' + \
        str(order.id) + str(order.place.name) + str(order.place.city) + '.pdf'
    template = get_template('supplies/orderdetail-pdf.html')
    pisa_status = render_to_pdf(supplies_in_order)
    return HttpResponse(pisa_status, content_type='application/pdf')


def fetch_resources(uri, rel):
    path = os.path.join(uri.replace(settings.STATIC_URL, ""))
    return path

def render_to_pdf(supplies_in_order):
    template = get_template('supplies/orderdetail-pdf.html')
    html = template.render({'supps': supplies_in_order})
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result, link_callback=fetch_resources, encoding='utf-8')
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


def render_to_csv(request, order_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=venues.csv'

    # Create a csv writer
    writer = csv.writer(response)

    # Designate The Model
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

    # Add column headings to the csv file
    writer.writerow(['?????????? ????????????', '??????????????????', 'REF', 'LOT', '??????????????????', '?????????? ??????????????????????'])

    # Loop Thu and output
    for supp in supplies_in_order:
        writer.writerow([supp.generalSupply.name, supp.generalSupply.category.name, supp.generalSupply.ref, supp.lot, supp.date_expired])

    return response

def render_to_xls(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Order-{order_id}.xlsx"

    row_num = 3

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet(f'???{order_id}, {order.place.name}, {order.place.city}')
    format = wb.add_format({'bold': True})
    format.set_font_size(16)


    columns_table = [ {'header': '???'},
        {'header': '?????????? ????????????'},
     {'header': 'REF'},
     {'header': 'LOT'},
     {'header': '??-????'},
     {'header': '??????.????????.'},
     ]

    ws.write(0, 0, f'??????????. ???{order_id} ?????? {order.place.name}, {order.place.city} ?????? {order.dateCreated.strftime("%d-%m-%Y")}', format)
    if order.comment:
        format = wb.add_format()
        format.set_font_size(14)
        ws.write(1, 0, f'??????????????.: {order.comment}', format)
        ws.write(2, 0, f'????????????: {supplies_in_order.count()} ????.', format)

    format = wb.add_format()
    format.set_font_size(12)

    for row in supplies_in_order:
        row_num += 1
        name = row.generalSupply.name
        ref = ''
        if row.generalSupply.ref:
           ref = row.generalSupply.ref
        lot = ''
        if row.lot:
            lot = row.lot
        count = row.count_in_order
        date_expired = row.date_expired.strftime("%d-%m-%Y")

        val_row = [name, ref, lot, count, date_expired]

        for col_num in range(len(val_row)):
            ws.write(row_num, 0, row_num - 3)
            ws.write(row_num, col_num + 1, str(val_row[col_num]), format)

    ws.set_column(0, 0, 3)
    ws.set_column(1, 1, 34)
    ws.set_column(2, 3, 12)
    ws.set_column(4, 4, 4)
    ws.set_column(5, 5, 10)

    ws.add_table(3, 0, supplies_in_order.count() + 3, len(columns_table) - 1, {'columns': columns_table})
    wb.close()

    return response


@login_required(login_url='login')
def devices_render_to_xls(request):
    devices = Device.objects.all()

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f"attachment; filename=Devices-List.xlsx"

    row_num = 3

    wb = Workbook(response, {'in_memory': True})
    ws = wb.add_worksheet('Devices-List')
    format = wb.add_format({'bold': True})
    format.set_font_size(24)

    columns_table = [{'header': '???'},
                     {'header': 'Name'},
                     {'header': 'S/N'},
                     {'header': 'Customer City'},
                     {'header': 'Customer Name'},
                     {'header': 'Date Installed'}
                     ]

    ws.write(0, 0,
             'Devices List DIAMEDIX Ukraine',
             format)

    format = wb.add_format({'text_wrap': True})
    format.set_font_size(22)
    for row in devices:
        row_num += 1
        name = row.general_device.name
        customer = row.in_place.name
        customer_city = row.in_place.city
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






@login_required(login_url='login')
def orderDetail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    supplies_in_order = order.supplyinorder_set.all()

    print(supplies_in_order.first())
    return render(request, 'supplies/orderDetail.html', {'title': f'???????????????????? ??? {order_id}', 'order': order, 'supplies': supplies_in_order, 'isOrders': True})


@login_required(login_url='login')
def clientsInfo(request):
    place = Place.objects.all().order_by('-id')
    placeFilter = PlaceFilter(request.GET, queryset=place)
    place = placeFilter.qs
    return render(request, 'supplies/clientsList.html',
                  {'title': f'??????????????', 'clients': place, 'placeFilter': placeFilter, 'isClients': True})


@login_required(login_url='login')
def serviceNotes(request):
    form = ServiceNoteForm()
    if request.method == 'POST':
        form = ServiceNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.from_user = User.objects.get(pk=request.user.id)
            obj.save()
            return redirect('/serviceNotes')

    serviceNotes = ServiceNote.objects.all().order_by('-id')
    serviceFilters = ServiceNotesFilter(request.GET, queryset=serviceNotes)
    serviceNotes = serviceFilters.qs

    return render(request, 'supplies/serviceNotes.html',
                   {'title': f'????????i?????? ????????????', 'serviceNotes': serviceNotes, 'form': form, 'serviceFilters': serviceFilters, 'isService': True})

