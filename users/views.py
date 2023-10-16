import json
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.http import JsonResponse, HttpRequest
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm
from django.http import HttpResponse
from django.core import serializers
from http import HTTPStatus
from django.forms.models import model_to_dict
from .models import CustomUser
# Create your views here.


def register(request):
    form = CustomUserCreationForm(request.POST)
    if form.is_valid():
        form.save()
        return HttpResponse(json.dumps({'message': 'User has was created'}))
    return HttpResponse(json.dumps(form.errors.get_json_data()))


def userLogIn(request):
    form = AuthenticationForm(request.POST)
    user = authenticate(
        username=request.POST.get('username'),
        password=request.POST.get('password')
    )
    if user is not None:
        login(request, user)
        return JsonResponse(json.loads(serializers.serialize('json', [user]).strip('[]')))
    return HttpResponse(json.dumps({'message': form.get_invalid_login_error().__str__().strip('[]')}))


def userLogOut(request):
    logout(request)
    return HttpResponse(json.dumps({'message': 'User logged out'}))


def searchUser(request: HttpRequest):
    UserModel = get_user_model()
    username = request.GET.get('username')
    email = request.GET.get('email')
    if (username and email) or (not username and not email):
        return HttpResponse("Invalid Request", status=HTTPStatus.BAD_REQUEST)
    user = None
    if username:
        user = UserModel.objects.get(username=username)
    if email:
        user = UserModel.objects.get(email=email)
    user = model_to_dict(user)
    return HttpResponse(json.dumps(user, default=str))
