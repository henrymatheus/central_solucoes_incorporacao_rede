from datetime import date

from django.test import SimpleTestCase

from apps.incorporacao import regras


class RegrasDoBITests(SimpleTestCase):
    """Colunas calculadas do Power BI traduzidas para Python."""

    hoje = date(2026, 11, 14)

    def test_chave_mapeamento_apara_espacos(self):
        self.assertEqual(regras.chave_mapeamento(" VERDOCIN ", "EXPCPJCO "), "VERDOCIN|EXPCPJCO")
        self.assertEqual(regras.chave_mapeamento("VERDOCIN", None), "VERDOCIN|")

    def test_etapa_calculada_so_cobre_quatro_medidas(self):
        self.assertEqual(regras.etapa_calculada("VERDOCIN"), "DOCUMENTAÇÃO")
        self.assertEqual(regras.etapa_calculada("CATEBDGD"), "BDGD")
        self.assertEqual(regras.etapa_calculada("VISLEMAT"), "VISTORIA")
        self.assertEqual(regras.etapa_calculada("ARQUPROC"), "")

    def test_status_demanda(self):
        self.assertEqual(regras.status_demanda("FINL"), "DEMANDA FINALIZADA")
        self.assertEqual(regras.status_demanda("CANC"), "DEMANDA CANCELADA")
        for v in ("ATIV", "RECE", None, ""):
            self.assertEqual(regras.status_demanda(v), "DEMANDA ATIVA")

    def test_cortes_rtp_e_giro(self):
        self.assertEqual(regras.status_rtp(date(2023, 12, 1)), "RTP_Anterior")
        self.assertEqual(regras.status_rtp(date(2023, 12, 2)), "RTP26")
        self.assertEqual(regras.status_rtp(None), "RTP_Anterior")
        self.assertEqual(regras.classificacao_demanda(date(2026, 1, 2)), "GIRO")
        self.assertEqual(regras.classificacao_demanda(date(2026, 1, 1)), "PASSIVO")

    def test_flag_compulsoria_usa_60_meses_exatos(self):
        self.assertEqual(regras.flag_compulsoria(date(2021, 11, 14), self.hoje), "Mais de 5 anos")
        self.assertEqual(regras.flag_compulsoria(date(2021, 11, 15), self.hoje), "Até 5 anos")
        self.assertEqual(regras.flag_compulsoria(None, self.hoje), "Sem data")

    def test_status_prazo_nota_ir(self):
        casos = {
            date(2026, 11, 13): "Fora prazo",
            date(2026, 11, 14): "Vence Hoje",
            date(2026, 11, 19): "Prestes a Vencer",
            date(2026, 11, 20): "No Prazo",
            None: "",
        }
        for fim, esperado in casos.items():
            with self.subTest(fim=fim):
                self.assertEqual(regras.status_prazo_nota_ir(fim, self.hoje), esperado)

    def test_status_prazo_medida(self):
        self.assertEqual(
            regras.status_prazo_medida(date(2026, 11, 10), date(2026, 11, 12), self.hoje),
            "Medida concluída fora do prazo",
        )
        self.assertEqual(
            regras.status_prazo_medida(date(2026, 11, 20), date(2026, 11, 12), self.hoje),
            "Medida Concluída no prazo",
        )
        self.assertEqual(
            regras.status_prazo_medida(date(2026, 11, 13), None, self.hoje), "Medida Fora prazo"
        )
        self.assertEqual(regras.status_prazo_medida(None, None, self.hoje), "")

    def test_prazo_nota_vinculada_soma_30_dias(self):
        self.assertEqual(
            regras.status_prazo_nota_vinculada(None, date(2026, 10, 14), self.hoje), "Fora prazo"
        )
        self.assertEqual(
            regras.status_prazo_nota_vinculada(date(2026, 11, 1), date(2020, 1, 1), self.hoje),
            "No Prazo",
        )

    def test_normalizacao_da_gerencia_do_power_query(self):
        self.assertEqual(regras.normalizar_gerencia_sql(None), "Não Mapeado")
        self.assertEqual(
            regras.normalizar_gerencia_sql("  RELACIONAMENTO COM O CLIENTE "), "RELACIONAMENTO"
        )
        self.assertEqual(regras.normalizar_gerencia_sql("EXPANSÃO DE REDE"), "EXPANSÃO")
