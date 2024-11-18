from django.urls import path
from main.views import main,login,register,user_profile,worker_profile

urlpatterns = [
    path('', main, name='main'),
    path('login/', login, name='login'),
    path('register/', register, name='register'),
    path('user_profile/', user_profile, name='user_profile'),
    path('worker_profile/', worker_profile, name='worker_profile'),
]
