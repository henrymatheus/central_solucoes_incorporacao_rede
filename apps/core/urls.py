from django.urls import path

from apps.core import views

urlpatterns = [
    path("login/", views.LoginPage.as_view(), name="login"),
    path("logout/", views.sair, name="logout"),
]
