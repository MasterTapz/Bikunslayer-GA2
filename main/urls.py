from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path("register/", views.register, name="register"),
    path("register_user/", views.register_user, name="register_user"),
    path("register_worker/", views.register_worker, name="register_worker"),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path("profile/user/", views.user_profile, name="user_profile"),
    path("profile/worker/", views.worker_profile, name="worker_profile"),
    path("homepage/", views.homepage, name="homepage"),
]
