from django.contrib import admin

from apps.incorporacao.models import Acompanhamento, NotaIR


@admin.register(NotaIR)
class NotaIRAdmin(admin.ModelAdmin):
    list_display = (
        "nota",
        "estado",
        "regional",
        "gerencia",
        "origem_gerencia",
        "medida_atual",
        "situacao",
        "data_criacao",
    )
    list_filter = ("estado", "situacao", "origem_gerencia", "gerencia")
    search_fields = ("nota", "nota_proj", "pep")
    readonly_fields = [f.name for f in NotaIR._meta.fields]

    def has_add_permission(self, request):
        return False  # alimentada só pela sincronização com o Snowflake


@admin.register(Acompanhamento)
class AcompanhamentoAdmin(admin.ModelAdmin):
    list_display = ("nota", "estado", "autor", "criado_em")
    list_filter = ("estado",)
    search_fields = ("nota", "texto")
    readonly_fields = ("criado_em",)
