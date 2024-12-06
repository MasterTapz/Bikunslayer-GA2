from django.urls import path
from . import views

urlpatterns = [
    path('discount/', views.view_discount, name='view_discount'),
    path('testimony/', views.view_testimony, name='view_testimony'),
    path('voucher/', views.view_voucher, name='view_voucher'),
    path('api/discounts/', views.get_discounts, name='get_discounts'),
    path('api/vouchers/', views.get_vouchers, name='get_vouchers'),
    path('api/promotions/', views.get_promotions, name='get_promotions'),
    path('api/testimonials/', views.get_testimonials, name='get_testimonials'),
    path('purchase-voucher', views.purchase_voucher, name='purchase-voucher'),
    path('create-testimonial/', views.create_testimonial, name='create-testimonial'),
    


]
