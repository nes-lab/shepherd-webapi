from django.contrib.auth import views as admin_views
from django.urls import path

from . import views

urlpatterns = [
    path("observers", views.ObserversView.as_view(), name="observer-list"),
    path("", views.observer_add, name="testbed"),
]
