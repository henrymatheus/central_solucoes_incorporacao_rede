"""Indicadores de gestão da carteira de notas de incorporação.

Funções puras sobre a NotaIR. A carteira tem poucos milhares de notas, então o cálculo é feito
em memória a cada requisição: prazos e idades ficam sempre atuais em relação a "hoje".

Regras (decisões do negócio registradas na especificação §24):
- Nota ATIVA = STATUS_CCS diferente de FINL/CANC.
- Prazo da nota = FIM_DESEJADO. Prazo da medida = FIM_PROGRAMADO_MEDIDA (sem DATA_CONCLUSAO_MEDIDA).
- Faixas de prazo: vencida (< hoje) · vence em até 7 dias · no prazo · sem prazo.
- Entrante = DATA_CRIACAO da nota. Encerrada = DATA_ENCERRAMENTO_NOTA de nota finalizada/cancelada.
"""

from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal

from apps.incorporacao.models import NotaIR, Situacao

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
JANELA_A_VENCER = 7

DIMENSOES = {"estado": "Estado", "regional": "Regional", "gerencia": "Gerência", "medida": "Medida"}
PROXIMO_NIVEL = {"estado": "regional", "regional": "gerencia", "gerencia": "medida", "medida": None}

PRAZOS = {
    "vencida": "Vencida",
    "a_vencer": f"Vence em até {JANELA_A_VENCER} dias",
    "no_prazo": "No prazo",
    "sem_prazo": "Sem prazo",
}
PRAZOS_MEDIDA = {**PRAZOS, "concluida": "Medida concluída"}

ATRASOS = {
    "ate30": "Até 30 dias",
    "31a90": "31 a 90 dias",
    "91a180": "91 a 180 dias",
    "181a365": "181 dias a 1 ano",
    "1a2": "1 a 2 anos",
    "mais2": "Mais de 2 anos",
}
IDADES = {
    "ate30": "Até 30 dias",
    "31a90": "31 a 90 dias",
    "91a180": "91 a 180 dias",
    "181a365": "181 dias a 1 ano",
    "1a2": "1 a 2 anos",
    "2a5": "2 a 5 anos",
    "mais5": "Mais de 5 anos",
    "sem": "Sem data",
}
SITUACOES = {
    "ativa": "Ativas",
    "encerradas": "Encerradas",
    "finalizada": "Finalizadas",
    "cancelada": "Canceladas",
    "todas": "Todas",
}
ORDENS = {
    "atraso": "Maior atraso",
    "parada": "Mais tempo na medida",
    "idade": "Mais antigas",
    "recentes": "Mais recentes",
    "valor": "Maior valor",
}
PERIODOS = {"7": "7 dias", "30": "30 dias", "90": "90 dias", "365": "12 meses"}


# --------------------------------------------------------------------------- classificação


def faixa_prazo(dias):
    if dias is None:
        return "sem_prazo"
    if dias < 0:
        return "vencida"
    if dias <= JANELA_A_VENCER:
        return "a_vencer"
    return "no_prazo"


def faixa_atraso(dias_atraso):
    if dias_atraso is None or dias_atraso <= 0:
        return ""
    for limite, chave in (
        (30, "ate30"),
        (90, "31a90"),
        (180, "91a180"),
        (365, "181a365"),
        (730, "1a2"),
    ):
        if dias_atraso <= limite:
            return chave
    return "mais2"


def faixa_idade(dias):
    if dias is None:
        return "sem"
    for limite, chave in (
        (30, "ate30"), (90, "31a90"), (180, "91a180"), (365, "181a365"), (730, "1a2"), (1826, "2a5"),
    ):  # fmt: skip
        if dias <= limite:
            return chave
    return "mais5"


def _dias(ate, de):
    return (ate - de).days if ate and de else None


def linha(n, hoje):
    """Uma nota com tudo o que as telas de gestão precisam, já calculado."""
    ativa = n.situacao == Situacao.ATIVA
    dias_nota = _dias(n.fim_desejado, hoje)
    if n.data_conclusao_medida:
        dias_medida, prazo_medida = None, "concluida"
    else:
        dias_medida = _dias(n.fim_programado_medida, hoje)
        prazo_medida = faixa_prazo(dias_medida)
    prazo_nota = faixa_prazo(dias_nota)
    idade = _dias(hoje, n.data_criacao)
    return {
        "obj": n,
        "nota": n.nota,
        "estado": n.estado,
        "regional": n.regional or "Sem regional",
        "gerencia": n.gerencia or "Não mapeada",
        "medida": n.medida_atual or "Sem medida",
        "medida_texto": n.texto_breve_grupo_codigo,
        "ativa": ativa,
        "situacao": n.situacao,
        "prazo_nota": prazo_nota if ativa else "",
        "dias_nota": dias_nota,
        "atraso_nota": -dias_nota if ativa and dias_nota is not None and dias_nota < 0 else 0,
        "faixa_atraso": faixa_atraso(-dias_nota) if ativa and dias_nota is not None else "",
        "prazo_medida": prazo_medida if ativa else "",
        "dias_medida": dias_medida,
        "atraso_medida": -dias_medida
        if ativa and dias_medida is not None and dias_medida < 0
        else 0,
        "dias_na_medida": _dias(hoje, n.data_criacao_medida) if ativa else None,
        "idade": idade,
        "faixa_idade": faixa_idade(idade),
        "valor": n.vl_total_orcamento or Decimal("0"),
        "criacao": n.data_criacao,
        "encerramento": n.data_encerramento if not ativa else None,
    }


# --------------------------------------------------------------------------- carga e filtros


def carregar(ufs, filtros, hoje):
    """Notas visíveis (escopo por UF) com os filtros de dimensão aplicados no banco."""
    qs = NotaIR.objects.all()
    if ufs is not None:
        qs = qs.filter(estado__in=ufs)
    campos = {
        "estado": "estado",
        "regional": "regional",
        "gerencia": "gerencia",
        "medida": "medida_atual",
    }
    for chave, campo in campos.items():
        valor = filtros.get(chave)
        if valor:
            qs = qs.filter(**{campo: valor})
    return [linha(n, hoje) for n in qs.iterator()]


def opcoes(ufs):
    """Valores disponíveis nos filtros de dimensão."""
    qs = NotaIR.objects.all()
    if ufs is not None:
        qs = qs.filter(estado__in=ufs)

    def valores(campo):
        # order_by() vazio: a ordenação padrão do modelo impediria o DISTINCT.
        return sorted(v for v in qs.order_by().values_list(campo, flat=True).distinct() if v)

    return {
        "estado": valores("estado"),
        "regional": valores("regional"),
        "gerencia": valores("gerencia"),
        "medida": valores("medida_atual"),
    }


def filtrar_lista(linhas, f):
    """Filtros da lista de notas (além das dimensões, já aplicadas no banco)."""
    situacao = f.get("situacao") or "ativa"
    if situacao == "ativa":
        linhas = [r for r in linhas if r["ativa"]]
    elif situacao == "encerradas":
        linhas = [r for r in linhas if not r["ativa"]]
    elif situacao in ("finalizada", "cancelada"):
        linhas = [r for r in linhas if r["situacao"] == situacao]
    for campo in ("prazo_nota", "prazo_medida", "faixa_atraso", "faixa_idade"):
        if f.get(campo):
            linhas = [r for r in linhas if r[campo] == f[campo]]
    if f.get("criada_de"):
        linhas = [r for r in linhas if r["criacao"] and r["criacao"] >= f["criada_de"]]
    if f.get("criada_ate"):
        linhas = [r for r in linhas if r["criacao"] and r["criacao"] <= f["criada_ate"]]
    if f.get("encerrada_de"):
        linhas = [r for r in linhas if r["encerramento"] and r["encerramento"] >= f["encerrada_de"]]
    if f.get("encerrada_ate"):
        linhas = [
            r for r in linhas if r["encerramento"] and r["encerramento"] <= f["encerrada_ate"]
        ]
    termo = (f.get("q") or "").strip().upper()
    if termo:
        linhas = [
            r
            for r in linhas
            if termo in r["nota"]
            or termo in (r["obj"].nota_proj or "")
            or termo in (r["obj"].municipio or "").upper()
            or termo in (r["obj"].pep or "").upper()
        ]
    return ordenar(linhas, f.get("ordem") or "atraso")


def ordenar(linhas, ordem):
    chaves = {
        "atraso": lambda r: (-r["atraso_nota"], -(r["dias_na_medida"] or 0)),
        "parada": lambda r: -(r["dias_na_medida"] or 0),
        "idade": lambda r: -(r["idade"] or 0),
        "recentes": lambda r: r["idade"] if r["idade"] is not None else 10**6,
        "valor": lambda r: -r["valor"],
    }
    return sorted(linhas, key=chaves.get(ordem, chaves["atraso"]))


# --------------------------------------------------------------------------- agregações


def _pct(parte, todo):
    return round(100 * parte / todo, 1) if todo else 0


def _media(soma, qtd):
    return round(soma / qtd) if qtd else None


def resumo(linhas, hoje, periodo_dias=30):
    """KPIs da carteira: estoque, fluxo recente e prazos."""
    ativas = [r for r in linhas if r["ativa"]]
    inicio = hoje - timedelta(days=periodo_dias - 1)
    inicio_mes = hoje.replace(day=1)
    prazo = Counter(r["prazo_nota"] for r in ativas)
    prazo_med = Counter(r["prazo_medida"] for r in ativas)
    encerradas_mes = [r for r in linhas if r["encerramento"] and r["encerramento"] >= inicio_mes]
    total = len(ativas)
    return {
        "ativas": total,
        "valor": sum((r["valor"] for r in ativas), Decimal("0")),
        "entrantes_hoje": sum(1 for r in linhas if r["criacao"] == hoje),
        "entrantes_7": sum(
            1 for r in linhas if r["criacao"] and r["criacao"] > hoje - timedelta(days=7)
        ),
        "entrantes_mes": sum(1 for r in linhas if r["criacao"] and r["criacao"] >= inicio_mes),
        "entrantes_periodo": sum(1 for r in linhas if r["criacao"] and r["criacao"] >= inicio),
        "encerradas_periodo": sum(
            1 for r in linhas if r["encerramento"] and r["encerramento"] >= inicio
        ),
        "encerradas_mes": len(encerradas_mes),
        "finalizadas_mes": sum(1 for r in encerradas_mes if r["situacao"] == Situacao.FINALIZADA),
        "canceladas_mes": sum(1 for r in encerradas_mes if r["situacao"] == Situacao.CANCELADA),
        "notas_vencidas": prazo["vencida"],
        "notas_vencidas_pct": _pct(prazo["vencida"], total),
        "notas_a_vencer": prazo["a_vencer"],
        "notas_no_prazo": prazo["no_prazo"],
        "notas_sem_prazo": prazo["sem_prazo"],
        "medidas_vencidas": prazo_med["vencida"],
        "medidas_vencidas_pct": _pct(prazo_med["vencida"], total),
        "medidas_a_vencer": prazo_med["a_vencer"],
        "medidas_no_prazo": prazo_med["no_prazo"],
        "medidas_concluidas": prazo_med["concluida"],
        "atraso_mediano": _mediana([r["atraso_nota"] for r in ativas if r["atraso_nota"]]),
        "idade_media": _media(
            sum(r["idade"] or 0 for r in ativas), sum(1 for r in ativas if r["idade"] is not None)
        ),
        "periodo_dias": periodo_dias,
    }


def _mediana(valores):
    if not valores:
        return None
    v = sorted(valores)
    meio = len(v) // 2
    return v[meio] if len(v) % 2 else round((v[meio - 1] + v[meio]) / 2)


def por_dimensao(linhas, dim, hoje, periodo_dias=30):
    """Uma linha por valor da dimensão: estoque, fluxo no período, prazos e idade."""
    inicio = hoje - timedelta(days=periodo_dias - 1)
    grupos = defaultdict(lambda: defaultdict(int))
    textos = {}
    for r in linhas:
        g = grupos[r[dim]]
        if r["criacao"] and r["criacao"] >= inicio:
            g["entrantes"] += 1
        if r["encerramento"] and r["encerramento"] >= inicio:
            g["encerradas"] += 1
        if not r["ativa"]:
            continue
        g["ativas"] += 1
        g["valor"] += r["valor"]
        g["vencidas"] += r["prazo_nota"] == "vencida"
        g["a_vencer"] += r["prazo_nota"] == "a_vencer"
        g["medidas_vencidas"] += r["prazo_medida"] == "vencida"
        g["soma_atraso"] += r["atraso_nota"]
        if r["idade"] is not None:
            g["soma_idade"] += r["idade"]
            g["com_idade"] += 1
        if r["dias_na_medida"] is not None:
            g["soma_parada"] += r["dias_na_medida"]
            g["com_parada"] += 1
        if dim == "medida" and r["medida_texto"]:
            textos[r["medida"]] = r["medida_texto"]
    total_ativas = sum(g["ativas"] for g in grupos.values())
    saida = []
    for chave, g in grupos.items():
        saida.append(_fechar(chave, g, total_ativas, textos.get(chave, "")))
    saida.sort(key=lambda x: (-x["ativas"], -x["entrantes"], x["chave"]))
    total = defaultdict(int)
    for g in grupos.values():
        for k, v in g.items():
            total[k] += v
    return saida, _fechar("Total", total, total_ativas, "")


def _fechar(chave, g, total_ativas, texto):
    ativas = g["ativas"]
    return {
        "chave": chave,
        "texto": texto,
        "ativas": ativas,
        "pct_carteira": _pct(ativas, total_ativas),
        "entrantes": g["entrantes"],
        "encerradas": g["encerradas"],
        "saldo": g["entrantes"] - g["encerradas"],
        "vencidas": g["vencidas"],
        "pct_vencidas": _pct(g["vencidas"], ativas),
        "a_vencer": g["a_vencer"],
        "medidas_vencidas": g["medidas_vencidas"],
        "pct_medidas_vencidas": _pct(g["medidas_vencidas"], ativas),
        "atraso_medio": _media(g["soma_atraso"], g["vencidas"]),
        "idade_media": _media(g["soma_idade"], g["com_idade"]),
        "parada_media": _media(g["soma_parada"], g["com_parada"]),
        "valor": g["valor"] or Decimal("0"),
    }


def _rotulo_mes(d):
    return f"{MESES[d.month - 1]}/{d.year % 100:02d}"


def fluxo(linhas, grao, hoje):
    """Entrantes × encerradas por dia (últimos 60 dias) ou por mês (últimos 24 meses)."""
    if grao == "dia":
        inicio = hoje - timedelta(days=59)
        chaves = [inicio + timedelta(days=i) for i in range(60)]

        def bucket(d):
            return d if d and inicio <= d <= hoje else None

        def rotulo(d):
            return f"{d.day:02d}/{d.month:02d}"

        def intervalo(d):
            return d, d
    else:
        ano, mes = hoje.year, hoje.month
        chaves = []
        for _ in range(24):
            chaves.append(date(ano, mes, 1))
            ano, mes = (ano, mes - 1) if mes > 1 else (ano - 1, 12)
        chaves.reverse()
        primeiro = chaves[0]

        def bucket(d):
            return d.replace(day=1) if d and primeiro <= d <= hoje else None

        rotulo = _rotulo_mes

        def intervalo(d):
            proximo = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
            return d, proximo - timedelta(days=1)

    entr = Counter(bucket(r["criacao"]) for r in linhas)
    enc = Counter(bucket(r["encerramento"]) for r in linhas)
    serie = []
    for k in chaves:
        de, ate = intervalo(k)
        serie.append(
            {
                "rotulo": rotulo(k),
                "entrantes": entr[k],
                "encerradas": enc[k],
                "saldo": entr[k] - enc[k],
                "de": de.isoformat(),
                "ate": ate.isoformat(),
            }
        )
    return serie


def distribuicao(linhas, campo, rotulos):
    """Contagem por faixa, na ordem dos rótulos (só notas ativas)."""
    c = Counter(r[campo] for r in linhas if r["ativa"] and r[campo])
    total = sum(c.values())
    return [
        {"chave": k, "rotulo": v, "valor": c[k], "pct": _pct(c[k], total)}
        for k, v in rotulos.items()
        if c[k] or k not in ("sem", "sem_prazo", "concluida")
    ]


def matriz(linhas, linha_dim, coluna_dim):
    """Notas ativas: linha_dim × coluna_dim (ex.: gerência × estado)."""
    ativas = [r for r in linhas if r["ativa"]]
    colunas = sorted({r[coluna_dim] for r in ativas})
    contagem = Counter((r[linha_dim], r[coluna_dim]) for r in ativas)
    por_linha = Counter(r[linha_dim] for r in ativas)
    maximo = max(contagem.values(), default=0)
    linhas_saida = [
        {
            "chave": chave,
            "celulas": [
                {
                    "coluna": c,
                    "valor": contagem[(chave, c)],
                    "intensidade": _pct(contagem[(chave, c)], maximo),
                }
                for c in colunas
            ],
            "total": total,
        }
        for chave, total in por_linha.most_common()
    ]
    totais = [sum(contagem[(ch, c)] for ch in por_linha) for c in colunas]
    return {"colunas": colunas, "linhas": linhas_saida, "totais": totais, "total": len(ativas)}


def mais_atrasadas(linhas, limite=10):
    ativas = [r for r in linhas if r["ativa"] and r["atraso_nota"]]
    return sorted(ativas, key=lambda r: -r["atraso_nota"])[:limite]


def mais_paradas(linhas, limite=10):
    ativas = [r for r in linhas if r["ativa"] and r["dias_na_medida"] is not None]
    return sorted(ativas, key=lambda r: -r["dias_na_medida"])[:limite]
