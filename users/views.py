import json
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import QuerySet
from django.http import JsonResponse, HttpRequest
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm
from django.http import HttpResponse
from django.core import serializers
from http import HTTPStatus
from django.forms.models import model_to_dict
from django.core.validators import validate_email
from django.core import serializers
# Create your views here.
from .models import CustomUser


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


def searchUser(request: HttpRequest, user_info: str):
    try:
        try:
            validate_email(user_info)
            user = CustomUser.objects.get(email=user_info)
            user = model_to_dict(user)
            return HttpResponse(json.dumps(user, default=str))
        except ValidationError:
            users_query: QuerySet = CustomUser.objects.filter(username__icontains=user_info)
            users = serializers.serialize("json", users_query)
            return HttpResponse(users)
    except ObjectDoesNotExist:
        return HttpResponse(None, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        print(e)
        return HttpResponse("Invalid Request", status=HTTPStatus.BAD_REQUEST)


def updateUser(request: HttpRequest):
    '''
    update_info {
        type: username or email,
        user_info: {
            id: user_id
            username/email: updated_info
        }
    }
    '''

    update_info: dict = json.loads(request.body)
    update_type = update_info.get("type")
    if not update_type:
        return HttpResponse("Invalid Request", status=HTTPStatus.BAD_REQUEST)
    try:
        user_info: dict = update_info.get("user_info")
        user_id = user_info.get("id")
        if not user_info or not user_id:
            return HttpResponse("Invalid Request", status=HTTPStatus.BAD_REQUEST)
        user = CustomUser.objects.get(id=user_id)
        if update_type == "email":
            new_email: str = user_info.get("email")
            user.email = new_email
        elif update_type == "username":
            new_username: str = user_info.get("username")
            user.username = new_username
        else:
            return HttpResponse("Invalid Request", status=HTTPStatus.BAD_REQUEST)
        user.save()
        return HttpResponse("Updated User", status=HTTPStatus.OK)
    except ObjectDoesNotExist:
        return HttpResponse("Invalid Request", status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        print(e)
        return HttpResponse("Invalid Request", status=HTTPStatus.BAD_REQUEST)


def user(request: HttpRequest):
    if request.method == 'PUT':
        return updateUser(request)
    return HttpResponse("Invalid Method", status=HTTPStatus.METHOD_NOT_ALLOWED)