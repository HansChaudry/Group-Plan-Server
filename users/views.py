import json
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm
from django.http import HttpResponse
# Create your views here.

def register(request):
    form = CustomUserCreationForm(request.POST)
    if form.is_valid():
        form.save()
        return HttpResponse(json.dumps({'message': 'User has was created'}))
    return HttpResponse(json.dumps(form.errors.get_json_data()))

