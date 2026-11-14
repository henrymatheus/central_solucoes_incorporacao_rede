"""Resolução da gerência de cada nota.

Ordem de prioridade:
1. DE-PARA MEDIDA|CENTRO_TRABALHO (tabela do BI, editável no Admin) — gerência da etapa atual;
2. GERENCIA do SQL traduzida pela tabela de equivalência (editável no Admin);
3. GERENCIA do SQL como veio (ou "Não mapeada").
"""

from apps.incorporacao import regras
from apps.incorporacao.models import OrigemGerencia

NAO_MAPEADA = "Não mapeada"


def resolvedor():
    from apps.integracao.models import DeParaMedidaGerencia, EquivalenciaGerencia

    depara = {d.chave: d for d in DeParaMedidaGerencia.objects.all()}
    equivalencia = dict(EquivalenciaGerencia.objects.values_list("gerencia_sql", "gerencia"))

    def resolver(medida, centro_trabalho, gerencia_sql):
        """Devolve (gerencia, etapa, origem)."""
        mapa = depara.get(regras.chave_mapeamento(medida, centro_trabalho))
        if mapa:
            return mapa.gerencia, mapa.etapa, OrigemGerencia.DEPARA
        etapa = regras.etapa_calculada(medida)
        sql = (gerencia_sql or "").strip()
        if sql in equivalencia:
            return equivalencia[sql], etapa, OrigemGerencia.EQUIVALENCIA
        if not sql or sql == "Não Mapeado":
            return NAO_MAPEADA, etapa, OrigemGerencia.SQL
        return sql, etapa, OrigemGerencia.SQL

    return resolver


def recalcular_gerencias():
    """Reaplica a resolução em toda a carteira (após editar o DE-PARA ou as equivalências)."""
    from apps.incorporacao.models import NotaIR

    resolver = resolvedor()
    notas = list(NotaIR.objects.all())
    for n in notas:
        n.gerencia, n.etapa, n.origem_gerencia = resolver(
            n.medida_atual, n.centro_trabalho, n.dados.get("GERENCIA")
        )
    NotaIR.objects.bulk_update(notas, ["gerencia", "etapa", "origem_gerencia"], batch_size=1000)
    return len(notas)
