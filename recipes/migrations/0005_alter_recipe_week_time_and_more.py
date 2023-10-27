# Generated by Django 4.2.5 on 2023-10-27 14:53

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0004_recipe_ingredients_recipe_owner_recipe_vote_count_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='week_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='recipegroup',
            name='current_poll_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
