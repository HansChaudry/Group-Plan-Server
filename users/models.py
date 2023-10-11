from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


class CustomUser(AbstractUser):
    votedRecipe = models.IntegerField(default=0, null=True)
    email = models.EmailField('email address', blank=False)