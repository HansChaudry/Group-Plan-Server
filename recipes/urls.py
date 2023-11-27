from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("group/", views.group),
    path("group/get/<str:groupId>", views.get_group_info),
    path("group/add", views.add_user_to_group),
    path("group/members/<str:groupId>", views.get_group_members),
    path('searchGroups/<str:group_info>/', views.search_groups),
    path('getUserGroups/', views.get_user_groups),
    path('createRecipe/', views.create_recipe),
    path('getUserRecipes/', views.get_user_recipes),
    path('getRecipe/<str:recipeId>/', views.get_recipe),
    path('startPoll/<str:groupId>/', views.start_Poll),
    path('addVote/<str:groupId>/', views.add_vote),
    path('addRecipe/<str:groupId>', views.add_recipe_to_poll),
    path('getPoll/recipes/<str:groupId>', views.get_poll_recipes),
    path('getPoll/votes/<str:groupId>', views.get_poll_votes),
    path('getPoll/summary/<str:groupId>', views.get_poll_summary)
]