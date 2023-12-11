from django.contrib.auth import get_user_model

# from django.db.models import Count
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import RegisterForm

User = get_user_model()


@require_http_methods(["POST", "GET"])
def user_signup(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect("login")

    form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET"])
def profile(request):
    return render(request, "accounts/profile.html")
