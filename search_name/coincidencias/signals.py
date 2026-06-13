from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .matching import (
    consonant_skeleton,
    find_full_form,
    invalidate_abbreviations_cache,
    is_abbreviation_candidate,
    normalize_name,
    tokens,
)


@receiver(post_save, sender="coincidencias.Abreviacion")
@receiver(post_delete, sender="coincidencias.Abreviacion")
def _on_abreviacion_change(sender, **kwargs):
    invalidate_abbreviations_cache()


@receiver(post_save, sender="coincidencias.NameRecord")
def _detect_abbreviations_from_name_record(sender, instance, **kwargs):
    _detect_and_register(instance.nombre, instance.paterno, instance.materno)


@receiver(post_save, sender="coincidencias.PersonaCNBV")
def _detect_abbreviations_from_persona_cnbv(sender, instance, **kwargs):
    _detect_and_register(instance.nombre, instance.paterno, instance.materno)


def _detect_and_register(nombre: str, paterno: str, materno: str) -> None:
    """Detecta y registra abreviaciones nuevas desde los campos de nombre.

    Dos estrategias complementarias:
    1. Token corto/consonántico (ej. 'RDRGZ') → busca forma completa compatible.
    2. Token largo (ej. 'RODRIGUEZ') → quita vocales → registra el esqueleto
       consonántico como abreviación (ej. 'rdrgz → rodriguez').
    """
    from .models import Abreviacion

    all_tokens = set(tokens(nombre)) | set(tokens(paterno)) | set(tokens(materno))
    if not all_tokens:
        return

    new_entries: list[Abreviacion] = []

    # --- Estrategia 1: token corto → buscar forma completa en BD ---
    abbrev_candidates = [t for t in all_tokens if is_abbreviation_candidate(t)]
    if abbrev_candidates:
        known_full_forms = list(
            Abreviacion.objects.values_list("forma_completa", flat=True).distinct()
        )
        existing = set(
            Abreviacion.objects.filter(abreviacion__in=abbrev_candidates)
            .values_list("abreviacion", flat=True)
        )
        for tok in abbrev_candidates:
            if tok in existing:
                continue
            full = find_full_form(tok, known_full_forms)
            if full and full != tok:
                new_entries.append(
                    Abreviacion(abreviacion=tok, forma_completa=full, auto_detectada=True)
                )

    # --- Estrategia 2: token largo → derivar esqueleto consonántico ---
    full_form_tokens = [
        t for t in all_tokens
        if not is_abbreviation_candidate(t) and len(t) >= 5
    ]
    if full_form_tokens:
        existing_abbrevs = set(
            Abreviacion.objects.values_list("abreviacion", flat=True)
        )
        for tok in full_form_tokens:
            skel = consonant_skeleton(tok)
            if len(skel) < 3 or skel == tok or skel in existing_abbrevs:
                continue
            new_entries.append(
                Abreviacion(abreviacion=skel, forma_completa=tok, auto_detectada=True)
            )
            existing_abbrevs.add(skel)  # evitar duplicados dentro del mismo lote

    if new_entries:
        Abreviacion.objects.bulk_create(new_entries, ignore_conflicts=True)
        invalidate_abbreviations_cache()
