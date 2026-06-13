from django.apps import AppConfig


class CoincidenciasConfig(AppConfig):
    name = "coincidencias"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import coincidencias.signals  # noqa: F401
