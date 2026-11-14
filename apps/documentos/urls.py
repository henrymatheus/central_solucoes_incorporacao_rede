from django.urls import path

from apps.documentos import views

app_name = "documentos"
urlpatterns = [
    path("", views.lista_documentos, name="lista"),
    path("novo/", views.enviar_documento, name="enviar"),
    path("<int:pk>/download/", views.baixar_documento, name="download"),
]
