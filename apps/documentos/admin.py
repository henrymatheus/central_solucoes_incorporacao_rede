from django.contrib import admin

from apps.documentos.models import DocumentoModelo, RegistroDownload


@admin.register(DocumentoModelo)
class DocumentoModeloAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "versao", "vigente", "distribuidora")
    list_filter = ("categoria", "vigente", "distribuidora")
    search_fields = ("titulo", "descricao")


admin.site.register(RegistroDownload)
