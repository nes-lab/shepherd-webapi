import re
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from model_Target import Target
from django.utils.translation import gettext as _


class Observer(models.Model):
    """
    An Observer consists of a Beaglebone Board (running shepherd software) and a shepherd cape.
    The cape can emulate energy environments and record the power consumption of cyber-physical
    system (:model:`testbed.Target`). These are connected via two individual Ports.
    """

    name = models.SlugField(
        max_length=30,
        primary_key=True,  # implies unique
        verbose_name="Name of Observer",
        help_text=_(
            "String (up to %(max_length)s), only letters, numbers, underscores & hyphens",
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
        help_text="X in dec deg, 1 udeg ~= 0.64 * 111 mm (for lat ~ 50), cfaed is at 13.72288",
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
