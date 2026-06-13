from django.db import migrations

# Abreviaciones iniciales de apellidos mexicanos comunes.
# Claves y valores ya en forma normalizada (minúsculas, sin acentos).
INITIAL_ABBREVS = [
    ("hdez",   "hernandez"),
    ("hernz",  "hernandez"),
    ("hrnz",   "hernandez"),
    ("glez",   "gonzalez"),
    ("gonz",   "gonzalez"),
    ("mtnz",   "martinez"),
    ("mrtz",   "martinez"),
    ("mtz",    "martinez"),
    ("rdgz",   "rodriguez"),
    ("rdguez", "rodriguez"),
    ("rodz",   "rodriguez"),
    ("lpz",    "lopez"),
    ("snchz",  "sanchez"),
    ("snchez", "sanchez"),
    ("rmrz",   "ramirez"),
    ("rmz",    "ramirez"),
    ("gtrz",   "gutierrez"),
    ("gtrrz",  "gutierrez"),
    ("chvz",   "chavez"),
    ("mrls",   "morales"),
    ("jmnz",   "jimenez"),
    ("jimnz",  "jimenez"),
    ("vrgs",   "vargas"),
    ("mndz",   "mendoza"),
    ("alvrz",  "alvarez"),
    ("prz",    "perez"),
    ("grca",   "garcia"),
    ("ortz",   "ortiz"),
    ("flrs",   "flores"),
    ("rms",    "ramos"),
    ("dlgd",   "delgado"),
    ("hrra",   "herrera"),
    ("mdn",    "medina"),
    ("aglr",   "aguilar"),
    ("trs",    "torres"),
    ("cstr",   "castro"),
]


def seed_forward(apps, schema_editor):
    Abreviacion = apps.get_model("coincidencias", "Abreviacion")
    Abreviacion.objects.bulk_create(
        [
            Abreviacion(abreviacion=abbr, forma_completa=full, auto_detectada=False)
            for abbr, full in INITIAL_ABBREVS
        ],
        ignore_conflicts=True,
    )


def seed_backward(apps, schema_editor):
    Abreviacion = apps.get_model("coincidencias", "Abreviacion")
    Abreviacion.objects.filter(
        abreviacion__in=[abbr for abbr, _ in INITIAL_ABBREVS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('coincidencias', '0004_abreviacion'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_backward),
    ]
