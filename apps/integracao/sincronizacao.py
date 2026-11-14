"""Sincronização da carteira de notas IR (TB_NOTAS_IR_CORPORATIVO) com o banco do sistema.

Aplica os tratamentos do Power Query do BI, resolve a gerência (apps/integracao/gerencia.py),
deixa UMA linha por NOTA (fica a primeira ocorrência, como o Table.Distinct do BI — a tabela
de origem repete notas, ver docs/MAPEAMENTO_SNOWFLAKE.md §5) e grava a foto do dia no histórico.
"""

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

from django.db import transaction
from django.utils import timezone

from apps.incorporacao import regras
from apps.incorporacao.models import NotaHistorico, NotaIR, Situacao
from apps.integracao.gerencia import resolvedor
from apps.integracao.models import ExecucaoETL

JOB = "sincronizar_notas_ir"


def _texto(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.isoformat(sep=" ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _data(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def _decimal(v):
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v).replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _float(v):
    d = _decimal(v)
    return float(d) if d is not None else None


def _inteiro(v):
    d = _decimal(v)
    return int(d) if d is not None else 0


def _limpar(linha):
    """Chaves em maiúsculas (padrão do Snowflake) e tratamentos de nulos do Power Query."""
    r = {str(k).strip().upper(): v for k, v in linha.items()}
    for k, v in list(r.items()):
        if isinstance(v, str) and v.strip() == "":
            r[k] = None
    r["GERENCIA"] = regras.normalizar_gerencia_sql(r.get("GERENCIA"))
    r["STATUS_FISCALIZACAO"] = r.get("STATUS_FISCALIZACAO") or "Fora SISCO"
    r["STATUS_SGO"] = r.get("STATUS_SGO") or "Sem Nota Proj"
    r["STATUS_SAP"] = r.get("STATUS_SAP") or "Projeto Não Elaborado"
    r["CLIENTE_LIGADO"] = r.get("CLIENTE_LIGADO") or "NOTA NÃO MAPEADA"
    return r


def situacao(status_ccs):
    """FINL = finalizada, CANC = cancelada; qualquer outro status (ATIV, RECE, vazio) = ativa."""
    s = (status_ccs or "").strip()
    if s == "FINL":
        return Situacao.FINALIZADA
    if s == "CANC":
        return Situacao.CANCELADA
    return Situacao.ATIVA


def montar_notas(linhas, agora):
    """Recebe dicts da fonte e devolve (lista de NotaIR, linhas_lidas)."""
    resolver = resolvedor()
    vistos = {}
    lidas = 0
    for bruta in linhas:
        lidas += 1
        r = _limpar(bruta)
        nota = _texto(r.get("NOTA"))
        if not nota or nota in vistos:
            continue
        gerencia, etapa, origem = resolver(
            r.get("MEDIDA_ATUAL"), r.get("CENTRO_TRABALHO"), r.get("GERENCIA")
        )
        vistos[nota] = NotaIR(
            estado=_texto(r.get("ESTADO"))[:2],
            nota=nota[:20],
            tipo_nota=_texto(r.get("TIPO_NOTA"))[:5],
            status_ccs=_texto(r.get("STATUS_CCS"))[:10],
            situacao=situacao(r.get("STATUS_CCS")),
            gerencia=gerencia[:60],
            origem_gerencia=origem,
            etapa=(etapa or "")[:40],
            nota_proj=_texto(r.get("NOTA_PROJ"))[:20],
            pep=_texto(r.get("PEP"))[:60],
            pep_i=_texto(r.get("PEP_I"))[:300],
            medida_atual=_texto(r.get("MEDIDA_ATUAL"))[:20],
            texto_medida_atual=_texto(r.get("TEXTO_MEDIDA_ATUAL"))[:200],
            medida_anterior=_texto(r.get("MEDIDA_ANTERIOR"))[:20],
            texto_breve_grupo_codigo=_texto(r.get("TEXTO_BREVE_GRUPO_CODIGO"))[:160],
            centro_trabalho=_texto(r.get("CENTRO_TRABALHO"))[:20],
            regional=_texto(r.get("REGIONAL"))[:60],
            municipio=_texto(r.get("MUNICIPIO"))[:120],
            carteira_cliente=_texto(r.get("CARTEIRA_CLIENTE"))[:80],
            status_fiscalizacao=_texto(r.get("STATUS_FISCALIZACAO"))[:160],
            status_sgo=_texto(r.get("STATUS_SGO"))[:80],
            cliente_ligado=_texto(r.get("CLIENTE_LIGADO"))[:40],
            data_criacao=_data(r.get("DATA_CRIACAO")),
            data_encerramento=_data(r.get("DATA_ENCERRAMENTO_NOTA")),
            fim_desejado=_data(r.get("FIM_DESEJADO")),
            inicio_avaria=_data(r.get("INICIO_AVARIA")),
            inicio_avaria_nota_vinculada=_data(r.get("INICIO_AVARIA_NOTA_VINCULADA")),
            data_criacao_medida=_data(r.get("DATA_CRIACAO_MEDIDA")),
            fim_programado_medida=_data(r.get("FIM_PROGRAMADO_MEDIDA")),
            data_conclusao_medida=_data(r.get("DATA_CONCLUSAO_MEDIDA")),
            vl_total_orcamento=_decimal(r.get("VL_TOTAL_ORCAMENTO")),
            multa=_float(r.get("MULTA")),
            qtd_clientes_ligados=_inteiro(r.get("QTD_CLIENTES_LIGADOS")),
            dados={k: _texto(v) for k, v in r.items()},
            sincronizado_em=agora,
        )
    return list(vistos.values()), lidas


def ler_csv(conteudo):
    """CSV exportado do BI/Snowflake (separador , ou ;)."""
    texto = conteudo.decode("utf-8-sig") if isinstance(conteudo, bytes) else conteudo
    cabecalho = texto.split("\n", 1)[0]
    separador = max((",", ";", "\t"), key=cabecalho.count)
    return list(csv.DictReader(StringIO(texto), delimiter=separador))


def gravar_historico(notas, data_ref):
    """Foto do dia de cada nota (substitui a mesma data, se já existir)."""
    NotaHistorico.objects.filter(data=data_ref).delete()
    NotaHistorico.objects.bulk_create(
        [
            NotaHistorico(
                data=data_ref,
                nota=n.nota,
                estado=n.estado,
                regional=n.regional,
                gerencia=n.gerencia,
                medida=n.medida_atual,
                situacao=n.situacao,
                fim_programado_medida=n.fim_programado_medida,
            )
            for n in notas
        ],
        batch_size=2000,
    )


def sincronizar(linhas, fonte, snapshot=True, usuario=None, data_ref=None):
    """Substitui a carteira e (opcional) grava a foto do dia no histórico. Retorna a ExecucaoETL."""
    execucao = ExecucaoETL.objects.create(job=JOB, mensagem=f"Fonte: {fonte}")
    agora = timezone.now()
    data_ref = data_ref or timezone.localdate()
    try:
        notas, lidas = montar_notas(linhas, agora)
        if not notas:
            raise ValueError("A fonte não trouxe nenhuma nota.")
        with transaction.atomic():
            NotaIR.objects.all().delete()
            NotaIR.objects.bulk_create(notas, batch_size=1000)
            if snapshot:
                gravar_historico(notas, data_ref)
        execucao.status = ExecucaoETL.Status.SUCESSO
        execucao.registros_lidos = lidas
        execucao.mensagem = (
            f"Fonte: {fonte}. {lidas} linhas lidas, {len(notas)} notas distintas "
            f"({lidas - len(notas)} linhas repetidas descartadas). "
            + (f"Histórico do dia {data_ref:%d/%m/%Y} gravado." if snapshot else "")
        )
    except Exception as exc:
        execucao.status = ExecucaoETL.Status.ERRO
        execucao.mensagem = f"Fonte: {fonte}. Erro: {exc}"
        execucao.finalizado_em = timezone.now()
        execucao.save()
        raise
    execucao.finalizado_em = timezone.now()
    execucao.save()
    return execucao


def ultima_sincronizacao():
    return (
        ExecucaoETL.objects.filter(job=JOB, status=ExecucaoETL.Status.SUCESSO)
        .order_by("-finalizado_em")
        .first()
    )
