from django.urls import path
from . import views

#URLConf
urlpatterns = [
    path(r'register/', views.register),
    # path(r'login/', views.userLogIn),
    # path(r'logout/', views.userLogOut)
]