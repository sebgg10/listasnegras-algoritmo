from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coincidencias', '0003_oficio_personacnbv'),
    ]

    operations = [
        migrations.CreateModel(
            name='Abreviacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('abreviacion', models.CharField(db_index=True, max_length=20, unique=True)),
                ('forma_completa', models.CharField(db_index=True, max_length=100)),
                ('auto_detectada', models.BooleanField(default=False, help_text='Detectada automáticamente al guardar un registro de nombre.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Abreviación',
                'verbose_name_plural': 'Abreviaciones',
                'ordering': ['abreviacion'],
            },
        ),
    ]
