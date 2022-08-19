from django.urls import path
from django.contrib.auth import views as admin_views
from . import views

urlpatterns = [
    path("", views.observer_add, name="testbed"),
]
