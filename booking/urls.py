from django.urls import path
from .views import book_service, cancel_order, check_all_ids, check_database_connection, edit_order, join_subcategory, leave_subcategory, my_orders,view_categories,view_subcategory_detail,view_subcategory_detail_worker

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
    path('edit-order/<uuid:order_id>/', edit_order, name='edit_order'),
    path('cancel-order/<uuid:order_id>/', cancel_order, name='cancel_order'),
    path('create-testimonial/<uuid:subcategory_id>/', views.create_testimonial_for_subcategory, name='create_testimonial_for_subcategory'),








]
