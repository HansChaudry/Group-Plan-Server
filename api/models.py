from django.db import models
from django.contrib.auth.models import Group


# Create your models here.
class Recipe(models.Model):
    name = models.CharField(max_length=255)


class RecipeGroup(models.Model):
    django_group = models.OneToOneField(Group, unique=True, on_delete=models.CASCADE)
    current_recipe = models.OneToOneField(Recipe, unique=True, on_delete=models.SET_NULL, null=True)
