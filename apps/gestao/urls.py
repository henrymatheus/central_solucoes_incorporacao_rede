from django.urls import path

from apps.gestao import views

app_name = "gestao"
urlpatterns = [
    path("", views.visao_geral, name="visao_geral"),
    path("analise/", views.analise, name="analise"),
    path("prazos/", views.prazos, name="prazos"),
    path("notas/", views.notas, name="notas"),
    path("notas/exportar/", views.exportar, name="exportar"),
    path("notas/<str:numero>/", views.nota, name="nota"),
    path("notas/<str:numero>/acompanhamento/", views.acompanhar, name="acompanhar"),
]
