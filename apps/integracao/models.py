from django.db import models

from apps.core.models import Distribuidora, TimeStamped


class DeParaMedidaGerencia(TimeStamped):
    """Tabela_medidas_gerencia do Power BI: MEDIDA|CENTRO_TRABALHO → gerência e etapa."""

    chave = models.CharField(max_length=60, unique=True, help_text="MEDIDA|CENTRO_TRABALHO")
    medida = models.CharField(max_length=20, db_index=True)
    centro_trabalho = models.CharField(max_length=20, blank=True)
    gerencia = models.CharField(max_length=40)
    etapa = models.CharField(max_length=40)
    texto_breve_grupo_codigo = models.CharField(max_length=160, blank=True)
    gerencia_sap = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["gerencia", "medida", "centro_trabalho"]
        verbose_name = "DE-PARA medida → gerência"
        verbose_name_plural = "DE-PARA medida → gerência"

    def __str__(self):
        return f"{self.chave} → {self.gerencia} / {self.etapa}"


class StatusFiscalizacao(TimeStamped):
    """Tabela_status_fisc do Power BI."""

    status_sisco = models.CharField(max_length=160, unique=True)
    status_macro = models.CharField(max_length=60)
    status_detalhado = models.CharField(max_length=120, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "status_sisco"]
        verbose_name = "Status de fiscalização (SISCO)"
        verbose_name_plural = "Status de fiscalização (SISCO)"

    def __str__(self):
        return self.status_sisco


class ExecucaoETL(models.Model):
    class Status(models.TextChoices):
        EXECUTANDO = "EXEC", "Executando"
        SUCESSO = "OK", "Sucesso"
        ERRO = "ERR", "Erro"

    job = models.CharField(max_length=60)
    distribuidora = models.ForeignKey(
        Distribuidora, null=True, blank=True, on_delete=models.SET_NULL
    )
    iniciado_em = models.DateTimeField(auto_now_add=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=5, choices=Status.choices, default=Status.EXECUTANDO)
    registros_lidos = models.PositiveIntegerField(default=0)
    mensagem = models.TextField(blank=True)

    class Meta:
        ordering = ["-iniciado_em"]
        verbose_name = "Execução de sincronização"
        verbose_name_plural = "Execuções de sincronização"

    def __str__(self):
        return f"{self.job} {self.iniciado_em:%d/%m/%Y %H:%M} ({self.get_status_display()})"


class EquivalenciaGerencia(TimeStamped):
    """Nome da GERENCIA do SQL (TAB_CENTRO_TRABALHO_GERENCIA) → nome usado no sistema.

    Usada quando a nota não tem MEDIDA|CENTRO no DE-PARA (hoje, notas fora do Pará).
    As equivalências iniciais foram medidas nas notas do Pará, onde as duas fontes existem.
    """

    gerencia_sql = models.CharField(max_length=80, unique=True)
    gerencia = models.CharField(max_length=60)
    observacao = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["gerencia_sql"]
        verbose_name = "Equivalência de gerência (SQL → sistema)"
        verbose_name_plural = "Equivalências de gerência (SQL → sistema)"

    def __str__(self):
        return f"{self.gerencia_sql} → {self.gerencia}"
