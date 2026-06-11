from datetime import date, datetime

import pymysql
import pymysql.cursors
from django.core.management.base import BaseCommand, CommandError

from coincidencias.models import Oficio, PersonaCNBV

# Credenciales por defecto (mismas que conecta.php)
DEFAULT_HOST = "localhost"
DEFAULT_USER = "root"
DEFAULT_PASS = ""
DEFAULT_DB   = "listasnegras"
DEFAULT_PORT = 3306


class Command(BaseCommand):
    help = "Importa oficios y personas desde el MySQL de listasnegras (XAMPP)."

    def add_arguments(self, parser):
        parser.add_argument("--host",     default=DEFAULT_HOST)
        parser.add_argument("--user",     default=DEFAULT_USER)
        parser.add_argument("--password", default=DEFAULT_PASS)
        parser.add_argument("--db",       default=DEFAULT_DB)
        parser.add_argument("--port",     type=int, default=DEFAULT_PORT)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina todos los oficios de Django antes de importar.",
        )
        parser.add_argument(
            "--describe",
            action="store_true",
            help="Solo muestra las tablas y columnas disponibles en MySQL, sin importar.",
        )

    def handle(self, *args, **options):
        try:
            conn = pymysql.connect(
                host=options["host"],
                user=options["user"],
                password=options["password"],
                database=options["db"],
                port=options["port"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
        except pymysql.Error as e:
            raise CommandError(
                f"No se pudo conectar a MySQL ({options['host']}:{options['port']}): {e}"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Conectado a MySQL: {options['db']}@{options['host']}"
        ))

        with conn:
            with conn.cursor() as cur:
                if options["describe"]:
                    self._describe(cur)
                    return

                if options["reset"]:
                    deleted, _ = Oficio.objects.all().delete()
                    self.stdout.write(self.style.WARNING(f"Oficios eliminados: {deleted}"))

                self._importar(cur)

    # ── Describe ────────────────────────────────────────────────

    def _describe(self, cur):
        cur.execute("SHOW TABLES")
        tablas = [list(row.values())[0] for row in cur.fetchall()]
        self.stdout.write("\nTablas disponibles:")
        for tabla in tablas:
            cur.execute(f"DESCRIBE `{tabla}`")
            cols = [r["Field"] for r in cur.fetchall()]
            self.stdout.write(f"  {tabla}: {', '.join(cols)}")

    # ── Importar ─────────────────────────────────────────────────

    def _importar(self, cur):
        importados = omitidos = errores = 0

        cur.execute("SELECT * FROM expedientes ORDER BY Cnbv_Folio")
        expedientes = cur.fetchall()

        if not expedientes:
            self.stdout.write(self.style.WARNING("No hay expedientes en MySQL."))
            return

        for row in expedientes:
            try:
                folio = int(row.get("Cnbv_Folio") or 0)
                if not folio:
                    continue

                if Oficio.objects.filter(folio=folio).exists():
                    omitidos += 1
                    continue

                fecha = self._parse_fecha(row.get("Cnbv_FechaPublicacion"))
                dias_plazo = self._to_int(row.get("Cnbv_DiasPlazo"), default=1)
                anio = self._to_int(row.get("Cnbv_OficioYear"), default=0)
                tiene_aseg = str(row.get("TieneAseguramiento") or "").lower() in ("1", "true", "si", "sí")

                oficio = Oficio.objects.create(
                    folio=folio,
                    numero_oficio=self._s(row.get("Cnbv_NumeroOficio")),
                    numero_expediente=self._s(row.get("Cnbv_NumeroExpediente")),
                    solicitud_siara=self._s(row.get("Cnbv_SolicitudSiara")),
                    anio=anio,
                    area_clave=self._s(row.get("Cnbv_AreaClave")),
                    area_descripcion=self._s(row.get("Cnbv_AreaDescripcion")),
                    fecha_publicacion=fecha,
                    dias_plazo=dias_plazo,
                    autoridad_nombre=self._s(row.get("AutoridadNombre")),
                    referencia=self._s(row.get("Referencia")),
                    referencia1=self._s(row.get("Referencia1")),
                    tiene_aseguramiento=tiene_aseg,
                    archivo_xml=self._s(row.get("expediente")),
                )

                personas_creadas = self._importar_personas(cur, oficio)
                importados += 1
                self.stdout.write(
                    f"  Folio {folio} ({row.get('Cnbv_FechaPublicacion')}): "
                    f"{personas_creadas} persona(s)"
                )

            except Exception as exc:
                errores += 1
                self.stdout.write(self.style.ERROR(
                    f"Error en folio {row.get('Cnbv_Folio')}: {exc}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"\nResumen — Importados: {importados} | "
            f"Omitidos (ya existían): {omitidos} | Errores: {errores}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Total de oficios en Django: {Oficio.objects.count()}"
        ))

    def _importar_personas(self, cur, oficio):
        cur.execute(
            "SELECT * FROM personassolicitud WHERE Cnbv_Folio = %s",
            (oficio.folio,),
        )
        personas = cur.fetchall()
        creadas = 0
        for p in personas:
            try:
                PersonaCNBV.objects.create(
                    oficio=oficio,
                    persona_id=self._to_int(p.get("PersonaId"), default=0),
                    caracter=self._s(p.get("Caracter")),
                    tipo_persona=self._s(p.get("Persona")),
                    nombre=self._s(p.get("Nombre")),
                    paterno=self._s(p.get("Paterno")),
                    materno=self._s(p.get("Materno")),
                    rfc=self._s(p.get("Rfc")),
                    relacion=self._s(p.get("Relacion")),
                    domicilio=self._s(p.get("Domicilio")),
                    complementarios=self._s(p.get("Complementarios")),
                )
                creadas += 1
            except Exception:
                pass
        return creadas

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _s(value, max_len=None):
        """Convierte a str limpio."""
        if value is None:
            return ""
        result = str(value).strip()
        if max_len:
            result = result[:max_len]
        return result

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(value or default)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_fecha(value):
        if not value:
            return date.today()
        if isinstance(value, (date, datetime)):
            return value if isinstance(value, date) else value.date()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
            try:
                return datetime.strptime(str(value).strip(), fmt).date()
            except ValueError:
                continue
        return date.today()
