from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.models import (
    CentroTrabalho,
    Distribuidora,
    Municipio,
    ParametroSistema,
    Perfil,
    Regional,
    Usuario,
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Dados corporativos", {"fields": ("matricula",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Dados corporativos", {"fields": ("matricula",)}),)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo")
    list_filter = ("tipo",)
    filter_horizontal = ("distribuidoras", "regionais")


admin.site.register((Distribuidora, Regional, Municipio, CentroTrabalho, ParametroSistema))
