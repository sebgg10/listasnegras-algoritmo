from django.db import migrations, models


def normalize_name(value: str) -> str:
    value = (value or "").strip().lower()
    cleaned = []
    previous_space = False
    for char in value:
        if char.isalnum():
            cleaned.append(char)
            previous_space = False
            continue
        if char.isspace() and not previous_space:
            cleaned.append(" ")
            previous_space = True
    return "".join(cleaned).strip()


def forwards(apps, schema_editor):
    NameRecord = apps.get_model("coincidencias", "NameRecord")
    for record in NameRecord.objects.all():
        full_name = (getattr(record, "full_name", "") or "").strip()
        record.nombre = full_name
        record.paterno = ""
        record.materno = ""
        record.rfc = ""
        record.origen = "legacy"
        record.folio_ref = ""
        record.search_full_name = full_name
        record.normalized_name = normalize_name(full_name)
        record.save(
            update_fields=[
                "nombre",
                "paterno",
                "materno",
                "rfc",
                "origen",
                "folio_ref",
                "search_full_name",
                "normalized_name",
            ]
        )


def backwards(apps, schema_editor):
    NameRecord = apps.get_model("coincidencias", "NameRecord")
    for record in NameRecord.objects.all():
        full_name = (getattr(record, "search_full_name", "") or "").strip()
        record.full_name = full_name
        record.normalized_name = normalize_name(full_name)
        record.save(update_fields=["full_name", "normalized_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("coincidencias", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="namerecord",
            name="folio_ref",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="namerecord",
            name="materno",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="namerecord",
            name="nombre",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="namerecord",
            name="origen",
            field=models.CharField(blank=True, default="manual", max_length=40),
        ),
        migrations.AddField(
            model_name="namerecord",
            name="paterno",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="namerecord",
            name="rfc",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="namerecord",
            name="search_full_name",
            field=models.CharField(db_index=True, default="", editable=False, max_length=180),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name="namerecord",
            name="full_name",
        ),
        migrations.AlterModelOptions(
            name="namerecord",
            options={
                "ordering": ["search_full_name", "id"],
                "verbose_name": "Registro de nombre",
                "verbose_name_plural": "Registros de nombres",
            },
        ),
    ]
