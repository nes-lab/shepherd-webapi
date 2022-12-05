from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models

# Create your models here.

# Field types: https://docs.djangoproject.com/en/4.1/ref/models/fields/#model-field-types
# DurationField()


class Harvester(models.Model):

    name = models.SlugField(
        max_length=10,
        primary_key=True,
        verbose_name="Harvester-Name",
    )
    # TODO: add user-name to create unique ID? users and
    comment = models.CharField(
        max_length=200,
        default="",
        blank=True,
        help_text="Ideas, TODOs or other temporary info",
    )

    base_choices = [
        ("cv20", "V_const = 2.0 V"),
        ("cv", "V_const = 2.4 V"),
        ("cv33", "V_const = 3.3 V"),
        ("mppt_voc", "MPPT VOC Generic - Solar"),
        ("mppt_bq", "MPPT VOC BQ - Solar"),
        ("mppt_bqt", "MPPT VOC BQ - Thermoelectric"),
        ("mppt_po", "MPPT Perturb & Observe"),
        ("mppt_opt", "MPPT PO - Power Optimum"),
    ]  # TODO: source from yaml-file

    base = models.SlugField(
        max_length=10,
        choices=base_choices,
        default="mppt_opt",
        verbose_name="Base Model",
        help_text="Source for Fallback values -> allows omitting redundant parameters",
    )

    # window_size      -> not relevant for emu-harvester
    # dtype            -> always ivsample for emu

    voltage_valid = [MinValueValidator(0), MaxValueValidator(5_000)]

    voltage_mV = models.IntegerField(
        verbose_name="Voltage [mV]",
        help_text="",
        blank=True,
        validators=voltage_valid,
    )
    voltage_min_mV = models.IntegerField(
        verbose_name="Voltage Min [mV]",
        help_text="",
        blank=True,
        validators=voltage_valid + [MaxValueValidator(voltage_mV)],
    )
    voltage_max_mV = models.IntegerField(
        verbose_name="Voltage Max [mV]",
        help_text="",
        blank=True,
        validators=voltage_valid + [MinValueValidator(voltage_mV)],
    )

    current_limit_uA = models.IntegerField(
        verbose_name="Current-Limit [uA]",
        help_text="Max current output of VOC-MPPT",
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(50_000)],
    )
    voltage_step_mV = models.IntegerField(
        verbose_name="Voltage Step [mV]",
        help_text="Step-size for perturb & observe",
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1_000_000)],
    )

    setpoint_n = models.FloatField(
        verbose_name="MPPT Setpoint [n]",
        help_text="Value between 0..1, typical .76 for solar, .5 for thermoelectric",
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )

    interval_ms = models.FloatField(
        verbose_name="Measurement-Interval [ms]",
        help_text="Interval between start of measurements",
        blank=True,
        validators=[MinValueValidator(0.01), MaxValueValidator(1_000_000)],
    )
    duration_ms = models.FloatField(
        verbose_name="Measurement-Duration [ms]",
        help_text="Duration of measurement",
        blank=True,
        validators=[
            MinValueValidator(0.01),
            MaxValueValidator(1_000_000),
            MaxValueValidator(interval_ms),
        ],
    )

    # rising            -> not relevant for emu
    # wait_cycles       -> not relevant for emu


# int_list_validator
