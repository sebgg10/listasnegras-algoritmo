from django.contrib import admin

from .models import NameRecord, Oficio, PersonaCNBV


@admin.register(NameRecord)
class NameRecordAdmin(admin.ModelAdmin):
    list_display = ("full_name", "normalized_name", "created_at")
    search_fields = ("full_name", "normalized_name")
    list_filter = ("created_at",)


@admin.register(Oficio)
class OficioAdmin(admin.ModelAdmin):
    list_display = ("folio", "numero_oficio", "fecha_publicacion", "referencia", "dias_plazo", "importado_en")
    search_fields = ("folio", "numero_oficio", "numero_expediente", "referencia")
    list_filter = ("fecha_publicacion", "area_descripcion", "tiene_aseguramiento")
    ordering = ("-fecha_publicacion", "-folio")


@admin.register(PersonaCNBV)
class PersonaCNBVAdmin(admin.ModelAdmin):
    list_display = ("search_full_name", "tipo_persona", "rfc", "caracter", "oficio")
    search_fields = ("search_full_name", "normalized_name", "rfc")
    list_filter = ("tipo_persona", "caracter", "oficio__fecha_publicacion")
    raw_id_fields = ("oficio",)
