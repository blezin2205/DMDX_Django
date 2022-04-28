from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('onlyGood', views.onlyGood, name='onlyGood'),
    path('onlyExpired', views.onlyExpired, name='onlyExpired'),

    path('update_item/', views.updateItem, name='update_item'),
    path('delete_supply/', views.deleteSupply, name='delete_supply'),




    path('add-general-supply', views.addgeneralSupply, name='addGeneralSupply'),
    path('newLot/<int:supp_id>', views.addNewLotforSupply, name='addNewLot'),

    path('update/<int:supp_id>', views.updateSupply, name='updateSupply'),

    # path('auth', views.registerPage, name='auth'),
    path('login', views.loginPage, name='login'),
    path('logout', views.logoutUser, name='logout'),

    path('orders', views.orders, name='orders'),

    path('clientsInfo', views.clientsInfo, name='clientsInfo'),
    path('clientsInfo/<int:client_id>/orders', views.ordersForClient, name='ordersForClient'),
    path('clientsInfo/<int:client_id>/serviceNotes', views.serviceNotesForClient, name='serviceNotesForClient'),


    path('serviceNotes', views.serviceNotes, name='clientsInfo'),
    path('serviceNotes/create', views.createNote, name='create_note'),
    path('serviceNotes/delete/<int:note_id>', views.deleteServiceNote, name='deleteNote'),
    path('serviceNotes/update/<int:note_id>', views.updateNote, name='updateNote'),

    path('orders/<int:order_id>', views.orderDetail, name='orderDetail'),


    path('api', views.SuppliesApiView.as_view()),
    path('api/<int:pk>/', views.SupplyDetailView.as_view()),

    path('api/orders', views.OrdersApiView.as_view()),
    path('api/orders/<int:order_id>', views.SuppliesInOrderView.as_view()),


    path('api/places', views.PlacesApiView.as_view()),

    # path('api/auth', views.RegistrationAPIView.as_view()),
    # path('api/login', views.LoginAPIView.as_view()),



]