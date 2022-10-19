from django.urls import path

from . import views

urlpatterns = [
    path("", views.experiments, name="experiments"),
    path("<int:experiment_id>/", views.experiment, name="experiment"),
]
