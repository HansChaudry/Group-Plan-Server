from http import HTTPStatus

from django.forms.models import model_to_dict
import json
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group
from users.models import CustomUser
from .models import RecipeGroup, Recipe
from django.core import serializers
from django.db.models import QuerySet, Q

# Create your views here.
from django.http import HttpResponse, HttpRequest


def _create_message(msg: str):
    return json.dumps({"message": msg})


def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")


def add_user_to_group(request: HttpRequest):
    if not request.user.is_authenticated:
        print(request.user)
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    if request.method != "POST":
        return HttpResponse(_create_message("Invalid Method"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    info: dict = json.loads(request.body)
    user_id = info.get("user_id")
    group_id = info.get("group_id")
    if not user_id or not group_id:
        return HttpResponse(_create_message("Missing User ID or Group ID"), status=HTTPStatus.BAD_REQUEST)
    try:
        user: CustomUser = CustomUser.objects.get(id=user_id)
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=group_id)
        django_group = recipe_group.django_group
        django_group.user_set.add(user)
        recipe_json = model_to_dict(recipe_group)
        return HttpResponse(json.dumps(recipe_json, default=str))
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User/Group Not Found"), status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse(_create_message("Unknown Error"), status=HTTPStatus.INTERNAL_SERVER_ERROR)


def create_group(request: HttpRequest):
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    group_info: dict = json.loads(request.body)
    group_name = group_info.get('name')
    group_privacy = group_info.get('privacy')
    if not group_name or not group_privacy:
        return HttpResponse(_create_message("Missing Name or Privacy"), status=HTTPStatus.BAD_REQUEST)
    if group_privacy not in RecipeGroup.RecipePrivacy.values:
        return HttpResponse(_create_message("Invalid Privacy Option"), status=HTTPStatus.BAD_REQUEST)
    try:
        new_native_group: Group = Group.objects.create(name=group_name)
        user = request.user
        new_native_group.user_set.add(user)
        new_recipe_group: RecipeGroup = RecipeGroup.objects.create(name=group_name, privacy=group_privacy, owner=user,
                                                                   django_group=new_native_group)
        recipe_group = model_to_dict(new_recipe_group)
        return HttpResponse(json.dumps(recipe_group, default=str))
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User Not Found"), status=HTTPStatus.BAD_REQUEST)
    except IntegrityError:
        return HttpResponse(_create_message("Duplicate Group Name"), status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse(_create_message("Unknown Error"), status=HTTPStatus.INTERNAL_SERVER_ERROR)


def search_groups(request: HttpRequest, group_info: str):
    if request.method != 'GET':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    user = request.user
    groups = user.groups.all()
    groupNames = []
    for group in groups:
        groupNames.append(group.name)
    recipeGroupsQuery: QuerySet = (RecipeGroup.objects.filter(~Q(name__in=groupNames), name__contains=group_info)
                                   .order_by('name'))
    recipeGroups = serializers.serialize("json", recipeGroupsQuery)
    return HttpResponse(recipeGroups, status=HTTPStatus.OK)


def get_user_groups(request: HttpRequest):
    if request.method != 'GET':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    user = request.user
    groups = user.groups.all()
    groupNames = []
    for group in groups:
        groupNames.append(group.name)
    recipeGroupsQuery: QuerySet = RecipeGroup.objects.filter(name__in=groupNames).order_by('name')
    recipeGroups = serializers.serialize("json", recipeGroupsQuery)
    return HttpResponse(recipeGroups, status=HTTPStatus.OK)

def start_Poll(request: HttpRequest, groupId: int):
    if request.method != 'PUT':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)

    recipeGroupQuery: QuerySet = RecipeGroup.objects.filter(id=groupId)
    group = recipeGroupQuery.get(id=groupId)
    group.current_poll = True
    group.save()
    return HttpResponse(_create_message("Poll started"), status=HTTPStatus.OK)


def group(request: HttpRequest):
    if request.method == 'POST':
        return create_group(request)
    return HttpResponse(_create_message("Invalid Method"), status=HTTPStatus.METHOD_NOT_ALLOWED)


# RECIPE ROUTES
def create_recipe(request: HttpRequest):
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    recipe_info: dict = json.loads(request.body)
    recipe_name = recipe_info.get('recipe_name')
    recipe_ingredients = recipe_info.get('recipe_ingredients')
    recipe_instructions = recipe_info.get('recipe_instructions')
    user = request.user
    duplicate = getDuplicateRecipe(user, recipe_name)
    try:
        user = request.user
        if not duplicate:
            Recipe.objects.create(name=recipe_name, owner=user, ingredients=recipe_ingredients, instructions=recipe_instructions)
        else:
            return HttpResponse(_create_message("Duplicate Recipe Name"), status=HTTPStatus.BAD_REQUEST)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User Not Found"), status=HTTPStatus.BAD_REQUEST)
    return HttpResponse("Hello, you can create recipes soon!")


def get_user_recipes(request: HttpRequest):
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)

    try:
        user = request.user
        Recipe.objects.filter(owner=user)
        recipes_query: QuerySet = Recipe.objects.filter(owner=user).order_by('name')
        recipes = serializers.serialize("json", recipes_query)
        return HttpResponse(recipes)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User Not Found"), status=HTTPStatus.BAD_REQUEST)


def get_recipe(request: HttpRequest, recipeId: int):
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)

    try:
        recipes_query: QuerySet = Recipe.objects.filter(id=recipeId).order_by('name')
        recipe = serializers.serialize("json", recipes_query)

        return HttpResponse(recipe)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User Not Found"), status=HTTPStatus.BAD_REQUEST)

def getDuplicateRecipe(userName, recipeName: str) -> QuerySet:
    return Recipe.objects.filter(owner=userName).filter(name=recipeName)
