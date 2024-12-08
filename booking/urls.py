from django.urls import path
from .views import book_service, cancel_order, cancel_worker_order, check_all_ids, check_database_connection, create_testimonial_for_subcategory, get_customer_balance, get_worker_details, join_subcategory, leave_subcategory, my_orders, process_payment,view_categories,view_subcategory_detail,view_subcategory_detail_worker

urlpatterns = [
    path('check-db/', check_database_connection),
    path('categories/', view_categories, name='view_categories'),
    path('subcategory/<uuid:subcategory_id>/', view_subcategory_detail, name='subcategory_detail'),
    path('subcategory/<uuid:subcategory_id>/worker/<uuid:worker_id>/', view_subcategory_detail_worker, name='subcategory_detail_worker'),
    path('check_ids/', check_all_ids, name='check_ids'),
    path('subcategory/<uuid:subcategory_id>/worker/<uuid:worker_id>/join/', join_subcategory, name='join_subcategory'),
    path('subcategory/<uuid:subcategory_id>/worker/<uuid:worker_id>/leave/', leave_subcategory, name='leave_subcategory'),
    path('book-service/<uuid:subcategory_id>/<int:session>/', book_service, name='book_service'),
    path('subcategory/<uuid:subcategory_id>/worker/<uuid:worker_id>/join/', join_subcategory, name='join_subcategory'),
    path('my-orders/', my_orders, name='my_orders'),
    path('cancel-order/<uuid:order_id>/', cancel_order, name='cancel_order'),
    path('cancel-worker-order/<uuid:order_id>/', cancel_worker_order, name='cancel_worker_order'),
    path('create-testimonial/<uuid:subcategory_id>/', create_testimonial_for_subcategory, name='create_testimonial_for_subcategory'),
    path('get-customer-balance/', get_customer_balance, name='get_customer_balance'),
    path('pay-order/<uuid:order_id>/', process_payment, name='process_payment'),
    path('get-worker-details/<uuid:worker_id>/', get_worker_details, name='get_worker_details'),













]
