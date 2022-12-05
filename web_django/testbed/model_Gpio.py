from django.db import models


class Gpio(models.Model):
    """
    Entries describe relation for target GPIO: \n
    - main GPIOs are monitored by the PRU and can be observed
    - most GPIOs are connected to a second pin and can be controlled from linux userspace
    - for each pin the position on the Pin-Header and the affiliated register-name are provided

    """

    name = models.SlugField(
        max_length=30,
        primary_key=True,
        verbose_name="GPIO-Name",
        # help_text="",
    )
    description = models.CharField(
        max_length=400,
        default="",
        blank=True,
        help_text="Properties or special behavior that needs documentation",
    )
    comment = models.CharField(
        max_length=200,
        default="",
        blank=True,
        help_text="ideas, TODOs or other temporary info",
    )

    direction_choices = [
        ("I", "Input"),
        ("O", "Output"),
        ("IO", "Bidirectional"),
    ]

    direction = models.SlugField(
        max_length=2,
        choices=direction_choices,
        default="I",
        verbose_name="Direction-Capability",
        help_text="Specify I=Input, O=Output, IO, with reference to observer",
    )
    dir_switch = models.SlugField(
        max_length=10,
        blank=True,
        verbose_name="Direction-Pin",
        help_text="Toggle changes direction, High is sys-out / target-in",
    )

    reg_pru = models.SlugField(
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        verbose_name="PRU Register-Name of Pin",
        help_text="something like r31_05 for input, r30_xx for output",
    )
    pin_pru = models.SlugField(
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        verbose_name="PRU Pin-Name on Header",
        help_text="something like P8_29",
    )

    reg_sys = models.SlugField(
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        verbose_name="System Register-Name of Pin",
        help_text="something like GPIO1[23] translates to 1*32+23 = 55",
    )
    pin_sys = models.SlugField(
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        verbose_name="System Pin-Name on Header",
        help_text="something like P8_29",
    )

