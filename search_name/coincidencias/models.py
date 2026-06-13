from django.db import models

from .matching import build_search_name, clean_name_piece, normalize_name


class Abreviacion(models.Model):
    """Mapeo abreviación → forma completa normalizada (ej. 'hdez' → 'hernandez')."""
    abreviacion = models.CharField(max_length=20, unique=True, db_index=True)
    forma_completa = models.CharField(max_length=100, db_index=True)
    auto_detectada = models.BooleanField(
        default=False,
        help_text="Detectada automáticamente al guardar un registro de nombre.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["abreviacion"]
        verbose_name = "Abreviación"
        verbose_name_plural = "Abreviaciones"

    def save(self, *args, **kwargs):
        self.abreviacion = normalize_name(self.abreviacion)
        self.forma_completa = normalize_name(self.forma_completa)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.abreviacion} → {self.forma_completa}"


class Oficio(models.Model):
    folio = models.IntegerField(unique=True, db_index=True)
    numero_oficio = models.CharField(max_length=80, blank=True, default="")
    numero_expediente = models.CharField(max_length=80, blank=True, default="")
    solicitud_siara = models.CharField(max_length=60, blank=True, default="")
    anio = models.IntegerField(default=0)
    area_clave = models.CharField(max_length=10, blank=True, default="")
    area_descripcion = models.CharField(max_length=120, blank=True, default="")
    fecha_publicacion = models.DateField()
    dias_plazo = models.IntegerField(default=1)
    autoridad_nombre = models.CharField(max_length=220, blank=True, default="")
    referencia = models.CharField(max_length=220, blank=True, default="")
    referencia1 = models.CharField(max_length=220, blank=True, default="")
    tiene_aseguramiento = models.BooleanField(default=False)
    archivo_xml = models.CharField(max_length=220, blank=True, default="")
    importado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_publicacion", "-folio"]
        verbose_name = "Oficio CNBV"
        verbose_name_plural = "Oficios CNBV"

    def __str__(self):
        return f"Folio {self.folio} — {self.numero_oficio.strip()}"


class PersonaCNBV(models.Model):
    oficio = models.ForeignKey(Oficio, on_delete=models.CASCADE, related_name="personas")
    persona_id = models.IntegerField(default=0)
    caracter = models.CharField(max_length=60, blank=True, default="")
    tipo_persona = models.CharField(max_length=20, blank=True, default="")
    nombre = models.CharField(max_length=220, blank=True, default="")
    paterno = models.CharField(max_length=80, blank=True, default="")
    materno = models.CharField(max_length=80, blank=True, default="")
    rfc = models.CharField(max_length=20, blank=True, default="")
    relacion = models.CharField(max_length=120, blank=True, default="")
    domicilio = models.CharField(max_length=320, blank=True, default="")
    complementarios = models.CharField(max_length=220, blank=True, default="")
    search_full_name = models.CharField(max_length=300, db_index=True, editable=False, default="")
    normalized_name = models.CharField(max_length=300, db_index=True, editable=False, default="")

    class Meta:
        ordering = ["oficio", "persona_id"]
        verbose_name = "Persona CNBV"
        verbose_name_plural = "Personas CNBV"

    def prepare_search_fields(self):
        self.nombre = clean_name_piece(self.nombre)
        self.paterno = clean_name_piece(self.paterno)
        self.materno = clean_name_piece(self.materno)
        self.rfc = clean_name_piece(self.rfc).upper()
        self.search_full_name = build_search_name(
            nombre=self.nombre,
            paterno=self.paterno,
            materno=self.materno,
        )
        self.normalized_name = normalize_name(self.search_full_name)

    def save(self, *args, **kwargs):
        self.prepare_search_fields()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.search_full_name} ({self.tipo_persona})"


class NameRecord(models.Model):
    nombre = models.CharField(max_length=120, blank=True, default="")
    paterno = models.CharField(max_length=80, blank=True, default="")
    materno = models.CharField(max_length=80, blank=True, default="")
    rfc = models.CharField(max_length=20, blank=True, default="")
    origen = models.CharField(max_length=40, blank=True, default="manual")
    folio_ref = models.CharField(max_length=50, blank=True, default="")
    search_full_name = models.CharField(
        max_length=180, db_index=True, editable=False, default=""
    )
    normalized_name = models.CharField(max_length=180, db_index=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["search_full_name", "id"]
        verbose_name = "Registro de nombre"
        verbose_name_plural = "Registros de nombres"

    @property
    def full_name(self):
        return self.search_full_name

    def prepare_search_fields(self):
        self.nombre = clean_name_piece(self.nombre)
        self.paterno = clean_name_piece(self.paterno)
        self.materno = clean_name_piece(self.materno)
        self.rfc = clean_name_piece(self.rfc).upper()
        self.origen = clean_name_piece(self.origen) or "manual"
        self.folio_ref = clean_name_piece(self.folio_ref)
        self.search_full_name = build_search_name(
            nombre=self.nombre,
            paterno=self.paterno,
            materno=self.materno,
        )
        self.normalized_name = normalize_name(self.search_full_name)

    def save(self, *args, **kwargs):
        self.prepare_search_fields()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.search_full_name
