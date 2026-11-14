from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeStamped(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Distribuidora(TimeStamped):
    sigla = models.CharField(max_length=10, unique=True)
    nome = models.CharField(max_length=120)
    nome_catalogo = models.CharField(max_length=60, unique=True)
    uf = models.CharField(max_length=2)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["sigla"]
        verbose_name = "Distribuidora"
        verbose_name_plural = "Distribuidoras"

    def __str__(self):
        return f"{self.sigla} — {self.nome}"


class Regional(TimeStamped):
    distribuidora = models.ForeignKey(
        Distribuidora, on_delete=models.CASCADE, related_name="regionais"
    )
    nome = models.CharField(max_length=60)

    class Meta:
        ordering = ["distribuidora", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["distribuidora", "nome"], name="uniq_regional_distribuidora"
            )
        ]

    def __str__(self):
        return f"{self.distribuidora.sigla}/{self.nome}"


class Municipio(TimeStamped):
    distribuidora = models.ForeignKey(
        Distribuidora, on_delete=models.CASCADE, related_name="municipios"
    )
    regional = models.ForeignKey(Regional, on_delete=models.PROTECT, related_name="municipios")
    nome = models.CharField(max_length=120)

    class Meta:
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["distribuidora", "nome"], name="uniq_municipio_distribuidora"
            )
        ]

    def __str__(self):
        return self.nome


class CentroTrabalho(TimeStamped):
    codigo = models.CharField(max_length=20, unique=True)
    descricao = models.CharField(max_length=160, blank=True)
    gerencia_sap = models.CharField(max_length=60, blank=True)
    distribuidora = models.ForeignKey(
        Distribuidora, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.codigo


class Usuario(AbstractUser):
    matricula = models.CharField(max_length=20, blank=True)


class Perfil(TimeStamped):
    class Tipo(models.TextChoices):
        TATICO = "TATICO", "Tático"
        RELACIONAMENTO = "RELACIONAMENTO", "Relacionamento"
        ATIVOS = "ATIVOS", "Ativos"
        CADASTRO = "CADASTRO", "Cadastro"
        FINANCEIRO = "FINANCEIRO", "Financeiro"
        DEV = "DEV", "Desenvolvedor"

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name="perfil")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.TATICO)
    distribuidoras = models.ManyToManyField(Distribuidora, blank=True, related_name="perfis")
    regionais = models.ManyToManyField(Regional, blank=True, related_name="perfis")

    def __str__(self):
        return f"{self.usuario} — {self.get_tipo_display()}"


class ParametroSistema(TimeStamped):
    chave = models.CharField(max_length=60, unique=True)
    valor = models.CharField(max_length=200)
    descricao = models.CharField(max_length=240, blank=True)

    def __str__(self):
        return f"{self.chave} = {self.valor}"


class EnvioFormulario(models.Model):
    """Registro de idempotência: cada formulário renderizado recebe uma chave única.

    Um segundo POST com a mesma chave (duplo clique, Enter + clique, reenvio) é
    reconhecido e não cria registros duplicados.
    """

    chave = models.CharField(max_length=64, unique=True)
    usuario = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL)
    resultado_url = models.CharField(max_length=300, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Envio de formulário"
        verbose_name_plural = "Envios de formulário"

    def __str__(self):
        return self.chave
