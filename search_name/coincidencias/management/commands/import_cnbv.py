import glob
import os
import xml.etree.ElementTree as ET
from datetime import date

from django.core.management.base import BaseCommand

from coincidencias.models import NameRecord, Oficio, PersonaCNBV

NS = "http://www.cnbv.gob.mx"


def _tag(name):
    return f"{{{NS}}}{name}"


def _text(element, tag_name, default=""):
    el = element.find(_tag(tag_name))
    if el is None:
        return default
    return (el.text or "").strip()


class Command(BaseCommand):
    help = "Importa oficios CNBV desde una carpeta de archivos XML."

    def add_arguments(self, parser):
        parser.add_argument(
            "carpeta",
            type=str,
            help="Ruta a la carpeta raíz que contiene los XMLs (ej. listasnegras/)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina todos los oficios existentes antes de importar.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            count, _ = Oficio.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Oficios eliminados: {count}"))
            nr_count, _ = NameRecord.objects.filter(origen="SolicitudPartes").delete()
            self.stdout.write(self.style.WARNING(f"NameRecords eliminados: {nr_count}"))

        carpeta = options["carpeta"]
        pattern = os.path.join(carpeta, "**", "4-*.xml")
        archivos = sorted(glob.glob(pattern, recursive=True))

        if not archivos:
            self.stdout.write(self.style.WARNING(f"No se encontraron archivos 4-*.xml en: {carpeta}"))
            return

        importados = 0
        omitidos = 0
        errores = 0

        for archivo in archivos:
            try:
                tree = ET.parse(archivo)
                root = tree.getroot()

                folio_str = _text(root, "Cnbv_Folio")
                if not folio_str:
                    continue
                folio = int(folio_str)

                if Oficio.objects.filter(folio=folio).exists():
                    omitidos += 1
                    continue

                fecha_str = _text(root, "Cnbv_FechaPublicacion")
                try:
                    fecha = date.fromisoformat(fecha_str)
                except (ValueError, TypeError):
                    fecha = date.today()

                try:
                    dias_plazo = int(_text(root, "Cnbv_DiasPlazo", "1") or 1)
                except ValueError:
                    dias_plazo = 1

                try:
                    anio = int(_text(root, "Cnbv_OficioYear", "0") or 0)
                except ValueError:
                    anio = 0

                tiene_aseg = _text(root, "TieneAseguramiento").lower() == "true"

                oficio = Oficio.objects.create(
                    folio=folio,
                    numero_oficio=_text(root, "Cnbv_NumeroOficio"),
                    numero_expediente=_text(root, "Cnbv_NumeroExpediente"),
                    solicitud_siara=_text(root, "Cnbv_SolicitudSiara"),
                    anio=anio,
                    area_clave=_text(root, "Cnbv_AreaClave"),
                    area_descripcion=_text(root, "Cnbv_AreaDescripcion"),
                    fecha_publicacion=fecha,
                    dias_plazo=dias_plazo,
                    autoridad_nombre=_text(root, "AutoridadNombre"),
                    referencia=_text(root, "Referencia"),
                    referencia1=_text(root, "Referencia1"),
                    tiene_aseguramiento=tiene_aseg,
                    archivo_xml=os.path.basename(archivo),
                )

                personas_creadas = 0
                for sol_esp in root.findall(_tag("SolicitudEspecifica")):
                    for persona_el in sol_esp.findall(_tag("PersonasSolicitud")):
                        try:
                            persona_id = int(_text(persona_el, "PersonaId", "0") or 0)
                        except ValueError:
                            persona_id = 0

                        PersonaCNBV.objects.create(
                            oficio=oficio,
                            persona_id=persona_id,
                            caracter=_text(persona_el, "Caracter"),
                            tipo_persona=_text(persona_el, "Persona"),
                            nombre=_text(persona_el, "Nombre"),
                            paterno=_text(persona_el, "Paterno"),
                            materno=_text(persona_el, "Materno"),
                            rfc=_text(persona_el, "Rfc"),
                            relacion=_text(persona_el, "Relacion"),
                            domicilio=_text(persona_el, "Domicilio"),
                            complementarios=_text(persona_el, "Complementarios"),
                        )
                        personas_creadas += 1

                partes_creadas = self._importar_partes(root, folio)
                importados += 1
                self.stdout.write(
                    f"  Folio {folio} ({fecha_str}): "
                    f"{personas_creadas} PersonaCNBV, {partes_creadas} NameRecord"
                )

            except Exception as exc:
                errores += 1
                self.stdout.write(self.style.ERROR(f"Error en {archivo}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nResumen — Importados: {importados} | Omitidos (ya existían): {omitidos} | Errores: {errores}"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Total de oficios en BD: {Oficio.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Total de NameRecords en BD: {NameRecord.objects.count()}"))

    def _importar_partes(self, root, folio):
        creadas = 0
        folio_str = str(folio)
        for parte_el in root.findall(_tag("SolicitudPartes")):
            nombre  = _text(parte_el, "Nombre")
            paterno = _text(parte_el, "Paterno")
            materno = _text(parte_el, "Materno")
            rfc     = _text(parte_el, "Rfc")
            if not nombre and not paterno:
                continue
            _, created = NameRecord.objects.get_or_create(
                origen="SolicitudPartes",
                folio_ref=folio_str,
                nombre=nombre,
                paterno=paterno,
                materno=materno,
                defaults={"rfc": rfc},
            )
            if created:
                creadas += 1
        return creadas
