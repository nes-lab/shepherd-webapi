from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import User


class UserAdmin(BaseUserAdmin):
    list_filter = ("is_staff",)
    search_fields = ("username",)
    ordering = ("username",)
    filter_horizontal = ()


admin.site.register(User, UserAdmin)
