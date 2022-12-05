from django.db import models

from .model_Controller import Controller


class Target(models.Model):
    """
    Target-Boards are connected to the :model:`testbed.Observer` via one of two target-ports.
    Each Target-PCB can contain up to two MCUs (:model:`testbed.Controller`).
    This novel approach has multiple benefits:\n
    - one observer could utilize more than 2 MCUs
      (unused MCUs would receive a sleep-firmware)
    - a Target can use one MCU for processing and another one would
      be used as a radio or FRAM (MSP430FR)
    """

    name = models.SlugField(
        max_length=30,
        primary_key=True,
        verbose_name="Name of Target-PCB",
        help_text="unique and descriptive name",
    )
    description = models.CharField(
        max_length=400,
        blank=True,
        default="",
        help_text="Properties or special behavior that needs documentation",
    )
    comment = models.CharField(
        max_length=200,
        default="",
        blank=True,
        help_text="ideas, TODOs or other temporary info",
    )

    controller1 = models.ForeignKey(
        Controller,
        on_delete=models.PROTECT,
        verbose_name="MCU 1",
        to_field="name",
        related_name="targets_a",
        help_text="MCU on Programming Port 1",
        null=True,
    )
    controller2 = models.ForeignKey(
        Controller,
        on_delete=models.PROTECT,
        verbose_name="MCU 2",
        to_field="name",
        related_name="targets_b",
        help_text="MCU on Programming Port 2",
        null=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
