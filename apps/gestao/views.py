"""Gestão da carteira de notas de incorporação: Visão geral, Análise, Prazos, Notas e ficha da nota.

Todo número exibido é um link para a lista de notas que o compõe (mesmos filtros).
"""

from datetime import date
from io import BytesIO
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from apps.core.idempotencia import ChaveEnvioInvalida, EnvioDuplicado, registrar_envio
from apps.core.permissions import ufs_visiveis
from apps.core.validacao import Validador
from apps.gestao import ficha
from apps.gestao import indicadores as ind
from apps.incorporacao.models import Acompanhamento, NotaIR, OrigemGerencia
from apps.integracao.sincronizacao import ultima_sincronizacao

ESCOLHAS = {
    "situacao": ind.SITUACOES,
    "prazo_nota": ind.PRAZOS,
    "prazo_medida": ind.PRAZOS_MEDIDA,
    "faixa_atraso": ind.ATRASOS,
    "faixa_idade": ind.IDADES,
    "ordem": ind.ORDENS,
    "periodo": ind.PERIODOS,
    "grao": {"dia": "Por dia", "mes": "Por mês"},
    "nivel": ind.DIMENSOES,
}
DATAS = {
    "criada_de": "Criada a partir de",
    "criada_ate": "Criada até",
    "encerrada_de": "Encerrada a partir de",
    "encerrada_ate": "Encerrada até",
}
ROTULOS = {
    **ind.DIMENSOES,
    **DATAS,
    "situacao": "Situação",
    "prazo_nota": "Prazo da nota",
    "prazo_medida": "Prazo da medida",
    "faixa_atraso": "Atraso",
    "faixa_idade": "Idade",
    "q": "Busca",
}
# Parâmetros de visualização: não viram "chip" de filtro.
VISUALIZACAO = {"ordem", "periodo", "grao", "nivel"}
MAX_ACOMPANHAMENTO = 2000

# Cores: escalas sequenciais de um só tom (atraso em vermelho, idade em azul). Validadas com o validador
# de paleta (skill dataviz); sempre acompanhadas de rótulo.
COR_ATRASO = ["#f6c9c0", "#ec9c8b", "#de6b56", "#c4422f", "#9b2a1e", "#6b1810"]
COR_IDADE = ["#cfdcf3", "#a9c1ea", "#7fa2dd", "#5583cd", "#2f63b5", "#1a4ea3", "#0a2463", "#8b97ad"]


# --------------------------------------------------------------------------- filtros e links


def ler_filtros(get):
    f = {}
    for k in ind.DIMENSOES:
        v = (get.get(k) or "").strip()[:80]
        if v:
            f[k] = v
    for k, opcoes in ESCOLHAS.items():
        v = get.get(k)
        if v in opcoes:
            f[k] = v
    for k in DATAS:
        try:
            f[k] = date.fromisoformat((get.get(k) or "").strip())
        except ValueError:
            pass
    q = "".join(c for c in (get.get("q") or "") if c.isalnum() or c in " -.")[:40].strip()
    if q:
        f["q"] = q
    return f


def _qs(f, **novos):
    params = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in f.items()}
    for k, v in novos.items():
        if v in (None, ""):
            params.pop(k, None)
        else:
            params[k] = v.isoformat() if isinstance(v, date) else v
    return urlencode(params)


def url_notas(f, **novos):
    """Lista de notas com as dimensões atuais + filtros novos."""
    base = {k: v for k, v in f.items() if k in ind.DIMENSOES}
    return f"{reverse('gestao:notas')}?{_qs(base, **novos)}"


def _chips(f):
    chips = []
    for k, v in f.items():
        if k in VISUALIZACAO:
            continue
        if isinstance(v, date):
            valor = v.strftime("%d/%m/%Y")
        elif k in ESCOLHAS:
            valor = ESCOLHAS[k][v]
        else:
            valor = v
        chips.append(
            {"rotulo": ROTULOS.get(k, k), "valor": valor, "remover": "?" + _qs(f, **{k: None})}
        )
    return chips


def _contexto(request, pagina):
    hoje = timezone.localdate()
    ufs = ufs_visiveis(request.user)
    f = ler_filtros(request.GET)
    linhas = ind.carregar(ufs, f, hoje)
    escopo = NotaIR.objects.all() if ufs is None else NotaIR.objects.filter(estado__in=ufs)
    return {
        "pagina": pagina,
        "hoje": hoje,
        "f": f,
        "linhas": linhas,
        "opcoes": ind.opcoes(ufs),
        "dimensoes": ind.DIMENSOES,
        "chips": _chips(f),
        "ultima": ultima_sincronizacao(),
        "sem_dados": not escopo.exists(),
    }


def _anexar_links(grupos, f, dim, pagina):
    """Links de cada linha de uma tabela agrupada: detalhar (próximo nível) e notas."""
    proximo = ind.PROXIMO_NIVEL[dim]
    for g in grupos:
        filtro = {dim: g["chave"]}
        g["url_notas"] = url_notas(f, **filtro)
        g["url_vencidas"] = url_notas(f, prazo_nota="vencida", **filtro)
        g["url_a_vencer"] = url_notas(f, prazo_nota="a_vencer", **filtro)
        g["url_medidas_vencidas"] = url_notas(f, prazo_medida="vencida", **filtro)
        g["url_entrantes"] = url_notas(f, situacao="todas", criada_de=_inicio_periodo(f), **filtro)
        g["url_encerradas"] = url_notas(
            f, situacao="encerradas", encerrada_de=_inicio_periodo(f), **filtro
        )
        g["url_detalhar"] = (
            f"{reverse('gestao:' + pagina)}?{_qs(f, nivel=proximo, **filtro)}"
            if proximo
            else g["url_notas"]
        )
    return grupos


def _periodo(f):
    return int(f.get("periodo") or 30)


def _inicio_periodo(f):
    from datetime import timedelta

    return timezone.localdate() - timedelta(days=_periodo(f) - 1)


def _serie_faixas(dist, cores, f, campo, **extra):
    return [
        {**d, "cor": cores[i % len(cores)] if isinstance(cores, list) else cores.get(d["chave"], "#8b97ad"),
         "url": url_notas(f, **{campo: d["chave"]}, **extra)}
        for i, d in enumerate(dist)
    ]  # fmt: skip


def _grafico_fluxo(linhas, grao, hoje, f):
    serie = ind.fluxo(linhas, grao, hoje)
    for s in serie:
        s["url_entrantes"] = url_notas(f, situacao="todas", criada_de=s["de"], criada_ate=s["ate"])
        s["url_encerradas"] = url_notas(
            f, situacao="encerradas", encerrada_de=s["de"], encerrada_ate=s["ate"]
        )
    return {"tipo": "fluxo", "serie": serie}


# --------------------------------------------------------------------------- páginas


@login_required
def visao_geral(request):
    ctx = _contexto(request, "visao_geral")
    f, linhas, hoje = ctx["f"], ctx["linhas"], ctx["hoje"]
    r = ind.resumo(linhas, hoje, 30)
    inicio_mes = hoje.replace(day=1)
    ctx["r"] = r
    ctx["links"] = {
        "ativas": url_notas(f),
        "entrantes_hoje": url_notas(f, situacao="todas", criada_de=hoje, ordem="recentes"),
        "entrantes_7": url_notas(
            f, situacao="todas", criada_de=date.fromordinal(hoje.toordinal() - 6), ordem="recentes"
        ),
        "entrantes_mes": url_notas(f, situacao="todas", criada_de=inicio_mes, ordem="recentes"),
        "encerradas_mes": url_notas(f, situacao="encerradas", encerrada_de=inicio_mes),
        "notas_vencidas": url_notas(f, prazo_nota="vencida"),
        "notas_a_vencer": url_notas(f, prazo_nota="a_vencer"),
        "medidas_vencidas": url_notas(f, prazo_medida="vencida", ordem="parada"),
        "medidas_a_vencer": url_notas(f, prazo_medida="a_vencer"),
    }
    estados, total = ind.por_dimensao(linhas, "estado", hoje, 30)
    ctx["estados"] = _anexar_links(estados, f, "estado", "analise")
    ctx["total_estados"] = total
    gerencias, _ = ind.por_dimensao(linhas, "gerencia", hoje, 30)
    gerencias = [g for g in gerencias if g["ativas"]]
    ctx["gerencias"] = _anexar_links(
        sorted(gerencias, key=lambda g: -g["vencidas"])[:6], f, "gerencia", "analise"
    )
    medidas, _ = ind.por_dimensao(linhas, "medida", hoje, 30)
    gargalos = [m for m in medidas if m["ativas"] >= 5]
    ctx["gargalos"] = _anexar_links(
        sorted(gargalos, key=lambda m: -(m["parada_media"] or 0))[:6], f, "medida", "analise"
    )
    ctx["atrasadas"] = ind.mais_atrasadas(linhas, 8)
    ctx["sem_equivalencia"] = sum(
        1 for x in linhas if x["ativa"] and x["obj"].origem_gerencia == OrigemGerencia.SQL
    )
    ctx["graficos"] = {"fluxo": _grafico_fluxo(linhas, "dia", hoje, f)}
    ctx["url_todas_atrasadas"] = url_notas(f, prazo_nota="vencida")
    return render(request, "gestao/visao_geral.html", ctx)


@login_required
def analise(request):
    ctx = _contexto(request, "analise")
    f, linhas, hoje = ctx["f"], ctx["linhas"], ctx["hoje"]
    nivel = f.get("nivel") or next((d for d in ind.DIMENSOES if d not in f), "medida")
    periodo = _periodo(f)
    grao = f.get("grao") or "mes"
    grupos, total = ind.por_dimensao(linhas, nivel, hoje, periodo)
    ctx.update(
        nivel=nivel,
        nivel_rotulo=ind.DIMENSOES[nivel],
        periodo=str(periodo),
        periodos=ind.PERIODOS,
        grao=grao,
        grupos=_anexar_links(grupos, f, nivel, "analise"),
        total=total,
        r=ind.resumo(linhas, hoje, periodo),
        links_nivel={d: "?" + _qs(f, nivel=d) for d in ind.DIMENSOES},
        links_periodo={p: "?" + _qs(f, periodo=p) for p in ind.PERIODOS},
        links_grao={g: "?" + _qs(f, grao=g) for g in ("dia", "mes")},
    )
    mtz = ind.matriz(linhas, "gerencia", "estado")
    for lin in mtz["linhas"]:
        lin["url"] = url_notas(f, gerencia=lin["chave"])
        for c in lin["celulas"]:
            c["url"] = url_notas(f, gerencia=lin["chave"], estado=c["coluna"])
    ctx["matriz"] = mtz
    ctx["graficos"] = {
        "fluxo": _grafico_fluxo(linhas, grao, hoje, f),
        "idade": {"tipo": "barras", "serie": _serie_faixas(ind.distribuicao(linhas, "faixa_idade", ind.IDADES), COR_IDADE, f, "faixa_idade")},
    }  # fmt: skip
    return render(request, "gestao/analise.html", ctx)


@login_required
def prazos(request):
    ctx = _contexto(request, "prazos")
    f, linhas, hoje = ctx["f"], ctx["linhas"], ctx["hoje"]
    nivel = f.get("nivel") or "gerencia"
    grupos, total = ind.por_dimensao(linhas, nivel, hoje)
    grupos = [g for g in grupos if g["ativas"]]
    medidas, _ = ind.por_dimensao(linhas, "medida", hoje)
    medidas = [m for m in medidas if m["ativas"]]
    ctx.update(
        r=ind.resumo(linhas, hoje),
        nivel=nivel,
        nivel_rotulo=ind.DIMENSOES[nivel],
        links_nivel={d: "?" + _qs(f, nivel=d) for d in ind.DIMENSOES},
        grupos=_anexar_links(sorted(grupos, key=lambda g: (-g["vencidas"], -g["ativas"])), f, nivel, "prazos"),
        total=total,
        gargalos=_anexar_links(sorted(medidas, key=lambda m: (-m["medidas_vencidas"], -(m["parada_media"] or 0)))[:12], f, "medida", "prazos"),
        atrasadas=ind.mais_atrasadas(linhas, 15),
        url_todas_atrasadas=url_notas(f, prazo_nota="vencida"),
        links={
            "notas_vencidas": url_notas(f, prazo_nota="vencida"),
            "notas_a_vencer": url_notas(f, prazo_nota="a_vencer"),
            "notas_no_prazo": url_notas(f, prazo_nota="no_prazo"),
            "medidas_vencidas": url_notas(f, prazo_medida="vencida", ordem="parada"),
            "medidas_a_vencer": url_notas(f, prazo_medida="a_vencer"),
            "medidas_no_prazo": url_notas(f, prazo_medida="no_prazo"),
        },
    )  # fmt: skip
    ctx["graficos"] = {
        "atraso": {"tipo": "barras", "serie": _serie_faixas(ind.distribuicao(linhas, "faixa_atraso", ind.ATRASOS), COR_ATRASO, f, "faixa_atraso", prazo_nota="vencida")},
    }  # fmt: skip
    return render(request, "gestao/prazos.html", ctx)


@login_required
def notas(request):
    ctx = _contexto(request, "notas")
    f = ctx["f"]
    lista = ind.filtrar_lista(ctx["linhas"], f)
    pagina = Paginator(lista, 50).get_page(request.GET.get("page"))
    ctx.update(
        lista=pagina,
        total_lista=len(lista),
        situacoes=ind.SITUACOES,
        prazos=ind.PRAZOS,
        prazos_medida=ind.PRAZOS_MEDIDA,
        atrasos=ind.ATRASOS,
        idades=ind.IDADES,
        ordens=ind.ORDENS,
        qs_sem_pagina=_qs(f),
        url_exportar=f"{reverse('gestao:exportar')}?{_qs(f)}",
    )
    return render(request, "gestao/notas.html", ctx)


def _nota_visivel(request, numero):
    n = NotaIR.objects.filter(nota=numero).first()
    ufs = ufs_visiveis(request.user)
    if not n or (ufs is not None and n.estado not in ufs):
        raise Http404("Nota não encontrada.")
    return n


@login_required
def nota(request, numero):
    n = _nota_visivel(request, numero)
    hoje = timezone.localdate()
    eventos, dias_historico = ficha.linha_do_tempo(n)
    return render(
        request,
        "gestao/nota.html",
        {
            "pagina": "notas",
            "n": n,
            "r": ind.linha(n, hoje),
            "rotulos_prazo": ind.PRAZOS,
            "rotulos_prazo_medida": ind.PRAZOS_MEDIDA,
            "secoes": ficha.secoes(n.dados),
            "eventos": eventos,
            "dias_historico": dias_historico,
            "acompanhamentos": Acompanhamento.objects.filter(nota=n.nota).select_related("autor"),
            "todos_campos": sorted(n.dados.items()),
            "max_acompanhamento": MAX_ACOMPANHAMENTO,
            "voltar": request.META.get("HTTP_REFERER", "")
            if "/notas/" in request.META.get("HTTP_REFERER", "")
            else "",
        },
    )


@login_required
@require_POST
def acompanhar(request, numero):
    n = _nota_visivel(request, numero)
    destino = reverse("gestao:nota", args=[n.nota]) + "#acompanhamento"
    v = Validador(request.POST)
    texto = v.texto("texto", "Registro", obrigatorio=True, max_len=MAX_ACOMPANHAMENTO)
    if v.erros:
        for erro in v.erros:
            messages.error(request, erro)
        return redirect(destino)
    try:
        with transaction.atomic():
            envio = registrar_envio(request)
            Acompanhamento.objects.create(
                nota=n.nota, estado=n.estado, texto=texto, autor=request.user
            )
            envio.concluir(destino)
    except EnvioDuplicado as dup:
        messages.info(request, str(dup))
        return redirect(dup.resultado_url or destino)
    except ChaveEnvioInvalida as exc:
        messages.error(request, str(exc))
        return redirect(destino)
    messages.success(request, "Registro adicionado.")
    return redirect(destino)


COLUNAS_EXPORTACAO = [
    ("nota", "NOTA"), ("estado", "ESTADO"), ("regional", "REGIONAL"), ("gerencia", "GERENCIA (sistema)"),
    ("situacao", "SITUACAO"), ("medida", "MEDIDA_ATUAL"), ("medida_texto", "DESCRICAO_MEDIDA"),
    ("prazo_nota", "PRAZO_NOTA"), ("dias_nota", "DIAS_PARA_FIM_DESEJADO"), ("prazo_medida", "PRAZO_MEDIDA"),
    ("dias_medida", "DIAS_PARA_FIM_PROGRAMADO_MEDIDA"), ("dias_na_medida", "DIAS_NA_MEDIDA_ATUAL"),
    ("idade", "IDADE_DIAS"), ("valor", "VL_TOTAL_ORCAMENTO"),
]  # fmt: skip


@login_required
def exportar(request):
    ctx = _contexto(request, "notas")
    lista = ind.filtrar_lista(ctx["linhas"], ctx["f"])
    wb = Workbook()
    ws = wb.active
    ws.title = "Notas"
    origem = list(lista[0]["obj"].dados.keys()) if lista else []
    origem = [
        c
        for c in origem
        if c not in {"NOTA", "ESTADO", "REGIONAL", "MEDIDA_ATUAL", "VL_TOTAL_ORCAMENTO"}
    ]
    ws.append([rotulo for _, rotulo in COLUNAS_EXPORTACAO] + origem)
    rotulos = {**ind.PRAZOS_MEDIDA, "": ""}
    for r in lista:
        valores = []
        for chave, _ in COLUNAS_EXPORTACAO:
            v = r[chave]
            if chave in ("prazo_nota", "prazo_medida"):
                v = rotulos.get(v, v)
            elif chave == "valor":
                v = float(v)
            elif chave == "situacao":
                v = r["obj"].get_situacao_display()
            valores.append(v)
        ws.append(valores + [r["obj"].dados.get(c, "") for c in origem])
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "B2"
    for i in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = 18
    saida = BytesIO()
    wb.save(saida)
    resposta = HttpResponse(
        saida.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resposta["Content-Disposition"] = (
        f'attachment; filename="notas-incorporacao-{ctx["hoje"]:%Y%m%d}.xlsx"'
    )
    return resposta
