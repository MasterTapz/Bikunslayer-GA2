# urls.py
from django.urls import path
from . import views
from .views import  MyPay_Transaction

urlpatterns = [
    path('mypay/', views.MyPay, name='mypay'),  # This will map the '/mypay' URL to the 'mypay' view
    path('perform_transaction/', MyPay_Transaction, name='perform_transaction'),
    path('servicejob/', views.ServiceJob, name='servicejob'),
    path('servicejob-status/', views.ServiceJob_Status, name='servicejob_status'),
    path('accept_order/<uuid:order_id>/', views.accept_order, name='accept_order'),

    ]
