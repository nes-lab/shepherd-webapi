from django.db import models


class Controller(models.Model):
    """
    MCUs are logic building-blocks of :model:`testbed.Target` defined
    by a general MCU-Family, a specific core and a programming-method.
    """

    name = models.SlugField(
        max_length=30,
        primary_key=True,
        verbose_name="MCU-Name",
        # help_text="",
    )
    comment = models.CharField(
        max_length=200,
        default="",
        blank=True,
        help_text="ideas, TODOs or other temporary info",
    )
    platform = models.SlugField(
        max_length=20,
        verbose_name="MCU-Platform",
        help_text="MCU-Family or generalized Name",
    )
    core = models.SlugField(
        max_length=20,
        unique=True,
        verbose_name="Part-Number",
        help_text="PN of Manufacturer",
    )
    programmer_choices = [
        ("swd", "Serial-Wire-Debug"),
        ("sbw", "Spy-By-Wire"),
        ("jtag", "JTAG"),
        ("uart", "UART"),
    ]
    programmer = models.SlugField(
        max_length=10,
        choices=programmer_choices,
        help_text="Choose how the MCU gets programmed",
    )

    def __str__(self):
        return self.core

    class Meta:
        ordering = ["name"]
