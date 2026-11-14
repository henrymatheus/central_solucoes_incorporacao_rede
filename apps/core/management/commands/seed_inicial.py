from django.core.management.base import BaseCommand

from apps.core.models import Distribuidora, ParametroSistema
from apps.integracao.carga import carregar_tabelas_apoio
from apps.integracao.models import DeParaMedidaGerencia, StatusFiscalizacao

DISTRIBUIDORAS = [
    ("EQTL-AL", "Equatorial Alagoas", "ALAGOAS", "AL"),
    ("EQTL-AP", "Equatorial Amapá", "AMAPÁ", "AP"),
    ("EQTL-GO", "Equatorial Goiás", "GOIÁS", "GO"),
    ("EQTL-MA", "Equatorial Maranhão", "MARANHÃO", "MA"),
    ("EQTL-PA", "Equatorial Pará", "PARÁ", "PA"),
    ("EQTL-PI", "Equatorial Piauí", "PIAUÍ", "PI"),
    ("EQTL-RS", "Equatorial Rio Grande do Sul", "RIO.GRANDE.DO.SUL", "RS"),
]

PARAMETROS = [
    ("SLA_NOTA_DIAS", "90"),
    ("SLA_NOTA_VINCULADA_DIAS", "30"),
    ("SLA_ALERTA_DIAS", "5"),
    ("SLA_RESTITUICAO_DIAS", "90"),
    ("ANOS_COMPULSORIA", "5"),
    ("DATA_CORTE_GIRO", "2026-01-01"),
    ("DATA_CORTE_RTP26", "2023-12-01"),
    ("DEMANDA_LIMITE_RESTITUICAO_KW", "50"),
    ("ORCAMENTO_LINHAS_MATERIAL", "55"),
    ("ORCAMENTO_LINHAS_MAO_OBRA", "10"),
]


class Command(BaseCommand):
    help = (
        "Carrega distribuidoras, parâmetros e as tabelas de apoio do BI (DE-PARA e status SISCO)."
    )

    def handle(self, *args, **options):
        for sigla, nome, catalogo, uf in DISTRIBUIDORAS:
            Distribuidora.objects.update_or_create(
                sigla=sigla,
                defaults={"nome": nome, "nome_catalogo": catalogo, "uf": uf},
            )
        for chave, valor in PARAMETROS:
            ParametroSistema.objects.update_or_create(chave=chave, defaults={"valor": valor})
        carregar_tabelas_apoio(DeParaMedidaGerencia, StatusFiscalizacao)
        self.stdout.write(self.style.SUCCESS("Carga inicial concluída."))
