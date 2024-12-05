from django.urls import path
from .views import check_all_ids, check_database_connection, join_subcategory, leave_subcategory,view_categories,view_subcategory_detail,view_subcategory_detail_worker

urlpatterns = [
    path('check-db/', check_database_connection),
    path('categories/', view_categories),
    path('subcategory/<uuid:subcategory_id>/', view_subcategory_detail, name='subcategory_detail'),
    path('subcategory/<uuid:subcategory_id>/worker/<uuid:worker_id>/', view_subcategory_detail_worker, name='subcategory_detail_worker'),
    path('check_ids/', check_all_ids, name='check_ids'),
    path('subcategory/<uuid:subcategory_id>/worker/<uuid:worker_id>/join/', join_subcategory, name='join_subcategory'),
    path('subcategory/<uuid:subcategory_id>/worker/<uuid:worker_id>/leave/', leave_subcategory, name='leave_subcategory'),



]
