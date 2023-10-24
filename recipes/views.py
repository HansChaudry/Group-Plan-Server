import json
from http import HTTPStatus

from django.shortcuts import render
from users.models import CustomUser

# Create your views here.
from django.http import HttpResponse, HttpRequest


def index(request):
    print(CustomUser.objects.all())
    return HttpResponse("Hello, world. You're at the polls index.")


def create_group(request: HttpRequest):
    group_info: dict = json.loads(request.body)

    pass


def group(request: HttpRequest):
    if request.method == 'POST':
        return create_group(request)
    return HttpResponse("Invalid Method", status=HTTPStatus.METHOD_NOT_ALLOWED)