import datetime
from http import HTTPStatus
import random

from django.forms.models import model_to_dict
import json
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group
from users.models import CustomUser
from .models import RecipeGroup, Recipe, Vote, PollRecipe
from django.core import serializers
from django.db.models import QuerySet, Q
from django.utils import timezone

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
    
def remove_user_from_group(request: HttpRequest):
    if not request.user.is_authenticated:
        print(request.user)
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    if request.method != "PUT":
        return HttpResponse(_create_message("Invalid Method"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    info: dict = json.loads(request.body)
    group_id = info.get("group_id")
    if not group_id:
        return HttpResponse(_create_message("Missing Group ID"), status=HTTPStatus.BAD_REQUEST)
    try:
        # user: CustomUser = CustomUser.objects.get(id=user_id)
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=group_id)
        django_group = recipe_group.django_group
        django_group.user_set.remove(request.user)
        # recipe_json = model_to_dict(recipe_group)
        return HttpResponse(_create_message("User Removed"))
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
    recipeGroupsQuery: QuerySet = RecipeGroup.objects.filter(
        name__in=groupNames).order_by('name')
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
    group.current_poll_time = timezone.now()
    group.save()
    return HttpResponse(_create_message("Poll started"), status=HTTPStatus.OK)


def get_group_members(request: HttpRequest, groupId: int):
    if not request.method == 'GET':
        return HttpResponse(_create_message("Invalid Method"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Not Authorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=groupId)
        django_group: Group = recipe_group.django_group
        users = django_group.user_set.all().values("pk", "username", "first_name", "last_name", "email", "votedRecipe", "profileIMG")
        return HttpResponse(json.dumps(list(users), default=str), content_type="application/json")
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group does not exist"), status=HTTPStatus.BAD_REQUEST)


def get_group_info(request: HttpRequest, groupId: int):
    if not request.method == 'GET':
        return HttpResponse(_create_message("Invalid Method"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Not Authorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=groupId)
        recipe_group = model_to_dict(recipe_group)
        return HttpResponse(json.dumps(recipe_group, default=str), content_type="application/json")
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group does not exist"), status=HTTPStatus.BAD_REQUEST)


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
            Recipe.objects.create(name=recipe_name, owner=user,
                                  ingredients=recipe_ingredients, instructions=recipe_instructions)
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
        recipes_query: QuerySet = Recipe.objects.filter(
            owner=user).order_by('name')
        recipes = serializers.serialize("json", recipes_query)
        return HttpResponse(recipes)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User Not Found"), status=HTTPStatus.BAD_REQUEST)


def get_recipe(request: HttpRequest, recipeId: int):
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)

    try:
        recipes_query: QuerySet = Recipe.objects.filter(
            id=recipeId).order_by('name')
        recipe = serializers.serialize("json", recipes_query)

        return HttpResponse(recipe)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User Not Found"), status=HTTPStatus.BAD_REQUEST)


def getDuplicateRecipe(userName, recipeName: str) -> QuerySet:
    return Recipe.objects.filter(owner=userName).filter(name=recipeName)

def hasVote(user, group, recipe_id) -> QuerySet:
    return Vote.objects.filter(~Q(recipe_id=recipe_id),recipe_group=group, user=user)
#Poll Routes
def add_vote(request: HttpRequest, groupId: int):
    if request.method != 'PUT':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        vote_info: dict = json.loads(request.body)
        recipe_id = vote_info.get("recipe_id")
        user = request.user
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=groupId)
        recipe: Recipe = Recipe.objects.get(id=recipe_id)
        poll_time = recipe_group.current_poll_time
        # _ is an "is created" boolean, overwrites any existing vote
        user_vote, _ = Vote.objects.get_or_create(user=user, recipe_group=recipe_group, current_poll_time=poll_time)
        if(hasVote(user, recipe_group, recipe_id)):
            Vote.objects.filter(~Q(recipe_id=recipe_id),user=user, recipe_group=recipe_group).delete()
        user_vote, _ = Vote.objects.get_or_create(user=user, recipe_group=recipe_group, current_poll_time=poll_time)
        user_vote.user = user
        user_vote.recipe_group = recipe_group
        user_vote.recipe = recipe
        user_vote.current_poll_time = poll_time
        user_vote.save()
        return HttpResponse(json.dumps(model_to_dict(user_vote), default=str), status=HTTPStatus.OK)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group/Recipe Not Found"), status=HTTPStatus.BAD_REQUEST)


def add_recipe_to_poll(request: HttpRequest, groupId: int):
    if request.method != 'PUT':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        vote_info: dict = json.loads(request.body)
        recipe_id = vote_info.get("recipe_id")
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=groupId)
        recipe: Recipe = Recipe.objects.get(id=recipe_id)
        poll_time = recipe_group.current_poll_time

        # _ is an "is created" boolean
        user_poll_recipe, _ = PollRecipe.objects.get_or_create(recipe=recipe, recipe_group=recipe_group, current_poll_time=poll_time, user=request.user)
        user_poll_recipe.save()
        return HttpResponse(json.dumps(model_to_dict(user_poll_recipe), default=str), status=HTTPStatus.OK)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group/Recipe Not Found"), status=HTTPStatus.BAD_REQUEST)




def get_poll_votes(request: HttpRequest, groupId: int):
    if request.method != 'GET':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=groupId)
        poll_time = recipe_group.current_poll_time
        votes = Vote.objects.filter(recipe_group=recipe_group, current_poll_time=poll_time).values()
        return HttpResponse(json.dumps(list(votes), default=str), status=HTTPStatus.OK)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group/Recipe Not Found"), status=HTTPStatus.BAD_REQUEST)

def get_poll_recipes(request: HttpRequest, groupId: int):
    if request.method != 'GET':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=groupId)
        poll_time = recipe_group.current_poll_time
        poll_recipes = PollRecipe.objects.prefetch_related("recipe").filter(recipe_group=recipe_group, current_poll_time=poll_time).all()
        recipe_list = []
        for recipe in poll_recipes:
            temp = model_to_dict(recipe)
            temp["recipeName"] = recipe.recipe.name
            recipe_list.append(temp)
        return HttpResponse(json.dumps(recipe_list, default=str), status=HTTPStatus.OK)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group/Recipe Not Found"), status=HTTPStatus.BAD_REQUEST)
    
def Generate_Poll_Summary(voteList):
    summary= {"N/A 1":{"id":0, "votes":0},"N/A 2":{"id":0, "votes":0}, "N/A 3":{"id":0, "votes":0}}
    for vote in voteList:
        recipeName = vote.recipe.name
        if(recipeName in summary):
            summary[recipeName] = {"id":vote.recipe.pk, "votes": summary[recipeName]["votes"]+1}
        else:
            summary[recipeName] = {"id":vote.recipe.pk, "votes": 1}
    summary = dict(sorted(summary.items(), key=lambda x: x[1]["votes"], reverse=True))
    return summary

def get_poll_summary(request: HttpRequest, groupId: int):
    if request.method != 'GET':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=groupId)
        user_count = recipe_group.django_group.user_set.count()
        poll_time = recipe_group.current_poll_time
        votes = Vote.objects.filter(recipe_group=recipe_group, current_poll_time=poll_time).select_related('recipe').all()
        summary = {"user_count":user_count, "summary":Generate_Poll_Summary(votes)}
        return HttpResponse(json.dumps(summary, default=str), status=HTTPStatus.OK)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group/Recipe Not Found"), status=HTTPStatus.BAD_REQUEST)
    