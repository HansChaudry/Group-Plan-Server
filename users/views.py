import json
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render
from .forms import CustomUserCreationForm
from django.http import HttpResponse
# Create your views here.

def register(request):
    form = CustomUserCreationForm(request.POST)
    if form.is_valid():
        form.save()
        return HttpResponse(json.dumps({'message': 'User has was created'}))
    return HttpResponse(json.dumps(form.errors.get_json_data()))

def userLogIn(request):
    if request.method == 'POST':
        user = authenticate(
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user is not None:
            login(request, user)
            return HttpResponse(json.dumps({'message': 'User logged in'}))
    return HttpResponse(json.dumps({'message': 'Error'}))

def userLogOut(request):
    logout(request)
    return HttpResponse(json.dumps({'message': 'User logged out'}))
