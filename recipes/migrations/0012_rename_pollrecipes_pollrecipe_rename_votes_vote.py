# Generated by Django 4.2.5 on 2023-11-27 01:07

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recipes', '0011_alter_recipe_week_time_pollrecipes'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PollRecipes',
            new_name='PollRecipe',
        ),
        migrations.RenameModel(
            old_name='Votes',
            new_name='Vote',
        ),
    ]
