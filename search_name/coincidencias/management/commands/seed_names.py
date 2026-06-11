from django.core.management.base import BaseCommand

from coincidencias.models import NameRecord

SAMPLE_RECORDS = [
    {"nombre": "Juan", "paterno": "Perez", "materno": "Lopez", "origen": "SolicitudPartes", "folio_ref": "FICT-001", "rfc": "JUPL800101AAA"},
    {"nombre": "Johan", "paterno": "Peres", "materno": "Lopes", "origen": "SolicitudPartes", "folio_ref": "FICT-002", "rfc": "JOPL800101AAA"},
    {"nombre": "Maria Fernanda", "paterno": "Lopez", "materno": "Garcia", "origen": "PersonasSolicitud", "folio_ref": "FICT-003"},
    {"nombre": "Mario Fernando", "paterno": "Lopes", "materno": "Garzia", "origen": "PersonasSolicitud", "folio_ref": "FICT-004"},
    {"nombre": "Carlos Alberto", "paterno": "Ruiz", "materno": "Mora", "origen": "SolicitudPartes", "folio_ref": "FICT-005"},
    {"nombre": "Karlos Alberto", "paterno": "Ruis", "materno": "Mora", "origen": "SolicitudPartes", "folio_ref": "FICT-006"},
    {"nombre": "Cristian", "paterno": "Hernandez", "materno": "Soto", "origen": "PersonasSolicitud", "folio_ref": "FICT-007", "rfc": "CRHS820212BBB"},
    {"nombre": "Christian", "paterno": "Hernandes", "materno": "Soto", "origen": "PersonasSolicitud", "folio_ref": "FICT-008"},
    {"nombre": "Sofia", "paterno": "Martinez", "materno": "Reyes", "origen": "SolicitudPartes", "folio_ref": "FICT-009"},
    {"nombre": "Sofya", "paterno": "Martines", "materno": "Reyes", "origen": "SolicitudPartes", "folio_ref": "FICT-010"},
    {"nombre": "Alejandro", "paterno": "Gomez", "materno": "Vega", "origen": "PersonasSolicitud", "folio_ref": "FICT-011"},
    {"nombre": "Alejandro", "paterno": "Gomes", "materno": "Vega", "origen": "PersonasSolicitud", "folio_ref": "FICT-012"},
    {"nombre": "Patricia", "paterno": "Sanchez", "materno": "Luna", "origen": "SolicitudPartes", "folio_ref": "FICT-013"},
    {"nombre": "Patrisia", "paterno": "Sanches", "materno": "Luna", "origen": "SolicitudPartes", "folio_ref": "FICT-014"},
    {"nombre": "Jose Antonio", "paterno": "Ramirez", "materno": "Silva", "origen": "PersonasSolicitud", "folio_ref": "FICT-015"},
    {"nombre": "Jhose Antonio", "paterno": "Ramires", "materno": "Silva", "origen": "PersonasSolicitud", "folio_ref": "FICT-016"},
    {"nombre": "Ana Lucia", "paterno": "Torres", "materno": "Diaz", "origen": "SolicitudPartes", "folio_ref": "FICT-017"},
    {"nombre": "Ana Luisa", "paterno": "T orres", "materno": "Diaz", "origen": "SolicitudPartes", "folio_ref": "FICT-018"},
    {"nombre": "Luis Eduardo", "paterno": "Mendez", "materno": "Cruz", "origen": "PersonasSolicitud", "folio_ref": "FICT-019"},
    {"nombre": "Luis Eduard", "paterno": "Mendez", "materno": "Cruz", "origen": "PersonasSolicitud", "folio_ref": "FICT-020"},
    {"nombre": "Gabriela", "paterno": "Nunez", "materno": "Ortega", "origen": "SolicitudPartes", "folio_ref": "FICT-021"},
    {"nombre": "Grabiela", "paterno": "Nuñez", "materno": "Ortega", "origen": "SolicitudPartes", "folio_ref": "FICT-022"},
    {"nombre": "Juan Perez Lopez", "paterno": "Perez", "materno": "Lopez", "origen": "PersonasSolicitud", "folio_ref": "FICT-023"},
    {"nombre": "Maria Fernanda Lopez Garcia", "paterno": "", "materno": "", "origen": "PersonasSolicitud", "folio_ref": "FICT-024"},
]


class Command(BaseCommand):
    help = "Carga nombres de ejemplo para pruebas de coincidencia."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los registros actuales antes de cargar los datos.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = NameRecord.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Registros eliminados: {deleted}"))

        created = 0
        for payload in SAMPLE_RECORDS:
            _, was_created = NameRecord.objects.get_or_create(
                nombre=payload["nombre"],
                paterno=payload["paterno"],
                materno=payload["materno"],
                origen=payload["origen"],
                folio_ref=payload["folio_ref"],
                defaults={"rfc": payload.get("rfc", "")},
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Nombres insertados: {created}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Total de registros ahora: {NameRecord.objects.count()}"
            )
        )
