import json
from http import HTTPStatus

from django.forms.models import model_to_dict
import json
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group
from users.models import CustomUser
from .models import RecipeGroup

# Create your views here.
from django.http import HttpResponse, HttpRequest


def index(request):
    print(CustomUser.objects.all())
    return HttpResponse("Hello, world. You're at the polls index.")


def create_group(request: HttpRequest):
    group_info: dict = json.loads(request.body)
    group_name = group_info.get('name')
    group_privacy = group_info.get('privacy')
    user_id = group_info.get('user_id')
    if not group_name or not group_privacy or not user_id:
        return HttpResponse("Missing Name or Privacy or User", status=HTTPStatus.BAD_REQUEST)
    if group_privacy not in RecipeGroup.RecipePrivacy.values:
        return HttpResponse("Invalid Privacy Option", status=HTTPStatus.BAD_REQUEST)
    try:
        new_native_group: Group = Group.objects.create(name=group_name)
        user: CustomUser = CustomUser.objects.get(id=user_id)
        new_native_group.user_set.add(user)
        new_recipe_group: RecipeGroup = RecipeGroup.objects.create(name=group_name, privacy=group_privacy, owner=user, django_group=new_native_group)
        recipe_group = model_to_dict(new_recipe_group)
        return HttpResponse(json.dumps(recipe_group, default=str))
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse("User Not Found", status=HTTPStatus.BAD_REQUEST)
    except IntegrityError:
        return HttpResponse("Duplicate Group Name", status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse("Unknown Error", status=HTTPStatus.INTERNAL_SERVER_ERROR)


def group(request: HttpRequest):
    if request.method == 'POST':
        return create_group(request)
    return HttpResponse("Invalid Method", status=HTTPStatus.METHOD_NOT_ALLOWED)