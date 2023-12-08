import datetime
from http import HTTPStatus
import random
import os
from azure.storage.blob import BlobServiceClient
from django.forms.models import model_to_dict
import json
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group
from users.models import CustomUser
from .models import RecipeGroup, Recipe, Vote, PollRecipe
from django.core import serializers
from django.db.models import QuerySet, Q, Count
from django.utils import timezone
from dotenv import load_dotenv
from django.http import HttpResponse, HttpRequest

load_dotenv()
#TODO: double check for bugs and refactor routes

#TODO: MAJOR TASK
#TODO: CHECK IF THE POLL FINISHED.
# Might have to be checked within many routes, but mainly the get user groups route.
# After the poll is finished.
# All the poll recipes for that group should be removed, all the votes should be removed,
# the boolean value "current_poll" should be set to false,
# the current_poll_time property set to null,
# and the the current recipe is update to the recipe with the most votes from the poll.
# In the event of a tie, the recipe is chosen randomly

def _create_message(msg: str):
    return json.dumps({"message": msg})


def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")


def add_user_to_group(request: HttpRequest):
    """
        Returns the group that the user joined
    """
    if not request.user.is_authenticated:
        print(request.user)
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    if request.method != "POST":
        return HttpResponse(_create_message("Invalid Method"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    info: dict = json.loads(request.body)
    group_id = info.get("group_id")
    if not group_id:
        return HttpResponse(_create_message("Missing Group ID"), status=HTTPStatus.BAD_REQUEST)
    try:
        user = request.user
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=group_id)
        django_group = recipe_group.django_group
        django_group.user_set.add(user)
        recipe_group_json = model_to_dict(recipe_group)
        return HttpResponse(json.dumps(recipe_group_json, default=str))
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User/Group Not Found"), status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse(_create_message("Unknown Error"), status=HTTPStatus.INTERNAL_SERVER_ERROR)


def _reset_user_group(user, recipe_group: RecipeGroup, django_group: Group):
    if recipe_group.owner_id == user.id:
        users = [u for u in django_group.user_set.values() if u["id"] != user.id]
        if users:
            new_owner = random.choice(users)
            new_owner_custom = CustomUser.objects.get(id=new_owner["id"])
            recipe_group.owner = new_owner_custom
            recipe_group.save()
        else:
            recipe_group.delete()
    PollRecipe.objects.filter(user=user, recipe_group=recipe_group).delete()
    Vote.objects.filter(user=user, recipe_group=recipe_group).delete()
    django_group.user_set.remove(user)


def remove_user_from_group(request: HttpRequest):
    """
        Returns "User Removed" if the user was succesfully removed 
    """
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
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=group_id)
        django_group = recipe_group.django_group
        _reset_user_group(request.user, recipe_group, django_group)
        return HttpResponse(_create_message("User Removed"))
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User/Group Not Found"), status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse(_create_message("Unknown Error"), status=HTTPStatus.INTERNAL_SERVER_ERROR)


def create_group(request: HttpRequest):
    """
        Returns a information about a group, that was created
    """
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
    """
        Returns a list containing groups where the name contains group_info in their name, and where the user is not in the group's user set
    """
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    if request.method != 'GET':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    try:
        user = request.user
        groups = user.groups.all()
        groupNames = []
        for group in groups:
            groupNames.append(group.name)
        recipeGroupsQuery: QuerySet = (RecipeGroup.objects.filter(~Q(name__in=groupNames), name__contains=group_info)
                                    .order_by('name'))
        recipeGroups = serializers.serialize("json", recipeGroupsQuery)
        return HttpResponse(recipeGroups, status=HTTPStatus.OK)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("No groups found"), status=HTTPStatus.BAD_REQUEST)


def get_user_groups(request: HttpRequest):
    """
        Returns of the user's gorups include the groups current recipe name
    """
    if request.method != 'GET':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        user = request.user
        groups = user.groups.all()
        groupNames = []
        for group in groups:
            groupNames.append(group.name)
        recipeGroupsQuery: QuerySet = RecipeGroup.objects.select_related("current_recipe").filter(
            name__in=groupNames).order_by('name')
        groups=[]
        for recipeGroup in recipeGroupsQuery:
            temp = model_to_dict(recipeGroup)
            if(recipeGroup.current_recipe):
                temp["current_recipe_name"] = recipeGroup.current_recipe.name
            else:
                temp["current_recipe_name"] = "None"
            groups.append(temp)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group/Recipe Not Found"), status=HTTPStatus.BAD_REQUEST)

    return HttpResponse(json.dumps(groups, default=str), status=HTTPStatus.OK)



def start_Poll(request: HttpRequest, groupId: int):
    """
        returns "Poll Started" if the current_poll property was succesfully set to true and the current poll time is set be 24 hours from now
    """
    if request.method != 'PUT':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        recipeGroupQuery: QuerySet = RecipeGroup.objects.filter(id=groupId)
        group = recipeGroupQuery.get(id=groupId)
        group.current_poll = True
        group.current_poll_time = timezone.now() + timezone.timedelta(hours=24)
        group.save()
        return HttpResponse(_create_message("Poll started"), status=HTTPStatus.OK)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group Not Found"), status=HTTPStatus.BAD_REQUEST)


def get_group_members(request: HttpRequest, groupId: int):
    """
        returns all the group members
    """
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
    """
        returns all information about a specific group
    """
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


def uploadImg(fileName, file):
    """
        uploads recipe image file to azure blobs and returns the link to the image for public reference by client
    """
    connect_str = os.getenv('CONNSTR') 
    container_name = "photos"

    blob_service_client = BlobServiceClient.from_connection_string(conn_str=connect_str) 
    try:
        container_client = blob_service_client.get_container_client(container=container_name) 
        container_client.get_container_properties() 
    
    except Exception as e:
        container_client = blob_service_client.create_container(container_name) 
    imgageURL = container_client.upload_blob(fileName, file).url
    blob_service_client.close()
    return imgageURL

# RECIPE ROUTES
def create_recipe(request: HttpRequest):
    """
        Returns "Recipe Created" if the recipe was succefully created under the user 
    """
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    recipe_name = request.POST.get('recipe_name')
    recipe_ingredients = request.POST.get('recipe_ingredients')
    recipe_instructions = request.POST.get('recipe_instructions')
    recipe_image = request.FILES.getlist("imageFile")
    user = request.user
    recipe_image_url = ''
    if(len(recipe_image)):
        recipe_image_url = uploadImg((user.username + "_" +recipe_name), recipe_image[0])
    duplicate = getDuplicateRecipe(user, recipe_name)
    try:
        user = request.user
        if not duplicate:
            Recipe.objects.create(name=recipe_name, owner=user,
                                  ingredients=recipe_ingredients, instructions=recipe_instructions, recipe_image=recipe_image_url)
        else:
            return HttpResponse(_create_message("Duplicate Recipe Name"), status=HTTPStatus.BAD_REQUEST)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("User Not Found"), status=HTTPStatus.BAD_REQUEST)
    return HttpResponse("Recipe Created")


def get_user_recipes(request: HttpRequest):
    """
        Retunrns a list containing all of the user's recipes 
    """
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
    """
        Returns Json model of the desired recipe
    """
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
    """
        returns duplicate recipe if one exist
    """
    return Recipe.objects.filter(owner=userName).filter(name=recipeName)

def hasVote(user, group, recipe_id) -> QuerySet:
    """
        returns a user's vote for the current poll if they have one
    """
    return Vote.objects.filter(~Q(recipe_id=recipe_id),recipe_group=group, user=user)
#Poll Routes
def add_vote(request: HttpRequest, groupId: int):
    """
        Returns dictionary of the user's vote for the current poll
    """
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
    """
        returns the user's poll recipe if it successfully added to the group
    """
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
    """
        returns a list containing all the votes for the current poll
    """
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
    """
        Returns a list of the recipes user's can vote for under the current poll
    """
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
    """
        Returns a dictionary that summarizes the distribution of votes for the current poll
    """
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
    """
        Returns a json of containing the number of group members and the summary of vote distributions
    """
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


def _reset_poll(recipe_group: RecipeGroup, votes: QuerySet[Vote]):
    most_voted = votes.values("recipe_id").annotate(recipe_count=Count("recipe_id")).order_by("-recipe_count")

    if most_voted.count() is None or most_voted.count() < 1:
        recipes = PollRecipe.objects.filter(recipe_group=recipe_group.id).all()
        if recipes.count() < 1:
            # Don't change the value of current recipe if there are no poll recipes for this group
            pass
        else:
            chosen_recipe = random.choice(list(recipes))
            recipe_group.current_recipe = Recipe.objects.get(id=chosen_recipe.recipe.id)
    else:
        max_count = max(most_voted, key=lambda x: x["recipe_count"])["recipe_count"]
        recipe_candidates = [vote for vote in most_voted if vote["recipe_count"] == max_count]
        chosen_recipe = random.choice(recipe_candidates)
        recipe = Recipe.objects.get(id=chosen_recipe["recipe_id"])
        recipe_group.current_recipe = recipe

    PollRecipe.objects.filter(recipe_group=recipe_group.id).delete()
    Vote.objects.filter(recipe_group=recipe_group.id).delete()
    recipe_group.current_poll = False
    recipe_group.current_poll_time = None
    recipe_group.save()
    return recipe_group.current_recipe


def get_poll_status(request: HttpRequest, group_id: int):
    # TODO: CHECK IF THE POLL FINISHED.
    # Might have to be checked within many routes, but mainly the get user groups route.
    # After the poll is finished.
    # All the poll recipes for that group should be removed, all the votes should be removed,
    # the boolean value "current_poll" should be set to false,
    # the current_poll_time property set to null,
    # and the the current recipe is update to the recipe with the most votes from the poll.
    # In the event of a tie, the recipe is chosen randomly
    if request.method != 'GET':
        return HttpResponse(_create_message("Bad Request"), status=HTTPStatus.METHOD_NOT_ALLOWED)
    if not request.user.is_authenticated:
        return HttpResponse(_create_message("Unauthorized"), status=HTTPStatus.UNAUTHORIZED)
    try:
        recipe_group: RecipeGroup = RecipeGroup.objects.get(id=group_id)
        current_poll_time = recipe_group.current_poll_time
        if not recipe_group.current_poll:
            return HttpResponse(_create_message("Poll not active"), status=HTTPStatus.OK)

        votes = Vote.objects.filter(recipe_group=recipe_group, current_poll_time=current_poll_time)
        user_count = recipe_group.django_group.user_set.count()
        vote_count = votes.count()
        current_poll_time = datetime.datetime.fromisoformat(current_poll_time.strftime("%Y-%m-%d %H:%M:%S"))
        current_time = datetime.datetime.now()
        poll_time_passed = current_poll_time < current_time

        if vote_count == user_count or poll_time_passed:
            recipe = _reset_poll(recipe_group, votes)
            return HttpResponse(json.dumps(model_to_dict(recipe), default=str), status=HTTPStatus.OK)
        else:
            message = {
                "votes": vote_count,
                "user_count": user_count,
                "poll_time": recipe_group.current_poll_time,
                "summary": Generate_Poll_Summary(votes)
            }
            return HttpResponse(json.dumps(message, default=str), status=HTTPStatus.OK)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return HttpResponse(_create_message("Group/Recipe Not Found"), status=HTTPStatus.BAD_REQUEST)