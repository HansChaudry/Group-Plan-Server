from django.db import models
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from users.models import CustomUser
from django.contrib.postgres.fields import ArrayField
import datetime
from django.utils import timezone


# Create your models here.
class Recipe(models.Model):
    name = models.CharField(max_length=255)
    ingredients = models.CharField(null=False, default="[]", max_length=2048)
    instructions = models.CharField(null=False, default="[]", max_length=2048)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    django_group = models.OneToOneField(Group, on_delete=models.DO_NOTHING, null=True)
    week_time = models.DateTimeField(null=True)
    vote_count = models.IntegerField(default=0, null=False, validators=[MinValueValidator(0)])
    recipe_image = models.CharField(max_length=255, null=True)


class RecipeGroup(models.Model):
    # https://stackoverflow.com/questions/54802616/how-can-one-use-enums-as-a-choice-field-in-a-django-model
    # https://docs.djangoproject.com/en/4.2/ref/models/fields/#field-choices-enum-types
    class RecipePrivacy(models.TextChoices):
        PUBLIC = "PUBLIC", _("PUBLIC")
        PRIVATE = "PRIVATE", _("PRIVATE")

    name = models.CharField(max_length=300, default="Recipe Group")
    privacy = models.CharField(max_length=10, choices=RecipePrivacy.choices, default=RecipePrivacy.PRIVATE)
    current_poll_time = models.DateTimeField(null=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, null=True)
    django_group = models.OneToOneField(Group, unique=True, on_delete=models.CASCADE)
    current_recipe = models.OneToOneField(Recipe, unique=True, on_delete=models.SET_NULL, null=True)
    current_poll = models.BooleanField(default=0, null=True)


class Vote(models.Model):
    recipe_group = models.ForeignKey(RecipeGroup, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True)
    current_poll_time = models.DateTimeField(null=True) # Should be the same time as the group poll time


class PollRecipe(models.Model):
    current_poll_time = models.DateTimeField(null=True) # Should be the same time as the group poll time
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, null=True)
    recipe_group = models.ForeignKey(RecipeGroup, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
