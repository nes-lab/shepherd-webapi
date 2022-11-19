# from django.contrib.auth import views as admin_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="testbed"),
    path("observers", views.ObserversView.as_view(), name="observer-all"),
    path("observer/add", views.observer_add, name="observer-add"),
    path("observer/<str:observer_name>", views.observer_view, name="observer-view"),
    path(
        "observer/<str:observer_name>/change",
        views.observer_change,
        name="observer-change",
    ),
]


# want something like
# /testbed/observer -> Overview
# /testbed/observer/sheep0 -> element view
# /testbed/observer/sheep0/change -> element manipulation
# /testbed/observer/add -> element creation
