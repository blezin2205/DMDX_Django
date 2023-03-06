from django.urls import path
from . import views, NPViews
from . import apiViews
from .NPModels import *

urlpatterns = [

    path('cart/', views.cartDetail, name='cart'),
    path('preorders-cart/', views.cartDetailForClient, name='precart'),
    path('get_place_for_city_in_cart/', views.get_place_for_city_in_cart, name='get_place_for_city_in_cart'),
    path('get_place_for_city_in_precart/', views.get_place_for_city_in_precart, name='get_place_for_city_in_precart'),
    path('get_agreement_for_place_for_city_in_cart/', views.get_agreement_for_place_for_city_in_cart, name='get_agreement_for_place_for_city_in_cart'),
    path('add_to_exist_order_from_cart/', views.add_to_exist_order_from_cart, name='add_to_exist_order_from_cart'),
    path('choose_place_in_cart_not_precart/', views.choose_place_in_cart_not_precart, name='choose_place_in_cart_not_precart'),
    path('get_agreement_detail_for_cart/', views.get_agreement_detail_for_cart, name='get_agreement_detail_for_cart'),


     path('update-cart-item-count/', views.updateCartItemCount, name='cart-count'),
     path('update-precart-item-count/', views.updatePreCartItemCount, name='precart-count'),



    path('', views.home, name='home'),
    path('childSupply', views.childSupply, name='childSupply'),

     path('count-on-hold-make', views.countOnHoldMake, name='countOnHoldMake'),

    path('update_item/<int:supp_id>', views.updateItem, name='update_item'),
    path('update_item_precart/<int:supp_id>', views.preorder_supp_buttons, name='update_item_precart'),
    path('update_order_count/', views.update_order_count, name='update_order_count'),
    path('add_preorder_general_to_preorder/<int:prodId>', views.add_preorder_general_to_preorder, name='add_preorder_general_to_preorder'),
    path('cart/update_item/', views.updateCartItem, name='update_item_detail'),
    path('preorders-cart/update_item/', views.updateCartItem, name='update_item_detail'),
    path('preorders-cart/orderTypeDescriptionField/', views.orderTypeDescriptionField, name='orderTypeDescriptionField'),
    path('preorders-cart/orderTypeDescriptionField_for_client/', views.orderTypeDescriptionField_for_client, name='orderTypeDescriptionField_for_client'),
    path('preorders-cart/update_count_in_preorder_cart/<int:itemId>', views.update_count_in_preorder_cart, name='update_count_in_preorder_cart'),
    path('preorders-cart/choose_preorder_in_cart_for_client', views.choose_preorder_in_cart_for_client, name='choose_preorder_in_cart_for_client'),


    path('delete_supply/<int:suppId>', views.deleteSupply, name='delete_supply'),
    path('delete_supply_in_order/', views.deleteSupplyInOrder, name='delete_supply_in_order'),

    path('allDevices/', views.devicesList, name='allDevices'),
    path('allDevices/full_image_view_for_device_image/<int:device_id>', views.full_image_view_for_device_image, name='full_image_view_for_device_image'),
    path('allDevices/export-to-xls', views.devices_render_to_xls, name='devices_render_to_xls'),



    path('add-general-supply-with-supply', views.addgeneralSupply, name='addGeneralSupply-with-supp'),
    path('add-general-supply', views.addgeneralSupplyOnly, name='add-general-supply'),
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
    path('agreements', views.agreements, name='agreements'),

    path('preorders', views.preorders, name='preorders'),
    path('delete-preorder/<int:order_id>', views.deletePreorder, name='delete-preorder'),
    path('delete_preorder_sup_in_preorder_cart/<int:sup_id>/<int:order_id>', views.delete_preorder_sup_in_preorder_cart, name='delete-preorder-sup-in-preorder-cart'),
    path('update-preorder-status/<int:order_id>', views.updatePreorderStatus, name='updatePreorderStatus'),
    path('orders_update_status/<int:order_id>', views.orderUpdateStatus, name='orders_update_status'),

    path('clientsInfo', views.clientsInfo, name='clientsInfo'),
    path('clientsInfo/<int:client_id>/orders', views.ordersForClient, name='ordersForClient'),
    path('clientsInfo/<int:client_id>/agreements', views.agreementsForClient, name='agreementsForClient'),
    path('clientsInfo/<int:client_id>/devices', views.devicesForClient, name='devicesForClient'),
    path('clientsInfo/<int:place_id>/add-new-worker', views.addNewWorkerForClient, name='newWorkerForPlace'),
    path('clientsInfo/<int:client_id>/serviceNotes', views.serviceNotesForClient, name='serviceNotesForClient'),
    path('clientsInfo/<int:client_id>/editInfo', views.editClientInfo, name='editClientInfo'),
    path('clientsInfo/<int:worker_id>/editWorkerInfo', views.editWorkerInfo, name='editWorkerInfo'),
    path('clientsInfo/<int:client_id>/add-new-device', views.addNewDeviceForClient, name='addNewDeviceForClient'),




    path('serviceNotes', views.serviceNotes, name='clientsInfo'),
    path('serviceNotes/create', views.createNote, name='create_note'),
    path('serviceNotes/delete/<int:note_id>', views.deleteServiceNote, name='deleteNote'),
    path('serviceNotes/update/<int:note_id>', views.updateNote, name='updateNote'),

    path('orders/<int:order_id>/<int:sup_id>', views.orderDetail, name='orderDetail'),
    # path('orders/<int:order_id>/<int:sup_id>', views.orderDetail_with_highlighted, name='orderDetail_with_highlighted'),
    path('agreements/<int:agreement_id>', views.agreementDetail, name='agreementDetail'),

    path('preorders/<int:order_id>', views.preorderDetail, name='preorderDetail'),
    path('preorders/<int:order_id>/generate-order', views.preorderDetail_generateOrder, name='preorderDetail-generate-order'),

    path('order-detail-pdf/<int:order_id>', views.orderDetail_pdf, name='orderDetailPdf'),
    path('order-detail-csv/<int:order_id>', views.render_to_xls, name='orderDetailCsv'),
    path('preorder-detail-csv/<int:order_id>', views.preorder_render_to_xls, name='preorderDetailCsv'),

    path('order_delete_order_previews_cell/<int:order_id>', views.order_delete, name='order_delete'),


    path('api/supplies', apiViews.SuppliesApiView.as_view()),
    path('api/supplies_add_from_scan', apiViews.SuppliesFromScanSaveApiView.as_view()),
    path('api/general-supplies', apiViews.GeneralSuppliesApiView.as_view()),
    path('api/<int:pk>/', apiViews.SupplyDetailView.as_view()),

    path('api/orders', apiViews.OrdersApiView.as_view()),
    path('api/orders/<int:order_id>', apiViews.SuppliesInOrderView.as_view()),
    path('api/places', apiViews.PlacesApiView.as_view()),

    # path('api/auth', views.RegistrationAPIView.as_view()),
    # path('api/login', views.LoginAPIView.as_view()),

    path('add_np_sender_place', views.add_np_sender_place, name='add_np_sender_place'),

    path('http-response', NPViews.httpRequest),
    path('address_getCities', NPViews.address_getCities),
    path('search-city-np', NPViews.search_city, name='search-city-np'),
    path('choosed-city', NPViews.choosed_city, name='choosed-city'),
    path('choosed-street', NPViews.choosed_street, name='choosed-street'),
    path('search-street-np', NPViews.search_street, name='search-street-np'),
    path('search-warehouse-np', NPViews.search_warehouse, name='search-warehouse-np'),
    path('radioAddClientTONP', NPViews.radioAddClientTONP, name='radioAddClientTONP'),
    path('create-np_document-for-order/<int:order_id>', NPViews.create_np_document_for_order, name='create_np_document_for_order'),
    path('np-delivery-detail-info-for-order/<int:order_id>', NPViews.np_delivery_detail_info_for_order, name='np_delivery_detail_info_for_order'),
    path('np_create_ID_button_subscribe/<int:order_id>', NPViews.np_create_ID_button_subscribe, name='np_create_ID_button_subscribe'),
    path('get_register_for_orders', NPViews.get_register_for_orders, name='get_register_for_orders'),

    path('nova_poshta_registers', NPViews.nova_poshta_registers, name='nova_poshta_registers')

]