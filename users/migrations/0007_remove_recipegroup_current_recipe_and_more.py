# Generated by Django 4.2.5 on 2023-10-24 21:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_recipegroup_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='recipegroup',
            name='current_recipe',
        ),
        migrations.RemoveField(
            model_name='recipegroup',
            name='django_group',
        ),
        migrations.DeleteModel(
            name='Recipe',
        ),
        migrations.DeleteModel(
            name='RecipeGroup',
        ),
    ]
