from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("group/", views.group),
    path("group/add", views.add_user_to_group)
]