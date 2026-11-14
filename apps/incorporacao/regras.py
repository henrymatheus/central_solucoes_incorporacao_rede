"""Colunas calculadas do Power BI (tabela BaseIncorporacao), traduzidas do DAX.

Fonte: modelo do arquivo "Gestão de Incorporação RD - Corporativo.pbix" (14/11/2026).
Funções puras: recebem os valores da nota e a data de referência ("hoje" = TODAY() do BI).
"""

from datetime import date

DATA_CORTE_RTP26 = date(2023, 12, 1)
DATA_CORTE_GIRO = date(2026, 1, 1)
ROTULOS_PRAZO = ("Fora prazo", "Vence Hoje", "Prestes a Vencer", "No Prazo")
ROTULOS_PRAZO_MEDIDA = (
    "Medida Fora prazo",
    "Medida Vence Hoje",
    "Medida Prestes a Vencer",
    "Medida No Prazo",
    "Medida concluída fora do prazo",
    "Medida Concluída no prazo",
)


def chave_mapeamento(medida, centro_trabalho):
    """CHAVE_MAPEAMENTO = TRIM(MEDIDA_ATUAL) & "|" & TRIM(CENTRO_TRABALHO)."""
    return f"{(medida or '').strip()}|{(centro_trabalho or '').strip()}"


def etapa_calculada(medida):
    """Coluna ETAPA da base (usada pelos cards Documentação e Etapa Cadastro)."""
    return {
        "VERDOCIN": "DOCUMENTAÇÃO",
        "CATEBDGD": "BDGD",
        "VISTOBRA": "VISTORIA",
        "VISLEMAT": "VISTORIA",
    }.get((medida or "").strip(), "")


def status_demanda(status_ccs):
    s = (status_ccs or "").strip()
    if s == "FINL":
        return "DEMANDA FINALIZADA"
    if s == "CANC":
        return "DEMANDA CANCELADA"
    return "DEMANDA ATIVA"


def status_rtp(data_criacao):
    return "RTP26" if data_criacao and data_criacao > DATA_CORTE_RTP26 else "RTP_Anterior"


def classificacao_demanda(data_criacao):
    return "GIRO" if data_criacao and data_criacao > DATA_CORTE_GIRO else "PASSIVO"


def _menos_meses(d, meses):
    total = d.year * 12 + (d.month - 1) - meses
    ano, mes = divmod(total, 12)
    mes += 1
    for dia in (d.day, 30, 29, 28):
        try:
            return date(ano, mes, dia)
        except ValueError:
            continue
    return date(ano, mes, 28)


def flag_compulsoria(data_criacao, hoje):
    """60 meses = 5 anos exatos (EDATE(TODAY(), -60))."""
    if not data_criacao:
        return "Sem data"
    return "Mais de 5 anos" if data_criacao <= _menos_meses(hoje, 60) else "Até 5 anos"


def _status_por_dias(dias):
    if dias is None:
        return ""
    if dias < 0:
        return "Fora prazo"
    if dias == 0:
        return "Vence Hoje"
    if dias <= 5:
        return "Prestes a Vencer"
    return "No Prazo"


def status_prazo_nota_ir(fim_desejado, hoje):
    """Prazo_nota_IR = FIM_DESEJADO; dias = prazo − hoje."""
    return _status_por_dias((fim_desejado - hoje).days if fim_desejado else None)


def status_prazo_nota_vinculada(inicio_avaria_vinculada, inicio_avaria, hoje):
    base = inicio_avaria_vinculada or inicio_avaria
    if not base:
        return ""
    from datetime import timedelta

    return _status_por_dias((base + timedelta(days=30) - hoje).days)


def status_prazo_medida(fim_programado, data_conclusao, hoje):
    if not fim_programado:
        return ""
    dias = (fim_programado - (data_conclusao or hoje)).days
    if data_conclusao:
        return "Medida concluída fora do prazo" if dias < 0 else "Medida Concluída no prazo"
    if dias < 0:
        return "Medida Fora prazo"
    if dias == 0:
        return "Medida Vence Hoje"
    if dias <= 5:
        return "Medida Prestes a Vencer"
    return "Medida No Prazo"


def status_documentacao(texto_medida_anterior):
    texto = texto_medida_anterior or ""
    if "Documentação Aprovada" in texto:
        return "Documentação Aprovada"
    if "Documentação Reprovada" in texto:
        return "Documentação Reprovada"
    return ""


def normalizar_gerencia_sql(valor):
    """Tratamentos do Power Query sobre a coluna GERENCIA vinda do Snowflake."""
    if valor is None:
        return "Não Mapeado"
    s = "".join(c for c in str(valor).strip() if c.isprintable())
    for de, para in (
        ("RELACIONAMENTO COM O CLIENTE", "RELACIONAMENTO"),
        ("RELACIONAMENTO ¿ APOIO", "RELACIONAMENTO"),
        ("EXPANSÃO DE REDE", "EXPANSÃO"),
        ("OPERAÇÃO SISTEMA", "OPERAÇÃO"),
    ):
        s = s.replace(de, para)
    return s
