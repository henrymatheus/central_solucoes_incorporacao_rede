from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.core.models import Distribuidora
from apps.incorporacao.models import NotaHistorico, NotaIR, OrigemGerencia, Situacao
from apps.integracao.models import (
    DeParaMedidaGerencia,
    EquivalenciaGerencia,
    ExecucaoETL,
    StatusFiscalizacao,
)
from apps.integracao.sincronizacao import ler_csv, sincronizar
from apps.integracao.snowflake import checar_leitura


def linha(nota, estado="PA", **extra):
    base = {
        "NOTA": nota, "ESTADO": estado, "TIPO_NOTA": "IR", "STATUS_CCS": "ATIV",
        "MEDIDA_ATUAL": "VERDOCIN", "CENTRO_TRABALHO": "EXPCPJCO", "REGIONAL": "NORTE",
        "DATA_CRIACAO": "2026-01-05", "VL_TOTAL_ORCAMENTO": "1000.50", "STATUS_FISCALIZACAO": None,
        "GERENCIA": "RELACIONAMENTO COM O CLIENTE",
    }  # fmt: skip
    base.update(extra)
    return base


class SincronizacaoTests(TestCase):
    def setUp(self):
        for uf in ("PA", "MA"):
            Distribuidora.objects.create(
                sigla=f"EQTL-{uf}", nome=f"Equatorial {uf}", nome_catalogo=uf, uf=uf
            )

    def test_tabelas_de_apoio_do_bi_carregadas_pela_migracao(self):
        self.assertEqual(DeParaMedidaGerencia.objects.count(), 53)
        self.assertEqual(StatusFiscalizacao.objects.count(), 7)
        self.assertTrue(DeParaMedidaGerencia.objects.filter(chave="VERDOCIN|EXPCPJCO").exists())

    def test_uma_linha_por_nota_e_tratamentos_do_power_query(self):
        execucao = sincronizar(
            [linha("1"), linha("1", STATUS_CCS="FINL"), linha("2", estado="MA")], "teste",
            data_ref=date(2026, 11, 14),
        )  # fmt: skip
        self.assertEqual(NotaIR.objects.count(), 2)
        n = NotaIR.objects.get(nota="1")
        self.assertEqual(n.status_ccs, "ATIV", "fica a primeira ocorrência, como no Table.Distinct")
        self.assertEqual(n.status_fiscalizacao, "Fora SISCO")
        self.assertEqual(n.status_sgo, "Sem Nota Proj")
        self.assertEqual(n.cliente_ligado, "NOTA NÃO MAPEADA")
        self.assertEqual(n.dados["GERENCIA"], "RELACIONAMENTO")
        self.assertEqual(n.vl_total_orcamento, Decimal("1000.50"))
        self.assertEqual(execucao.status, ExecucaoETL.Status.SUCESSO)
        self.assertEqual(execucao.registros_lidos, 3)

    def test_grava_historico_do_dia_e_substitui_mesma_data(self):
        sincronizar(
            [linha("1"), linha("2", STATUS_CCS="FINL")], "teste", data_ref=date(2026, 11, 13)
        )
        sincronizar(
            [linha("1"), linha("2", STATUS_CCS="FINL")], "teste", data_ref=date(2026, 11, 14)
        )
        sincronizar([linha("1", MEDIDA_ATUAL="VISTOBRA")], "teste", data_ref=date(2026, 11, 14))
        self.assertEqual(NotaHistorico.objects.filter(data=date(2026, 11, 13)).count(), 2)
        hoje = NotaHistorico.objects.get(data=date(2026, 11, 14))
        self.assertEqual((hoje.nota, hoje.medida, hoje.situacao), ("1", "VISTOBRA", Situacao.ATIVA))

    def test_sem_foto_nao_grava_historico(self):
        sincronizar([linha("1")], "teste", snapshot=False)
        self.assertFalse(NotaHistorico.objects.exists())

    def test_situacao_da_nota(self):
        sincronizar(
            [linha("1"), linha("2", STATUS_CCS="FINL"), linha("3", STATUS_CCS="CANC"),
             linha("4", STATUS_CCS="RECE"), linha("5", STATUS_CCS=None)], "teste",
        )  # fmt: skip
        situacoes = dict(NotaIR.objects.values_list("nota", "situacao"))
        self.assertEqual(
            situacoes,
            {"1": "ativa", "2": "finalizada", "3": "cancelada", "4": "ativa", "5": "ativa"},
        )

    def test_gerencia_depara_depois_equivalencia_depois_sql(self):
        sincronizar(
            [
                linha("1"),  # VERDOCIN|EXPCPJCO está no DE-PARA
                linha("2", estado="MA", CENTRO_TRABALHO="X1", GERENCIA="CONTROLADORIA"),
                linha("3", estado="MA", CENTRO_TRABALHO="X1", GERENCIA="OBRAS E MANUTENÇÃO"),
                linha("4", estado="MA", CENTRO_TRABALHO="X1", GERENCIA=None),
            ],
            "teste",
        )
        g = {n.nota: (n.gerencia, n.origem_gerencia) for n in NotaIR.objects.all()}
        self.assertEqual(g["1"], ("TÁTICO", OrigemGerencia.DEPARA))
        self.assertEqual(g["2"], ("ATIVOS", OrigemGerencia.EQUIVALENCIA))
        self.assertEqual(g["3"], ("OBRAS E MANUTENÇÃO", OrigemGerencia.SQL))
        self.assertEqual(g["4"], ("Não mapeada", OrigemGerencia.SQL))

    def test_editar_equivalencia_recalcula_a_carteira(self):
        sincronizar(
            [linha("3", estado="MA", CENTRO_TRABALHO="X1", GERENCIA="OBRAS E MANUTENÇÃO")], "teste"
        )
        EquivalenciaGerencia.objects.create(gerencia_sql="OBRAS E MANUTENÇÃO", gerencia="TÁTICO")
        n = NotaIR.objects.get()
        self.assertEqual((n.gerencia, n.origem_gerencia), ("TÁTICO", OrigemGerencia.EQUIVALENCIA))

    def test_falha_nao_apaga_a_base_atual(self):
        sincronizar([linha("1")], "teste")
        with self.assertRaises(ValueError):
            sincronizar([{"NOTA": ""}], "teste")
        self.assertEqual(NotaIR.objects.count(), 1)
        self.assertEqual(ExecucaoETL.objects.filter(status=ExecucaoETL.Status.ERRO).count(), 1)

    def test_csv_com_virgula_e_quebra_de_linha_em_campo(self):
        texto = 'NOTA,ESTADO,TEXTO_OBSERVACAO_MEDIDA_ANTERIOR\n1,PA,"linha 1\nlinha 2"\n2,PA,ok\n'
        self.assertEqual(len(ler_csv(texto.encode())), 2)

    def test_snowflake_bloqueia_escrita(self):
        checar_leitura("SELECT * FROM SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO")
        for sql in ("DELETE FROM t", "CREATE TABLE x AS SELECT 1", "SELECT 1; DROP TABLE t"):
            with self.subTest(sql=sql), self.assertRaises(RuntimeError):
                checar_leitura(sql)
