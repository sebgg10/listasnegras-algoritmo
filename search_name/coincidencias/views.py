from django.shortcuts import get_object_or_404, render

from .forms import NameSearchForm
from .matching import find_name_matches
from .models import NameRecord, Oficio, PersonaCNBV

# Orígenes de NameRecord que provienen de los propios oficios (no son clientes reales).
ORIGENES_OFICIO = ("SolicitudPartes", "PersonasSolicitud")


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

    # IDs de clientes seleccionados en el menú.
    try:
        selected_ids = [int(x) for x in request.GET.getlist("clientes") if x]
    except ValueError:
        selected_ids = []

    # Menú de clientes reales (no derivados de oficios).
    clientes_qs = NameRecord.objects.exclude(origen__in=ORIGENES_OFICIO)
    clientes_menu = list(
        clientes_qs.values("id", "search_full_name").order_by("search_full_name")
    )
    clientes_by_id = {c["id"]: c for c in clientes_menu}

    # Candidatos = LISTA NEGRA (personas señaladas en los oficios de la CNBV).
    # Aquí buscamos si los clientes están "funados".
    personas_negras = PersonaCNBV.objects.select_related("oficio")
    candidatos_negros = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "paterno": p.paterno,
            "materno": p.materno,
            "search_full_name": p.search_full_name,
            "rfc": p.rfc,
            "folio_ref": p.oficio.folio,
        }
        for p in personas_negras
    ]

    search_groups = []

    def _make_group(label, matches, es_cliente):
        return {
            "label": label,
            "es_cliente": es_cliente,
            "matches": matches,
            "count": len(matches),
            "best_score": matches[0]["score"] if matches else 0,
        }

    # 1) Búsqueda por texto libre contra la lista negra.
    if query:
        matches = find_name_matches(
            query=query, candidates=candidatos_negros, min_score=min_score, limit=limit
        )
        search_groups.append(_make_group(query, matches, es_cliente=False))

    # 2) Clientes seleccionados contra la lista negra.
    if selected_ids:
        for cid in selected_ids:
            cliente = clientes_by_id.get(cid)
            if not cliente:
                continue
            matches = find_name_matches(
                query=cliente["search_full_name"],
                candidates=candidatos_negros,
                min_score=min_score,
                limit=limit,
            )
            search_groups.append(
                _make_group(cliente["search_full_name"], matches, es_cliente=True)
            )

    return render(
        request,
        "coincidencias/home.html",
        {
            "form": form,
            "query": query,
            "clientes_menu": clientes_menu,
            "selected_ids": selected_ids,
            "search_groups": search_groups,
            "busqueda_activa": bool(query or selected_ids),
            "total_records": len(candidatos_negros),
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


def revisar_clientes(request):
    """Compara TODOS los clientes registrados contra la lista negra de un rango de
    fechas (por defecto los últimos 7 días) y devuelve una tabla de coincidencias:
    una fila por cada par (cliente, persona funada)."""
    from datetime import date, timedelta

    min_score = _parse_score(request.GET.get("min_score"), default=70)

    # Rango de fechas. Por defecto: últimos 7 días hasta hoy.
    hoy = date.today()
    fecha_desde = _parse_date(request.GET.get("fecha_desde", ""))
    fecha_hasta = _parse_date(request.GET.get("fecha_hasta", ""))
    if not fecha_desde and not fecha_hasta:
        fecha_hasta = hoy
        fecha_desde = hoy - timedelta(days=7)
    elif fecha_desde and not fecha_hasta:
        fecha_hasta = hoy
    elif fecha_hasta and not fecha_desde:
        fecha_desde = fecha_hasta - timedelta(days=7)
    if fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    # Personas de la lista negra en el rango (los candidatos a comparar).
    oficios_en_rango = list(
        Oficio.objects.filter(fecha_publicacion__range=[fecha_desde, fecha_hasta])
    )
    personas_negras = (
        PersonaCNBV.objects.filter(oficio__in=oficios_en_rango).select_related("oficio")
    )
    candidatos_negros = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "paterno": p.paterno,
            "materno": p.materno,
            "search_full_name": p.search_full_name,
            "rfc": p.rfc,
            "folio_ref": p.oficio.folio,
        }
        for p in personas_negras
    ]

    # Clientes reales = NameRecord que NO provienen de los oficios.
    clientes = NameRecord.objects.exclude(origen__in=ORIGENES_OFICIO)

    filas = []  # una fila por cada (cliente, persona funada)
    clientes_funados = set()
    for cliente in clientes:
        if not candidatos_negros:
            break
        matches = find_name_matches(
            query=cliente.search_full_name,
            candidates=candidatos_negros,
            min_score=min_score,
            limit=10,
        )
        if matches:
            clientes_funados.add(cliente.id)
        for match in matches:
            filas.append(
                {
                    "cliente": cliente.search_full_name,
                    "cliente_rfc": cliente.rfc,
                    "persona": match["name"],
                    "persona_rfc": match.get("rfc", ""),
                    "folio_ref": match.get("folio_ref", ""),
                    "score": match["score"],
                    "explanation": match["explanation"],
                }
            )

    # Mismo cliente junto, y dentro del cliente por score descendente.
    filas.sort(key=lambda f: (f["cliente"], -f["score"]))

    return render(
        request,
        "coincidencias/revisar_clientes.html",
        {
            "filas": filas,
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "min_score": min_score,
            "total_clientes": clientes.count(),
            "total_funados": len(clientes_funados),
            "total_coincidencias": len(filas),
            "total_personas_negras": len(candidatos_negros),
            "oficios_count": len(oficios_en_rango),
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
