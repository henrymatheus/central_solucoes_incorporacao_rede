"""Carga idempotente das tabelas de apoio do BI (DE-PARA e status SISCO)."""

from apps.integracao.dados_bi import DE_PARA_MEDIDAS, STATUS_FISCALIZACAO


def carregar_tabelas_apoio(DeParaMedidaGerencia, StatusFiscalizacao):
    """Recebe as classes (reais ou do estado da migração) e faz upsert pelos dados do BI."""
    for medida, centro, gerencia, etapa, texto, gerencia_sap in DE_PARA_MEDIDAS:
        DeParaMedidaGerencia.objects.update_or_create(
            chave=f"{medida}|{centro}",
            defaults={
                "medida": medida,
                "centro_trabalho": centro,
                "gerencia": gerencia,
                "etapa": etapa,
                "texto_breve_grupo_codigo": texto,
                "gerencia_sap": gerencia_sap,
            },
        )
    for sisco, macro, detalhado, ordem in STATUS_FISCALIZACAO:
        StatusFiscalizacao.objects.update_or_create(
            status_sisco=sisco,
            defaults={"status_macro": macro, "status_detalhado": detalhado, "ordem": ordem},
        )
