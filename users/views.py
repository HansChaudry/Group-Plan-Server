import json
from django.contrib.auth import login, logout, authenticate
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import QuerySet
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm
from http import HTTPStatus
from django.forms.models import model_to_dict
from django.core.validators import validate_email
from django.core import serializers
# Create your views here.

from .models import CustomUser

def _create_message(msg: str):
    return json.dumps({"message": msg})

def register(request):
    user_info: dict = json.loads(request.body)
    form = CustomUserCreationForm(user_info)
    if form.is_valid():
        form.save()
        users_query: QuerySet = CustomUser.objects.filter(username__icontains=user_info.get("username"))
        users = serializers.serialize("json", users_query)
        return HttpResponse(users)
    return HttpResponse(json.dumps(form.errors.get_json_data()))


def userLogIn(request):

    user_info: dict = json.loads(request.body)
    # form = AuthenticationForm(request.POST)
    user = authenticate(
        username=user_info.get("username"),
        password=user_info.get('password'))
    if user is not None:
        login(request, user)
        return JsonResponse(json.loads(serializers.serialize('json', [user]).strip('[]')))
    return HttpResponse(json.dumps({'message': "Please enter a correct username and password.\n\nNote that both "
                                               "fields may be case-sensitive."}))
# return HttpResponse(json.dumps({'message': form.get_invalid_login_error().__str__().strip('[]').strip("''")}))


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
        return HttpResponse(_create_message("User Not Found"), status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        print(e)
        return HttpResponse(_create_message("Invalid Request"), status=HTTPStatus.BAD_REQUEST)


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
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    update_info: dict = json.loads(request.body)
    update_type = update_info.get("type")
    if not update_type:
        return HttpResponse(_create_message("Missing Update Type"), status=HTTPStatus.BAD_REQUEST)
    try:
        user_info: dict = update_info.get("user_info")
        if not user_info:
            return HttpResponse(_create_message("Missing New Info"), status=HTTPStatus.BAD_REQUEST)
        django_user = request.user
        if update_type == "email":
            new_email: str = user_info.get("email")
            django_user.email = new_email
        elif update_type == "username":
            new_username: str = user_info.get("username")
            django_user.username = new_username
        else:
            return HttpResponse(_create_message("Invalid Request"), status=HTTPStatus.BAD_REQUEST)
        django_user.save()
        return HttpResponse(json.dumps(model_to_dict(django_user), default=str), status=HTTPStatus.OK)
    except ObjectDoesNotExist:
        return HttpResponse(_create_message("User not found."), status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        print(e)
        return HttpResponse(_create_message("Invalid Request"), status=HTTPStatus.BAD_REQUEST)


def user(request: HttpRequest):
    if request.method == 'PUT':
        return updateUser(request)
    return HttpResponse(_create_message("Invalid Method"), status=HTTPStatus.METHOD_NOT_ALLOWED)