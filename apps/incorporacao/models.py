"""Carteira de notas de incorporação (IR), sincronizada da SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO.

- NotaIR: estado ATUAL de cada nota (uma linha por NOTA). É substituída a cada sincronização.
- NotaHistorico: foto diária resumida de cada nota. A tabela de origem só traz o estado atual;
  o histórico é o que permite ver a linha do tempo da nota e a movimentação entre datas.
- Acompanhamento: registros feitos pela equipe na ficha da nota. Ligados pelo número da nota
  (não por chave estrangeira), para sobreviverem à substituição da NotaIR a cada sincronização.

Ver docs/MAPEAMENTO_SNOWFLAKE.md para a origem de cada coluna.
"""

from django.conf import settings
from django.db import models


class Situacao(models.TextChoices):
    ATIVA = "ativa", "Ativa"
    FINALIZADA = "finalizada", "Finalizada"
    CANCELADA = "cancelada", "Cancelada"


class OrigemGerencia(models.TextChoices):
    DEPARA = "depara", "DE-PARA medida/centro"
    EQUIVALENCIA = "equivalencia", "Gerência do SQL (equivalência)"
    SQL = "sql", "Gerência do SQL"


class NotaIR(models.Model):
    estado = models.CharField(max_length=2, db_index=True)
    nota = models.CharField(max_length=20, unique=True)
    tipo_nota = models.CharField(max_length=5, blank=True)
    status_ccs = models.CharField(max_length=10, blank=True, db_index=True)
    situacao = models.CharField(
        max_length=12, choices=Situacao.choices, default=Situacao.ATIVA, db_index=True
    )
    gerencia = models.CharField(max_length=60, blank=True, db_index=True)
    origem_gerencia = models.CharField(max_length=12, choices=OrigemGerencia.choices, blank=True)
    etapa = models.CharField(max_length=40, blank=True)
    nota_proj = models.CharField(max_length=20, blank=True, db_index=True)
    pep = models.CharField(max_length=60, blank=True)
    pep_i = models.CharField(max_length=300, blank=True)
    medida_atual = models.CharField(max_length=20, blank=True, db_index=True)
    texto_medida_atual = models.CharField(max_length=200, blank=True)
    medida_anterior = models.CharField(max_length=20, blank=True)
    texto_breve_grupo_codigo = models.CharField(max_length=160, blank=True)
    centro_trabalho = models.CharField(max_length=20, blank=True)
    regional = models.CharField(max_length=60, blank=True, db_index=True)
    municipio = models.CharField(max_length=120, blank=True)
    carteira_cliente = models.CharField(max_length=80, blank=True)
    status_fiscalizacao = models.CharField(max_length=160, blank=True)
    status_sgo = models.CharField(max_length=80, blank=True)
    cliente_ligado = models.CharField(max_length=40, blank=True)
    data_criacao = models.DateField(null=True, blank=True, db_index=True)
    data_encerramento = models.DateField(null=True, blank=True, db_index=True)
    fim_desejado = models.DateField(null=True, blank=True)
    inicio_avaria = models.DateField(null=True, blank=True)
    inicio_avaria_nota_vinculada = models.DateField(null=True, blank=True)
    data_criacao_medida = models.DateField(null=True, blank=True)
    fim_programado_medida = models.DateField(null=True, blank=True)
    data_conclusao_medida = models.DateField(null=True, blank=True)
    vl_total_orcamento = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    multa = models.FloatField(null=True, blank=True)
    qtd_clientes_ligados = models.IntegerField(default=0)
    dados = models.JSONField(default=dict, help_text="Linha completa (85 colunas) como texto.")
    sincronizado_em = models.DateTimeField()

    class Meta:
        ordering = ["-data_criacao", "nota"]
        verbose_name = "Nota IR"
        verbose_name_plural = "Notas IR"
        indexes = [models.Index(fields=["estado", "regional"])]

    def __str__(self):
        return f"{self.nota} ({self.estado})"

    @property
    def ativa(self):
        return self.situacao == Situacao.ATIVA


class NotaHistorico(models.Model):
    """Foto diária de uma nota (gravada pela sincronização)."""

    data = models.DateField(db_index=True)
    nota = models.CharField(max_length=20, db_index=True)
    estado = models.CharField(max_length=2)
    regional = models.CharField(max_length=60, blank=True)
    gerencia = models.CharField(max_length=60, blank=True)
    medida = models.CharField(max_length=20, blank=True)
    situacao = models.CharField(max_length=12, choices=Situacao.choices)
    fim_programado_medida = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["nota", "data"]
        verbose_name = "Histórico diário da nota"
        verbose_name_plural = "Histórico diário das notas"
        constraints = [
            models.UniqueConstraint(fields=["data", "nota"], name="uniq_historico_data_nota")
        ]


class Acompanhamento(models.Model):
    nota = models.CharField(max_length=20, db_index=True)
    estado = models.CharField(max_length=2)
    texto = models.TextField()
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Acompanhamento da nota"
        verbose_name_plural = "Acompanhamentos das notas"

    def __str__(self):
        return f"{self.nota} · {self.criado_em:%d/%m/%Y %H:%M}"
