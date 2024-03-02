from django.urls import path
from . import views, NPViews, view_upload
from . import apiViews
from .NPModels import *
from .booked_flow import booked_view

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
     path('get_progress_for_upload_supplies_new_order/<task_id>/<int:for_delivery_order_id>', view_upload.get_progress, name='get-progress'),
     path('upload_supplies_for_new_delivery/', view_upload.upload_supplies_for_new_delivery, name='upload_supplies_for_new_delivery'),
     path('new_delivery_save_delivery/<int:delivery_order_id>', view_upload.save_delivery, name='save-delivery'),
     path('delete_delivery_action/<int:delivery_order_id>', view_upload.delete_delivery_action, name='delete-delivery-action'),
     path('np-info', views.httpRequest, name='np-info'),
     path('np-info-sync-ref-post-request', views.np_info_sync_ref_post_request, name='np_info_sync_ref_post_request'),
     path('all_deliveries/', view_upload.all_deliveries, name='all_deliveries'),
     path('all_deliveries/<int:delivery_id>', view_upload.delivery_detail, name='delivery_detail'),
     path('all_deliveries/<int:delivery_id>/add_more_scan_to_exist_delivery_order/', view_upload.add_more_scan_to_exist_delivery_order, name='add_more_scan_to_exist_delivery_order'),
     path('all_deliveries/search-gen-sup-for-manual-add-in-delivery-order/<int:delivery_order_id>', view_upload.search_results_for_manual_add_in_delivery_order, name='search-gen-sup-for-manual-add-in-delivery-order'),
     path('all_deliveries/add_gen_sup_in_delivery_order_manual_list', view_upload.add_gen_sup_in_delivery_order_manual_list, name='add_gen_sup_in_delivery_order_manual_list'),
     path('all_deliveries/add_gen_sup_in_delivery_order_manual_list_delete_action', view_upload.add_gen_sup_in_delivery_order_manual_list_delete_action, name='add_gen_sup_in_delivery_order_manual_list_delete_action'),
     path('all_deliveries/add_gen_sup_in_delivery_order_manual_list_save_action', view_upload.add_gen_sup_in_delivery_order_manual_list_save_action, name='add_gen_sup_in_delivery_order_manual_list_save_action'),
     path('all_deliveries/add_gen_sup_in_delivery_order_manual_list_edit_action', view_upload.add_gen_sup_in_delivery_order_manual_list_edit_action, name='add_gen_sup_in_delivery_order_manual_list_edit_action'),
     path('all_deliveries/delivery_order_export_to_excel/<int:delivery_order_id>', view_upload.delivery_order_export_to_excel, name='delivery_order_export_to_excel'),
     path('all_deliveries/save-delivery-and-add-to-db/<int:delivery_order_id>', view_upload.upload_sup_from_delivery_order_and_save_db, name='save-delivery-and-add-to-db'),



    path('', views.home, name='home'),
    path('app_settings', views.app_settings, name='app_settings'),
    path('childSupply', views.childSupply, name='childSupply'),
    path('historySupply', views.historySupply, name='historySupply'),
    path('load_xms_data', views.load_xms_data, name='load_xms_data'),
    path('celery-test', view_upload.celery_test, name='celery_test'),


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
    path('deleteSupplyInOrderNPDocumentButton/', views.deleteSupplyInOrderNPDocumentButton, name='deleteSupplyInOrderNPDocumentButton'),


    path('allDevices/', views.devicesList, name='allDevices'),
    path('allDevices/full_image_view_for_device_image/<int:device_id>', views.full_image_view_for_device_image, name='full_image_view_for_device_image'),
    path('allDevices/export-to-xls', views.devices_render_to_xls, name='devices_render_to_xls'),



    path('add-general-supply-with-supply', views.addgeneralSupply, name='addGeneralSupply-with-supp'),
    path('add-general-supply', views.addgeneralSupplyOnly, name='add-general-supply'),
    path('add-new-city', views.addNewCity, name='add-new-city'),
    path('add-new-supply-category', views.addNewCategory, name='add-new-supply-category'),
    path('add-client', views.addNewClient, name='addClient'),
    path('newLot/<int:supp_id>', views.addNewLotforSupply, name='addNewLot'),
    path('history_for_supply/<int:supp_id>', views.history_for_supply, name='history_for_supply'),

    path('update/<int:supp_id>', views.updateSupply, name='updateSupply'),
    path('update_general/<int:supp_id>', views.updateGeneralSupply, name='updateGeneralSupply'),
    path('addSupplyToExistOrder/<int:supp_id>', views.addSupplyToExistOrder, name='addSupplyToExistOrder'),
    path('addSupplyToExistPreOrder/<int:supp_id>', views.addSupplyToExistPreOrder, name='addSupplyToExistPreOrder'),
    path('addSupplyToExistPreOrderGeneral/<int:supp_id>', views.addSupplyToExistPreOrderGeneral, name='addSupplyToExistPreOrderGeneral'),


    path('auth', views.registerPage, name='auth'),
    path('login', views.loginPage, name='login'),
    path('logout', views.logoutUser, name='logout'),

    path('orders', views.orders, name='orders'),
    path('agreements', views.agreements, name='agreements'),

    path('preorders', views.preorders, name='preorders'),
    path('delete-preorder/<int:order_id>', views.deletePreorder, name='delete-preorder'),
    path('delete_preorder_sup_in_preorder_cart/<int:sup_id>/<int:order_id>', views.delete_preorder_sup_in_preorder_cart, name='delete-preorder-sup-in-preorder-cart'),
    path('update-preorder-status/<int:order_id>', views.updatePreorderStatus, name='updatePreorderStatus'),
    path('orders_update_status/<int:order_id>', views.orderUpdateStatus, name='orders_update_status'),
    path('minus_from_preorders_detail_general_item', views.minus_from_preorders_detail_general_item, name='minus_from_preorders_detail_general_item'),

    path('clientsInfo', views.clientsInfo, name='clientsInfo'),
    path('clientsInfo/<int:client_id>/orders', views.ordersForClient, name='ordersForClient'),
    path('clientsInfo/<int:client_id>/agreements', views.agreementsForClient, name='agreementsForClient'),
    path('clientsInfo/<int:client_id>/devices', views.devicesForClient, name='devicesForClient'),
    path('clientsInfo/<int:place_id>/add-new-worker', views.addNewWorkerForClient, name='newWorkerForPlace'),
    path('clientsInfo/<int:client_id>/serviceNotes', views.serviceNotesForClient, name='serviceNotesForClient'),
    path('clientsInfo/<int:client_id>/editInfo', views.editClientInfo, name='editClientInfo'),
    path('clientsInfo/<int:worker_id>/editWorkerInfo', views.editWorkerInfo, name='editWorkerInfo'),
    path('clientsInfo/<int:client_id>/add-new-device', views.addNewDeviceForClient, name='addNewDeviceForClient'),
    path('clientsInfo/worker_card_info_delete_worker', views.worker_card_info_delete_worker, name='worker_card_info_delete_worker'),
    path('clientsInfo/worker_card_info_edit_action', views.worker_card_info_edit_action, name='worker_card_info_edit_action'),

    path('clientsInfo/<int:client_id>/booked_supplies_list', booked_view.booked_supplies_list, name='booked_sups_list_for_client'),
    path('add_sup_to_booked_cart/<int:sup_id>', booked_view.add_sup_to_booked_cart, name='add_sup_to_booked_cart'),
    path('booked-cart-badge-count', booked_view.booked_cart_badge_count_refresh, name='booked-cart-badge-count'),
    path('booked_cart_details/<int:booked_cart_id>', booked_view.booked_cart_details, name='booked_cart_details'),
    path('booked_carts_list', booked_view.booked_carts_list, name='booked_carts_list'),
    path('delete_sup_from_booked_cart_delete_action', booked_view.delete_sup_from_booked_cart_delete_action, name='delete_sup_from_booked_cart_delete_action'),
    path('minus_from_booked_supply_list_item', booked_view.minus_from_booked_supply_list_item, name='minus_from_booked_supply_list_item'),
    path('plus_from_preorders_detail_general_item', booked_view.plus_from_preorders_detail_general_item, name='plus_from_preorders_detail_general_item'),
    path('delete_from_preorders_detail_general_item/<int:el_id>', booked_view.delete_from_preorders_detail_general_item, name='delete_from_preorders_detail_general_item'),
    path('plus_from_booked_supply_list_item', booked_view.plus_from_booked_supply_list_item, name='plus_from_booked_supply_list_item'),
    path('delete_sup_from_booked_sups/<int:sup_id>', booked_view.delete_sup_from_booked_sups, name='delete_sup_from_booked_sups'),




    path('serviceNotes', views.serviceNotes, name='clientsInfo'),
    path('serviceNotes/create', views.createNote, name='create_note'),
    path('serviceNotes/create_for_client/<int:client_id>', views.createNote_for_client, name='create_note_for_client'),
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
    path('convert_order_to_booked_order/<int:order_id>', booked_view.convert_order_to_booked_order, name='convert_order_to_booked_order'),

    path('order_delete_order_previews_cell/<int:order_id>', views.order_delete, name='order_delete'),
    path('orderDetail_add_comment', views.orderDetail_add_comment, name='orderDetail_add_comment'),
    path('orderDetail_save_comment', views.orderDetail_save_comment, name='orderDetail_save_comment'),


    path('api/supplies', apiViews.SuppliesApiView.as_view()),
    path('api/supplies_add_from_scan', apiViews.SuppliesFromScanSaveApiView.as_view()),
    path('api/general-supplies', apiViews.GeneralSuppliesApiView.as_view()),
    path('api/<int:pk>/', apiViews.SupplyDetailView.as_view()),

    path('api/orders', apiViews.OrdersApiView.as_view()),
    path('api/orders/<int:order_id>', apiViews.SuppliesInOrderView.as_view()),
    path('api/places', apiViews.PlacesApiView.as_view()),

    # path('api/auth', views.RegistrationAPIView.as_view()),
    path('api/login', apiViews.LoginAPIView.as_view()),

    path('add_np_sender_place', views.add_np_sender_place, name='add_np_sender_place'),

    path('chart-sold', views.chartOfSoldSupplies),
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
    path('register_exls_selected_buttons', views.register_exls_selected_buttons, name='register_exls_selected_buttons'),
    path('get_print_xls_for_preorders', NPViews.get_print_xls_for_preorders, name='get_print_xls_for_preorders'),
    path('get_print_xls_for_preorders', NPViews.get_print_xls_for_preorders, name='get_print_xls_for_preorders'),
    path('add_more_np_places_input_group', NPViews.add_more_np_places_input_group, name='add_more_np_places_input_group'),
    path('minus_add_more_np_places_input_group', NPViews.minus_add_more_np_places_input_group, name='minus_add_more_np_places_input_group'),

    path('nova_poshta_registers', NPViews.nova_poshta_registers, name='nova_poshta_registers')

]