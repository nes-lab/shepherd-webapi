from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

# from django.shortcuts import render
from django.views.decorators.http import require_http_methods

User = get_user_model()


@login_required(login_url="/accounts/login/")
@require_http_methods(["GET"])
def experiments(request):
    return HttpResponse(
        "This will be the overview and management screen for experiments",
    )


@login_required(login_url="/accounts/login/")
@require_http_methods(["POST", "GET"])
def experiment(request):
    return HttpResponse(
        "This will be the overview and management screen for experiments",
    )
