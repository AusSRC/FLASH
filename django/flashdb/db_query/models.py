from django.db import models
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.postgres.fields import ArrayField


QUALITY_CHOICES = [
    ('GOOD', 'GOOD'),
    ('BAD', 'BAD'),
    ('UNCERTAIN', 'UNCERTAIN'),
    ('REJECTED', 'REJECTED'),
    ('NOT_VALIDATED', 'NOT_VALIDATED'),
]


class OIDField(models.Field):
    description = "PostgreSQL OID field"

    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return "oid"
        return "integer"  # fallback for other DBs

    def from_db_value(self, value, expression, connection):
        return value

    def to_python(self, value):
        if value is None:
            return value
        return int(value)


class CharFieldFixed(models.CharField):
    """CharField that creates CHAR(n) in PostgreSQL instead of VARCHAR(n)."""
    def db_type(self, connection):
        return f"char({self.max_length})"


class RealField(models.FloatField):
    description = "Real number (4-byte) stored as PostgreSQL REAL"

    def db_type(self, connection):
        # PostgreSQL 'real' type
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return 'real'
        return super().db_type(connection)


class SBID(models.Model):
    sbid_num = models.IntegerField()
    spect_runid = models.IntegerField(blank=True, null=True)
    detect_runid = models.IntegerField(blank=True, null=True)

    spectralf = models.BooleanField(blank=True, null=True)
    detectionf = models.BooleanField(blank=True, null=True)

    ascii_tar = OIDField(blank=True, null=True,
                                       help_text="PostgreSQL OID")
    detect_tar = OIDField(blank=True, null=True,
                                        help_text="PostgreSQL OID")

    quality = models.CharField(
        max_length=50,
        choices=QUALITY_CHOICES,
        blank=True,
        null=True
    )
    version = models.IntegerField()

    comment = models.TextField(blank=True, null=True)

    spectral_config_tar = OIDField(blank=True, null=True)
    detect_config_tar = OIDField(blank=True, null=True)

    results = models.TextField(blank=True, null=True)
    pointing = models.TextField(blank=True, null=True)
    detect_results = models.BinaryField(blank=True, null=True)

    invert_detectionf = models.BooleanField(blank=True, null=True)
    invert_detect_results = models.BinaryField(blank=True, null=True)
    invert_results = models.TextField(blank=True, null=True)
    invert_detect_runid = models.IntegerField(blank=True, null=True)
    invert_detect_tar = models.BigIntegerField(blank=True, null=True,
                                               help_text="PostgreSQL OID")

    mask_detectionf = models.BooleanField(blank=True, null=True)
    mask = models.TextField(blank=True, null=True)
    mask_detect_results = models.BinaryField(blank=True, null=True)
    mask_results = models.TextField(blank=True, null=True)
    mask_detect_tar = models.BigIntegerField(blank=True, null=True,
                                             help_text="PostgreSQL OID")
    mask_detect_runid = models.IntegerField(blank=True, null=True)
    mask_invert_runid = models.IntegerField(blank=True, null=True)
    mask_invertf = models.BooleanField(blank=True, null=True)
    mask_invert_detect_results = models.BinaryField(blank=True, null=True)
    mask_invert_results = models.TextField(blank=True, null=True)

    publicf = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'sbid'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quality__in=[c[0] for c in QUALITY_CHOICES]),
                name='check_types'
            ),
        ]

    def __str__(self):
        return f"SBID {self.sbid_num} (version {self.version})"

    # ------------------------
    # ORM-friendly properties
    # ------------------------
    @property
    def spect_run(self):
        from .models import SpectRun
        if self.spect_runid is None:
            return None
        return SpectRun.objects.filter(id=self.spect_runid).first()

    @property
    def detect_run(self):
        from .models import DetectRun
        if self.detect_runid is None:
            return None
        return DetectRun.objects.filter(id=self.detect_runid).first()

    @property
    def invert_detect_run(self):
        from .models import DetectRun
        if self.invert_detect_runid is None:
            return None
        return DetectRun.objects.filter(id=self.invert_detect_runid).first()

    @property
    def mask_detect_run(self):
        from .models import DetectRun
        if self.mask_detect_runid is None:
            return None
        return DetectRun.objects.filter(id=self.mask_detect_runid).first()

    @property
    def mask_invert_run(self):
        from .models import DetectRun
        if self.mask_invert_runid is None:
            return None
        return DetectRun.objects.filter(id=self.mask_invert_runid).first()

class SpectRun(models.Model):
    sbids = ArrayField(base_field=models.IntegerField(), blank=True, null=True)
    config_tar = models.BinaryField(blank=True, null=True)
    errlog = models.TextField(blank=True, null=True)
    stdlog = models.TextField(blank=True, null=True)
    platform = models.CharField(max_length=50, blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)
    run_tag = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'spect_run'

    def __str__(self):
        return f"{self.run_tag} - {self.date}"


class DetectRun(models.Model):
    sbids = ArrayField(models.IntegerField(), null=True, blank=True)
    config_tar = models.BinaryField(null=True, blank=True)
    errlog = models.TextField(null=True, blank=True)
    stdlog = models.TextField(null=True, blank=True)
    result_filepath = models.CharField(max_length=100, null=True, blank=True)
    results = models.TextField(null=True, blank=True)
    platform = models.CharField(max_length=50, null=True, blank=True)
    date = models.DateTimeField(null=True, blank=True)
    run_tag = models.CharField(max_length=100, null=True, blank=True)
    invertf = models.BooleanField(null=True, blank=True)
    maskf = models.BooleanField(null=True, blank=True)
    mask_invertf = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'detect_run'  # Specify the database table name

    def __str__(self):
        tag = self.run_tag or f"ID {self.id}"
        date_str = self.date.strftime(
            "%Y-%m-%d %H:%M") if self.date else "No date"
        flags = []
        if self.invertf: flags.append("invert")
        if self.maskf: flags.append("mask")
        if self.mask_invertf: flags.append("mask_invert")
        flags_str = f" [{', '.join(flags)}]" if flags else ""
        return f"{tag} ({date_str}){flags_str}"


class Component(models.Model):
    # Core identifiers
    comp_id = models.CharField(max_length=100)
    shortname = CharFieldFixed(max_length=5, blank=True, null=True)
    component_name = models.CharField(max_length=100, blank=True, null=True)
    ra_hms_cont = models.CharField(max_length=50, blank=True, null=True)
    dec_dms_cont = models.CharField(max_length=50, blank=True, null=True)
    ra_deg_cont = models.CharField(max_length=50, blank=True, null=True)
    dec_deg_cont = models.CharField(max_length=50, blank=True, null=True)
    processstate = models.CharField(max_length=50)
    opd_plotname = models.CharField(max_length=100, blank=True, null=True)
    flux_plotname = models.CharField(max_length=100, blank=True, null=True)
    opd_image = models.BinaryField(blank=True, null=True)
    flux_image = models.BinaryField(blank=True, null=True)
    fluxfilter = RealField(blank=True, null=True)
    flux_cutoff = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^(ABOVE|BELOW)$',
                message="flux_cutoff must be either 'ABOVE' or 'BELOW'"
            )
        ]
    )
    flux_peak = RealField(blank=True, null=True)
    flux_int = RealField(blank=True, null=True)
    mode_num = models.IntegerField(blank=True, null=True)
    invert_mode_num = models.IntegerField(blank=True, null=True)
    mask_mode_num = models.IntegerField(blank=True, null=True)
    invert_mask_mode_num = models.IntegerField(blank=True, null=True)
    ln_mean = RealField(blank=True, null=True)
    invert_ln_mean = RealField(blank=True, null=True)
    mask_ln_mean = RealField(blank=True, null=True)
    invert_mask_ln_mean = RealField(blank=True, null=True)
    spectral_date = models.DateTimeField(blank=True, null=True)
    detection_date = models.DateTimeField(blank=True, null=True)
    invert_detection_date = models.DateTimeField(blank=True, null=True)
    mask_detection_date = models.DateTimeField(blank=True, null=True)
    sbid_id = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    has_siblings = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'component'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(flux_cutoff__in=['ABOVE', 'BELOW']),
                name='check_flux'
            )
        ]

    def __str__(self):
        name = self.component_name or self.shortname or self.comp_id
        date_str = self.spectral_date.strftime("%Y-%m-%d") if self.spectral_date else ""
        return f"{name} ({self.comp_id}){f' - {date_str}' if date_str else ''} [{self.processstate}]"

    @property
    def sbid(self):
        from .models import SBID
        if not hasattr(self, "_sbid_cache"):
            self._sbid_cache = SBID.objects.filter(id=self.sbid_id).first()
        return self._sbid_cache