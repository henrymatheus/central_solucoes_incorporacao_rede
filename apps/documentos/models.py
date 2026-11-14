from django.conf import settings
from django.db import models

from apps.core.models import Distribuidora, TimeStamped


class DocumentoModelo(TimeStamped):
    CATEGORIAS = [
        ("ORCAMENTO", "Orçamento"),
        ("CHECKLIST", "Checklist"),
        ("TERMO", "Termos"),
        ("POP", "Procedimentos"),
        ("OUTRO", "Outros"),
    ]
    titulo = models.CharField(max_length=180)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default="OUTRO")
    descricao = models.TextField(blank=True)
    arquivo = models.FileField(upload_to="documentos-modelo/%Y/%m/")
    versao = models.PositiveIntegerField(default=1)
    vigente = models.BooleanField(default=True)
    distribuidora = models.ForeignKey(
        Distribuidora, null=True, blank=True, on_delete=models.CASCADE
    )
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["categoria", "titulo", "-versao"]
        constraints = [
            models.UniqueConstraint(
                fields=["titulo", "categoria", "versao"], name="uniq_documento_versao"
            )
        ]

    def __str__(self):
        return f"{self.titulo} v{self.versao}"


class RegistroDownload(models.Model):
    documento = models.ForeignKey(
        DocumentoModelo, on_delete=models.PROTECT, related_name="downloads"
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    baixado_em = models.DateTimeField(auto_now_add=True)
