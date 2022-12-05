from django.contrib.auth import views as admin_views
from django.urls import path

from . import views

urlpatterns = [
    path("login/", admin_views.LoginView.as_view(), name="login"),
    path("logout/", admin_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.user_signup, name="signup"),
    path("profile/", views.profile, name="profile"),
    path(
        "password-change/",
        admin_views.PasswordChangeView.as_view(
            template_name="accounts/password_change_form.html",
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        admin_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html",
        ),
        name="password_change_done",
    ),
]
