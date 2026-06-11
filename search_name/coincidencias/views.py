from django.shortcuts import get_object_or_404, render

from .forms import NameSearchForm
from .matching import find_name_matches
from .models import NameRecord, Oficio, PersonaCNBV


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


def comparar_oficio(request, folio):
    oficio = get_object_or_404(Oficio, folio=folio)
    personas_cnbv = list(oficio.personas.all())

    try:
        min_score = max(0, min(100, int(request.GET.get("min_score", 45))))
    except (ValueError, TypeError):
        min_score = 45

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
