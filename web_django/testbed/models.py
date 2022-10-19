import re

from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _

# TODO: generate documentation from these models? field-name, description, data-type constraints -> yes, but only adminDoc?
#   -> http://127.0.0.1:8000/admin_testbed/doc/models/testbed.target/
# - use docstring
# - determine how to show model of -> :model:`testbed.Observer`


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


class Controller(models.Model):
    """
    MCUs are logic building-blocks of :model:`testbed.Target` defined by a general MCU-Family, a specific core and a programming-method.
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


class Target(models.Model):
    """
    Target-Boards are connected to the :model:`testbed.Observer` via one of two target-ports. Each Target-PCB can contain up to two MCUs (:model:`testbed.Controller`). This novel approach has multiple benefits:\n
    - one observer could utilize more than 2 MCUs (unused MCUs would receive a sleep-firmware)
    - a Target can use one MCU for processing and another one would be used as a radio or FRAM (MSP430FR)
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


class Observer(models.Model):
    """
    An Observer consists of a Beaglebone Board (running shepherd software) and a shepherd cape. The cape can emulate energy environments and record the power consumption of cyber-physical system (:model:`testbed.Target`). These are connected via two individual Ports.
    """

    name = models.SlugField(
        max_length=30,
        primary_key=True,  # implies unique
        verbose_name="Name of Observer",
        help_text=_(
            "String (up to %(max_length)s), only letters, numbers, underscores & hyphens"
        ),  # TODO: not working could be useful for all
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

    ip = models.GenericIPAddressField(
        protocol="both",
        unique=True,
        verbose_name="IP-Address",
        help_text="Accepts IPv4 and IPv6 Format",
    )  # or limit to "IPv4"
    mac = models.CharField(
        max_length=17,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^(([a-f0-9]{2}([-:]?)){5})[a-f0-9]{2}",
                flags=re.I,
                message="provided MAC-Address is not valid",
            ),
        ],
        unique=True,
        verbose_name="MAC-Address",
        help_text="Accepts hex divided by ':' or '-', like 'AF:FE:E4:D0:9E:6A'",
    )

    room = models.SlugField(
        max_length=10,
        verbose_name="Room-Name",
        help_text="Where to find the Observer",
    )
    eth_port = models.SlugField(
        max_length=20,
        unique=True,
        verbose_name="Ethernet-Port",
        help_text="Name on Wall-Socket",
    )

    latitude = models.FloatField(
        help_text="Y in decimal degrees, 1 udeg ~= 111 mm, cfaed is at 51.02662",
        default=51.026573,  # out of bound, SE
    )
    longitude = models.FloatField(
        help_text="X in decimal degrees, 1 udeg ~= 0.64 * 111 mm (for lat ~ 50), cfaed is at 13.72288",
        default=13.723291,  # out of bound, SE
    )
    # see /cfaed_floorplan_gps.svg for help
    # or https://navigator.tu-dresden.de/etplan/bar/02

    target_a = models.OneToOneField(
        Target,
        on_delete=models.PROTECT,
        verbose_name="Target on Port A",
        related_name="observers_a",
        to_field="name",
        help_text="Target board for Port A on Shepherd Cape",
        null=True,
        blank=True,
    )
    target_b = models.OneToOneField(
        Target,
        on_delete=models.PROTECT,
        verbose_name="Target on Port B",
        related_name="observers_b",
        to_field="name",
        help_text="Target board for Port B on Shepherd Cape",
        null=True,
        blank=True,
    )

    alive_last = models.DateTimeField(
        verbose_name="Last seen",
        help_text="Timestamp of latest alive-message",
        editable=False,
        null=True,
    )
    created = models.DateTimeField(
        verbose_name="Setup-Time",
        help_text="When was the node added",
        default=timezone.now,
        editable=False,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Observer-Node"
