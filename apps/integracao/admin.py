from django.contrib import admin

from apps.integracao.models import (
    DeParaMedidaGerencia,
    EquivalenciaGerencia,
    ExecucaoETL,
    StatusFiscalizacao,
)


@admin.register(DeParaMedidaGerencia)
class DeParaMedidaGerenciaAdmin(admin.ModelAdmin):
    list_display = ("medida", "centro_trabalho", "gerencia", "etapa", "texto_breve_grupo_codigo")
    list_filter = ("gerencia", "etapa")
    search_fields = ("medida", "centro_trabalho", "texto_breve_grupo_codigo")

    def save_model(self, request, obj, form, change):
        obj.chave = f"{obj.medida.strip()}|{obj.centro_trabalho.strip()}"
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        return ("chave",)


@admin.register(StatusFiscalizacao)
class StatusFiscalizacaoAdmin(admin.ModelAdmin):
    list_display = ("ordem", "status_sisco", "status_macro", "status_detalhado")


@admin.register(ExecucaoETL)
class ExecucaoETLAdmin(admin.ModelAdmin):
    list_display = ("job", "iniciado_em", "finalizado_em", "status", "registros_lidos")
    list_filter = ("job", "status")
    readonly_fields = [f.name for f in ExecucaoETL._meta.fields]


@admin.register(EquivalenciaGerencia)
class EquivalenciaGerenciaAdmin(admin.ModelAdmin):
    list_display = ("gerencia_sql", "gerencia", "observacao")
    search_fields = ("gerencia_sql", "gerencia")
