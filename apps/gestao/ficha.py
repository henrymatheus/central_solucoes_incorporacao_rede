"""Ficha da nota: seções de dados e linha do tempo (datas da origem + histórico diário)."""

from apps.incorporacao.models import NotaHistorico, Situacao

SECOES = [
    ("Identificação", [
        ("NOTA", "Nota"), ("TIPO_NOTA", "Tipo"), ("STATUS_CCS", "Status CCS"), ("CODIFICACAO", "Codificação"),
        ("GRUPO_CODES", "Grupo de códigos"), ("TEXTO_BREVE", "Texto breve"), ("CARTEIRA_CLIENTE", "Carteira"),
        ("CENTRO_TRABALHO", "Centro de trabalho"), ("AREA_ESTRUT_REGIONAL", "Área estrutural"),
        ("DATA_CRIACAO", "Criada em"), ("INICIO_DESEJADO", "Início desejado"), ("FIM_DESEJADO", "Fim desejado"),
        ("DATA_ALTERACAO", "Última alteração"), ("DATA_ENCERRAMENTO_NOTA", "Encerrada em"),
    ]),
    ("Medidas", [
        ("MEDIDA_ATUAL", "Medida atual"), ("CODIGO_MEDIDA_ATUAL", "Código"), ("TEXTO_MEDIDA_ATUAL", "Situação da medida"),
        ("TEXTO_BREVE_GRUPO_CODIGO", "Descrição"), ("DATA_CRIACAO_MEDIDA", "Aberta em"),
        ("INICIO_PROGRAMADO_MEDIDA", "Início programado"), ("FIM_PROGRAMADO_MEDIDA", "Fim programado"),
        ("DATA_CONCLUSAO_MEDIDA", "Concluída em"), ("CONCLUIDO_POR", "Concluída por"),
        ("MEDIDA_ANTERIOR", "Medida anterior"), ("CODIGO_MEDIDA_ANTERIOR", "Código anterior"),
        ("TEXTO_MEDIDA_ANTERIOR", "Situação da anterior"),
    ]),
    ("Projeto e orçamento", [
        ("NOTA_PROJ", "Nota PROJ"), ("STATUS_SGO", "Status SGO"), ("STATUS_SAP", "Status SAP"),
        ("STATUS_PROJ", "Status PROJ"), ("PEP", "PEP"), ("PEP_I", "PEP (I)"), ("SLI_DESC_OBRA", "Descrição da obra"),
        ("SLI_SOLICITANTE", "Solicitante"), ("VL_MATERIAL_TOTAL", "Material (R$)"), ("VL_MO_TOTAL", "Mão de obra (R$)"),
        ("VL_TOTAL_ORCAMENTO", "Total do orçamento (R$)"),
    ]),
    ("Ligação e notas vinculadas", [
        ("CLIENTE_LIGADO", "Cliente ligado"), ("DATA_LIGACAO", "Data da ligação"),
        ("CLIENTE_LIGADO_NOTA_IR", "Ligação na própria nota IR"), ("DATA_ENERGIZACAO_NOTA_IR", "Energização da nota IR"),
        ("NOTA_OC_VINCULADA", "Nota OC/LN principal"), ("STATUS_CCS_NOTA_OC", "Status da OC/LN"),
        ("INICIO_AVARIA_NOTA_VINCULADA", "Início avaria (vinculada)"), ("QTD_NOTAS_VINCULADAS", "Notas vinculadas"),
        ("QTD_NOTAS_VINCULADAS_LIGADAS", "Vinculadas ligadas"), ("NOTAS_VINCULADAS", "Lista de vinculadas"),
        ("PRAZO_ANEXOIV", "Prazo Anexo IV"), ("MULTA", "Multa (R$)"),
    ]),
    ("Fiscalização", [
        ("STATUS_FISCALIZACAO", "Status SISCO"), ("DATA_SOLICITACAO", "Solicitada em"),
        ("DATA_AGENDAMENTO", "Agendamento"), ("DATA_ATRIBUICAO_FISCAL", "Atribuição ao fiscal"),
        ("DATA_DA_FISCALIZACAO", "Fiscalização"), ("DATA_PREVISAO_ENTREGA", "Previsão de entrega"),
        ("DATA_ENTREGA_RELATORIO_CAMPO", "Entrega do relatório"), ("DATA_DEVOLUCAO", "Devolução"),
        ("DATA_CONCLUSAO", "Conclusão"), ("DURACAO_DIAS", "Duração (dias)"),
    ]),
    ("Demanda interna", [
        ("STATUS_DEMANDA_INTERNA", "Status"), ("DATA_ABERTURA_DEMANDA_INTERNA", "Aberta em"),
        ("NOME_SOLICITANTE_DEMANDA_INTERNA", "Solicitante"), ("DESCRICAO_SOLICITACAO_DEMANDA_INTERNA", "Descrição"),
    ]),
    ("Cliente e local", [
        ("NOME", "Nome"), ("INSTALACAO", "Instalação"), ("CONTA_CONTRATO", "Conta contrato"),
        ("ENDERECO", "Endereço"), ("BAIRRO", "Bairro"), ("MUNICIPIO", "Município"), ("REGIONAL", "Regional"),
        ("PERIMETRO", "Perímetro"), ("LATITUDE", "Latitude"), ("LONGITUDE", "Longitude"),
    ]),
]  # fmt: skip

CAMPOS_DATA_HORA = {
    "INICIO_DESEJADO", "FIM_DESEJADO", "DATA_ALTERACAO", "DATA_ENCERRAMENTO_NOTA", "DATA_CRIACAO",
    "DATA_CRIACAO_MEDIDA", "INICIO_PROGRAMADO_MEDIDA", "FIM_PROGRAMADO_MEDIDA", "DATA_CONCLUSAO_MEDIDA",
    "DATA_ENERGIZACAO_NOTA_IR", "INICIO_AVARIA_NOTA_VINCULADA", "DATA_SOLICITACAO", "DATA_AGENDAMENTO",
    "DATA_ATRIBUICAO_FISCAL", "DATA_DA_FISCALIZACAO", "DATA_PREVISAO_ENTREGA", "DATA_ENTREGA_RELATORIO_CAMPO",
    "DATA_DEVOLUCAO", "DATA_ABERTURA_DEMANDA_INTERNA",
}  # fmt: skip


def _formatar(chave, valor):
    if not valor:
        return ""
    if chave in CAMPOS_DATA_HORA and len(valor) >= 10 and valor[4] == "-":
        return f"{valor[8:10]}/{valor[5:7]}/{valor[:4]}"
    return valor


def secoes(dados):
    """Seções com os campos preenchidos (campos vazios ficam de fora)."""
    saida = []
    for titulo, campos in SECOES:
        itens = [(rotulo, _formatar(k, dados.get(k, ""))) for k, rotulo in campos]
        itens = [(r, v) for r, v in itens if v]
        if itens:
            saida.append({"titulo": titulo, "itens": itens})
    return saida


def linha_do_tempo(n):
    """Eventos da nota, do mais recente ao mais antigo."""
    eventos = []
    if n.data_criacao:
        eventos.append(
            (n.data_criacao, 0, "Nota criada", f"Centro de trabalho {n.centro_trabalho or '—'}")
        )
    historico = list(NotaHistorico.objects.filter(nota=n.nota).order_by("data"))
    anterior = None
    for h in historico:
        if anterior is None:
            eventos.append(
                (
                    h.data,
                    1,
                    "Primeira foto no sistema",
                    f"Medida {h.medida or '—'} · {h.gerencia or '—'}",
                )
            )
        else:
            if h.medida != anterior.medida:
                eventos.append(
                    (h.data, 3, "Mudou de medida", f"{anterior.medida or '—'} → {h.medida or '—'}")
                )
            if h.gerencia != anterior.gerencia:
                eventos.append(
                    (
                        h.data,
                        3,
                        "Mudou de gerência",
                        f"{anterior.gerencia or '—'} → {h.gerencia or '—'}",
                    )
                )
            if h.situacao != anterior.situacao:
                eventos.append(
                    (
                        h.data,
                        4,
                        "Mudou de situação",
                        f"{anterior.get_situacao_display()} → {h.get_situacao_display()}",
                    )
                )
        anterior = h
    if n.data_criacao_medida:
        eventos.append(
            (
                n.data_criacao_medida,
                2,
                f"Medida {n.medida_atual or 'atual'} aberta",
                n.texto_breve_grupo_codigo,
            )
        )
    if n.data_conclusao_medida:
        eventos.append((n.data_conclusao_medida, 2, f"Medida {n.medida_atual} concluída", ""))
    if n.data_encerramento and n.situacao != Situacao.ATIVA:
        eventos.append((n.data_encerramento, 5, f"Nota {n.get_situacao_display().lower()}", ""))
    eventos.sort(key=lambda e: (e[0], e[1]), reverse=True)
    return [{"data": d, "titulo": t, "detalhe": det} for d, _, t, det in eventos], len(historico)
