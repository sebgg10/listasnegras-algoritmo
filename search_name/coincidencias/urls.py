from django.urls import path

from .views import (
    comparar_oficio,
    lista_oficios,
    revisar_clientes,
    search_names,
)

urlpatterns = [
    path("", search_names, name="search_names"),
    path("oficios/", lista_oficios, name="lista_oficios"),
    path("oficios/<int:folio>/comparar/", comparar_oficio, name="comparar_oficio"),
    path("revisar-clientes/", revisar_clientes, name="revisar_clientes"),
]
