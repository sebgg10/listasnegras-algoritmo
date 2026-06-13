from django.shortcuts import get_object_or_404, render

from .forms import NameSearchForm
from .matching import find_name_matches
from .models import NameRecord, Oficio, PersonaCNBV


def _parse_date(value: str):
    from datetime import date
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


def _parse_score(value, default: int = 45) -> int:
    try:
        return max(0, min(100, int(value)))
    except (ValueError, TypeError):
        return default


def search_names(request):
    form = NameSearchForm(request.GET or None)
    cleaned = form.cleaned_or_default()

    query = cleaned["query"]
    min_score = cleaned["min_score"]
    limit = cleaned["limit"]

    matches = []
    total_records = NameRecord.objects.count()

    if query:
        candidates = NameRecord.objects.values(
            "id",
            "nombre",
            "paterno",
            "materno",
            "search_full_name",
            "origen",
            "folio_ref",
            "rfc",
        )
        matches = find_name_matches(
            query=query,
            candidates=candidates,
            min_score=min_score,
            limit=limit,
        )

    return render(
        request,
        "coincidencias/home.html",
        {
            "form": form,
            "query": query,
            "matches": matches,
            "total_records": total_records,
            "min_score": min_score,
            "limit": limit,
        },
    )


def lista_oficios(request):
    oficios = Oficio.objects.prefetch_related("personas").order_by(
        "-fecha_publicacion", "-folio"
    )
    return render(
        request,
        "coincidencias/oficios.html",
        {
            "oficios": oficios,
            "total_oficios": oficios.count(),
        },
    )


def comparar_rango(request):
    fecha_desde_str = request.GET.get("fecha_desde", "")
    fecha_hasta_str = request.GET.get("fecha_hasta", "")
    min_score = _parse_score(request.GET.get("min_score"), default=45)

    fecha_desde = _parse_date(fecha_desde_str)
    fecha_hasta = _parse_date(fecha_hasta_str)

    resultados = []
    total_alertas = 0
    total_personas_cnbv = 0
    oficios_en_rango = []

    busqueda_activa = bool(fecha_desde and fecha_hasta)

    if busqueda_activa:
        oficios_en_rango = list(
            Oficio.objects.filter(
                fecha_publicacion__range=[fecha_desde, fecha_hasta]
            ).order_by("-fecha_publicacion")
        )
        personas_cnbv = list(
            PersonaCNBV.objects.filter(
                oficio__in=oficios_en_rango
            ).select_related("oficio")
        )
        total_personas_cnbv = len(personas_cnbv)

        clientes = list(
            NameRecord.objects.values(
                "id", "nombre", "paterno", "materno",
                "search_full_name", "origen", "folio_ref", "rfc",
            )
        )

        for persona in personas_cnbv:
            matches = find_name_matches(
                query=persona.search_full_name,
                candidates=clientes,
                min_score=min_score,
                limit=10,
            )
            if matches:
                total_alertas += 1
                resultados.append({"persona": persona, "matches": matches})

    return render(
        request,
        "coincidencias/comparar_rango.html",
        {
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str,
            "min_score": min_score,
            "resultados": resultados,
            "total_alertas": total_alertas,
            "total_personas_cnbv": total_personas_cnbv,
            "total_clientes": NameRecord.objects.count(),
            "oficios_count": len(oficios_en_rango),
            "busqueda_activa": busqueda_activa,
        },
    )


def comparar_oficio(request, folio):
    oficio = get_object_or_404(Oficio, folio=folio)
    personas_cnbv = list(oficio.personas.all())

    min_score = _parse_score(request.GET.get("min_score"), default=45)

    clientes = list(
        NameRecord.objects.values(
            "id",
            "nombre",
            "paterno",
            "materno",
            "search_full_name",
            "origen",
            "folio_ref",
            "rfc",
        )
    )

    resultados = []
    for persona in personas_cnbv:
        matches = find_name_matches(
            query=persona.search_full_name,
            candidates=clientes,
            min_score=min_score,
            limit=10,
        )
        resultados.append(
            {
                "persona": persona,
                "matches": matches,
                "tiene_coincidencias": bool(matches),
            }
        )

    total_alertas = sum(1 for r in resultados if r["tiene_coincidencias"])
    total_clientes = len(clientes)

    return render(
        request,
        "coincidencias/comparar.html",
        {
            "oficio": oficio,
            "resultados": resultados,
            "total_alertas": total_alertas,
            "total_personas_cnbv": len(personas_cnbv),
            "total_clientes": total_clientes,
            "min_score": min_score,
        },
    )
