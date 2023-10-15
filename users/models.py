from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.


class CustomUser(AbstractUser):
    votedRecipe = models.IntegerField(default=0, null=True)
    email = models.EmailField('email address', blank=False, unique=True)
    first_name = models.CharField('first name', blank=False)
    last_name = models.CharField('last name', blank=False)