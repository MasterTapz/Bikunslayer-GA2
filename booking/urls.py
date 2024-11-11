# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.category_view, name='category_view'),
]
