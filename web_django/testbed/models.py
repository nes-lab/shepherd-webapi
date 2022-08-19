from django.db import models

# TODO: generate documentation from these models? field-name, description, data-type constraints
# TODO: migration is not generated in working condition -> target gets created last, but references earlier
# TODO: do we need more than one key? add new fields to other models


class Gpio(models.Model):

    name = models.SlugField(
        max_length=30,
        primary_key=True,
    )  # only letters, numbers, underscores, hyphens
    description = models.TextField(max_length=400, blank=True)
    comment = models.TextField(max_length=200, blank=True)

    direction = models.SlugField(max_length=2)  # TODO: multiple choice
    dir_switch = models.SlugField(max_length=10, blank=True)  # TODO: multiple choice

    pin_pru = models.SlugField(max_length=10)
    pin_bbp = models.SlugField(max_length=10)
    pin_sys = models.SlugField(max_length=10)
    pin_bbs = models.SlugField(max_length=10)


class Target(models.Model):
    name = models.SlugField(
        max_length=30,
        primary_key=True,
    )  # only letters, numbers, underscores, hyphens
    description = models.TextField(
        max_length=400,
        blank=True,
        default="",
    )
    comment = models.TextField(
        max_length=200,
        default="",
        blank=True,
    )

    platform1 = models.SlugField(max_length=10, blank=True)
    core1 = models.SlugField(max_length=10, blank=True)
    programmer1 = models.SlugField(max_length=10, blank=True)
    platform2 = models.SlugField(max_length=10, blank=True)
    core2 = models.SlugField(max_length=10, blank=True)
    programmer2 = models.SlugField(max_length=10, blank=True)
    # TODO: not optimal. maybe use option to link up to two cores?


def validate_mac(value):
    # 18:62:E4:D0:DE:3F, TODO
    #raise ValidationError(
    #    _('%(value)s is not an even number'),
    #    params={'value': value},
    #)
    pass


class Observer(models.Model):
    name = models.SlugField(
        max_length=30,
        primary_key=True,  # implies unique
        verbose_name="Name of Observer",
        help_text="String (up to %(max_length)s), only letters, numbers, underscores & hyphens",
    )
    description = models.TextField(
        max_length=400,
        default="",
        help_text="String (up to %(max_length)s)",
        blank=True,
    )
    comment = models.TextField(
        max_length=200,
        default="",
        blank=True,
    )

    ip = models.GenericIPAddressField(
        protocol="both",
        unique=True,
        verbose_name="IP-Address",

    )  # or limit to "IPv4"
    mac = models.CharField(
        max_length=17,
        blank=True,
        validators=[validate_mac],
        unique=True,
        verbose_name="MAC-Address",
    )

    room = models.SlugField(max_length=10)
    eth_port = models.SlugField(max_length=20, unique=True, )

    longitude = models.FloatField()
    latitude = models.FloatField()

    target_a = models.OneToOneField(
        Target,
        on_delete=models.PROTECT,
        verbose_name="Target Port A",
        related_name="connectedA",
        to_field="name",
        parent_link=True,
        help_text="Target board for Port A on Shepherd Cape",
        blank=True,
    )
    target_b = models.OneToOneField(
        Target,
        on_delete=models.PROTECT,
        verbose_name="Target Port B",
        related_name="connectedB",
        to_field="name",
        parent_link=True,
        help_text="Target board for Port B on Shepherd Cape",  # TODO: add to others
        blank=True,
    )
    # TODO: add ForeignKey.to_field?

    alive_last = models.DateTimeField(
        verbose_name="Last seen",  # TODO: is this correct? could also be label
        help_text="Timestamp of latest alive-message.",
        editable=False,
        blank=True,
    )
