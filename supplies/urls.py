from django.urls import path
from . import views
from . import apiViews

urlpatterns = [

    path('cart/', views.cartDetail, name='cart'),

    path('', views.home, name='home'),
    path('childSupply', views.childSupply, name='childSupply'),

    path('update_item/', views.updateItem, name='update_item'),
    path('cart/update_item/', views.updateCartItem, name='update_item_detail'),
    path('delete_supply/', views.deleteSupply, name='delete_supply'),
    path('delete_supply_in_order/', views.deleteSupplyInOrder, name='delete_supply_in_order'),




    path('add-general-supply', views.addgeneralSupply, name='addGeneralSupply'),
    path('add-client', views.addNewClient, name='addClient'),
    path('newLot/<int:supp_id>', views.addNewLotforSupply, name='addNewLot'),

    path('update/<int:supp_id>', views.updateSupply, name='updateSupply'),
    path('update_general/<int:supp_id>', views.updateGeneralSupply, name='updateGeneralSupply'),
    path('addSupplyToExistOrder/<int:supp_id>', views.addSupplyToExistOrder, name='addSupplyToExistOrder'),


    # path('auth', views.registerPage, name='auth'),
    path('login', views.loginPage, name='login'),
    path('logout', views.logoutUser, name='logout'),

    path('orders', views.orders, name='orders'),
    path('orders_update_status/', views.orderUpdateStatus, name='orders_update_status'),

    path('clientsInfo', views.clientsInfo, name='clientsInfo'),
    path('clientsInfo/<int:client_id>/orders', views.ordersForClient, name='ordersForClient'),
    path('clientsInfo/<int:place_id>/add-new-worker', views.addNewWorkerForClient, name='newWorkerForPlace'),
    path('clientsInfo/<int:client_id>/serviceNotes', views.serviceNotesForClient, name='serviceNotesForClient'),
    path('clientsInfo/<int:client_id>/editInfo', views.editClientInfo, name='editClientInfo'),




    path('serviceNotes', views.serviceNotes, name='clientsInfo'),
    path('serviceNotes/create', views.createNote, name='create_note'),
    path('serviceNotes/delete/<int:note_id>', views.deleteServiceNote, name='deleteNote'),
    path('serviceNotes/update/<int:note_id>', views.updateNote, name='updateNote'),

    path('orders/<int:order_id>', views.orderDetail, name='orderDetail'),


    path('api', apiViews.SuppliesApiView.as_view()),
    path('api/<int:pk>/', apiViews.SupplyDetailView.as_view()),

    path('api/orders', apiViews.OrdersApiView.as_view()),
    path('api/orders/<int:order_id>', apiViews.SuppliesInOrderView.as_view()),
    path('api/places', apiViews.PlacesApiView.as_view()),

    # path('api/auth', views.RegistrationAPIView.as_view()),
    # path('api/login', views.LoginAPIView.as_view()),



]