from django.urls import path
from .views import (
    MyPay,
    MyPay_Transaction,
    ServiceJob_Status,
    ServiceJob,
    get_users,
    get_tr_mypay,
    get_tr_mypay_categories,
)
from . import views

urlpatterns = [
    # HTML Template views
    path('mypay/', MyPay, name='mypay'),
    path('mypay/transaction/', MyPay_Transaction, name='mypay-transaction'),
    path('servicejob/status/', ServiceJob_Status, name='servicejob_status'),
    path('servicejob/', ServiceJob, name='servicejob'),

    # API Endpoints
    path('api/get-users/', get_users, name='get-users'),
    path('api/get-tr-mypay/', get_tr_mypay, name='get-tr-mypay'),
    path('api/get-tr-mypay-categories/', get_tr_mypay_categories, name='get-tr-mypay-categories'),
    path('mypay/topup/', views.topup, name='topup'),
    path('mypay/service-payment/', views.service_payment, name='service_payment'),
    path('mypay/transfer/', views.transfer, name='transfer'),
    path('mypay/withdrawal/', views.withdrawal, name='withdrawal'),
]
