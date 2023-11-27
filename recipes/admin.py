from django.contrib import admin
from .models import Recipe, RecipeGroup, Vote, PollRecipe

# Register your models here.

admin.site.register(Recipe)
admin.site.register(RecipeGroup)
admin.site.register(Vote)
admin.site.register(PollRecipe)