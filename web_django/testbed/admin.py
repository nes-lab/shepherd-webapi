from django.contrib import admin

from .models import Controller
from .models import Gpio
from .models import Observer
from .models import Target


@admin.register(Gpio)
class AdminGpio(admin.ModelAdmin):
    list_filter = (
        "direction",
        "dir_switch",
    )
    list_display = (
        "name",
        "direction",
        "dir_switch",
        "pin_pru",
        "pin_sys",
    )
    search_fields = (
        "name",
        "direction",
        "dir_switch",
        "pin_pru",
        "pin_sys",
    )
    ordering = ("name",)
    filter_horizontal = ()


@admin.register(Controller)
class AdminController(admin.ModelAdmin):
    list_filter = ("platform", "core", "programmer")
    list_display = (
        "name",
        "platform",
        "core",
        "programmer",
    )
    search_fields = (
        "name",
        "core",
        "programmer",
    )
    ordering = ("name",)
    filter_horizontal = ()


@admin.register(Target)
class AdminTarget(admin.ModelAdmin):
    list_filter = ("controller1", "controller2")
    list_display = (
        "name",
        "controller1",
        "controller2",
    )
    search_fields = (
        "name",
        "controller1",
        "controller2",
    )
    ordering = ("name",)
    filter_horizontal = ()


@admin.register(Observer)
class AdminObserver(admin.ModelAdmin):
    list_filter = ("room",)
    list_display = (
        "name",
        "room",
        "eth_port",
        "ip",
        "mac",
        "target_a_id",
        "target_b_id",
        "alive_last",
        "created",
    )
    search_fields = ("name", "ip", "mac", "room")
    ordering = ("name",)
    filter_horizontal = ()
