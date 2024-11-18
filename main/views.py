from django.shortcuts import render

def main(request):
    return render(request, 'main.html')

def login(request):
    return render(request, 'login.html')

def register(request):
    return render(request, 'register.html')

def user_profile(request):
    return render(request, 'user_profile.html')

def worker_profile(request):
    return render(request, 'worker_profile.html')

