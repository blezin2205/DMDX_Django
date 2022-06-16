from django.urls import path
from . import views
from . import apiViews

urlpatterns = [

    path('cart/', views.cartDetail, name='cart'),
    path('preorders-cart/', views.cartDetailForClient, name='precart'),

    path('', views.home, name='home'),
    path('childSupply', views.childSupply, name='childSupply'),

     path('count-on-hold-make', views.countOnHoldMake, name='countOnHoldMake'),

    path('update_item/', views.updateItem, name='update_item'),
    path('update_order_count/', views.update_order_count, name='update_order_count'),
    path('preorder_general_supp_buttons/', views.preorder_general_supp_buttons, name='preorder_general_supp_buttons'),
    path('cart/update_item/', views.updateCartItem, name='update_item_detail'),
    path('preorders-cart/update_item/', views.updateCartItem, name='update_item_detail'),
    path('delete_supply/', views.deleteSupply, name='delete_supply'),
    path('delete_supply_in_order/', views.deleteSupplyInOrder, name='delete_supply_in_order'),

    path('allDevices/', views.devicesList, name='allDevices'),
    path('allDevices/export-to-xls', views.devices_render_to_xls, name='devices_render_to_xls'),



    path('add-general-supply', views.addgeneralSupply, name='addGeneralSupply'),
    path('add-client', views.addNewClient, name='addClient'),
    path('newLot/<int:supp_id>', views.addNewLotforSupply, name='addNewLot'),

    path('update/<int:supp_id>', views.updateSupply, name='updateSupply'),
    path('update_general/<int:supp_id>', views.updateGeneralSupply, name='updateGeneralSupply'),
    path('addSupplyToExistOrder/<int:supp_id>', views.addSupplyToExistOrder, name='addSupplyToExistOrder'),
    path('addSupplyToExistPreOrder/<int:supp_id>', views.addSupplyToExistPreOrder, name='addSupplyToExistPreOrder'),
    path('addSupplyToExistPreOrderGeneral/<int:supp_id>', views.addSupplyToExistPreOrderGeneral, name='addSupplyToExistPreOrderGeneral'),


    # path('auth', views.registerPage, name='auth'),
    path('login', views.loginPage, name='login'),
    path('logout', views.logoutUser, name='logout'),

    path('orders', views.orders, name='orders'),
    path('preorders', views.preorders, name='preorders'),
    path('orders_update_status/', views.orderUpdateStatus, name='orders_update_status'),

    path('clientsInfo', views.clientsInfo, name='clientsInfo'),
    path('clientsInfo/<int:client_id>/orders', views.ordersForClient, name='ordersForClient'),
    path('clientsInfo/<int:client_id>/devices', views.devicesForClient, name='devicesForClient'),
    path('clientsInfo/<int:place_id>/add-new-worker', views.addNewWorkerForClient, name='newWorkerForPlace'),
    path('clientsInfo/<int:client_id>/serviceNotes', views.serviceNotesForClient, name='serviceNotesForClient'),
    path('clientsInfo/<int:client_id>/editInfo', views.editClientInfo, name='editClientInfo'),
    path('clientsInfo/<int:client_id>/add-new-device', views.addNewDeviceForClient, name='addNewDeviceForClient'),




    path('serviceNotes', views.serviceNotes, name='clientsInfo'),
    path('serviceNotes/create', views.createNote, name='create_note'),
    path('serviceNotes/delete/<int:note_id>', views.deleteServiceNote, name='deleteNote'),
    path('serviceNotes/update/<int:note_id>', views.updateNote, name='updateNote'),

    path('orders/<int:order_id>', views.orderDetail, name='orderDetail'),
    path('preorders/<int:order_id>', views.preorderDetail, name='preorderDetail'),
    path('order-detail-pdf/<int:order_id>', views.orderDetail_pdf, name='orderDetailPdf'),
    path('order-detail-csv/<int:order_id>', views.render_to_xls, name='orderDetailCsv'),
    path('preorder-detail-csv/<int:order_id>', views.preorder_render_to_xls, name='preorderDetailCsv'),


    path('api/supplies', apiViews.SuppliesApiView.as_view()),
    path('api/general-supplies', apiViews.GeneralSuppliesApiView.as_view()),
    path('api/<int:pk>/', apiViews.SupplyDetailView.as_view()),

    path('api/orders', apiViews.OrdersApiView.as_view()),
    path('api/orders/<int:order_id>', apiViews.SuppliesInOrderView.as_view()),
    path('api/places', apiViews.PlacesApiView.as_view()),

    # path('api/auth', views.RegistrationAPIView.as_view()),
    # path('api/login', views.LoginAPIView.as_view()),


    path('http-response', views.httpRequest),



]