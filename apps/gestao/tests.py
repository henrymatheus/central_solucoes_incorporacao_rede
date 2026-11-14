from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.idempotencia import CAMPO_CHAVE, gerar_chave
from apps.core.models import Distribuidora, Perfil, Usuario
from apps.gestao import indicadores as ind
from apps.incorporacao.models import Acompanhamento, NotaHistorico, NotaIR, Situacao

HOJE = date(2026, 11, 14)


def nota(numero, estado="PA", situacao=Situacao.ATIVA, **extra):
    """Cria uma NotaIR de teste. Datas relativas a HOJE via dias_*."""
    campos = {
        "estado": estado,
        "nota": numero,
        "situacao": situacao,
        "status_ccs": {"ativa": "ATIV", "finalizada": "FINL", "cancelada": "CANC"}[situacao],
        "regional": "NORTE",
        "gerencia": "TÁTICO",
        "medida_atual": "VERDOCIN",
        "texto_breve_grupo_codigo": "Verificar documentação",
        "data_criacao": HOJE - timedelta(days=extra.pop("idade", 100)),
        "data_criacao_medida": HOJE - timedelta(days=extra.pop("na_medida", 10)),
        "fim_desejado": HOJE + timedelta(days=extra.pop("prazo", 30)),
        "fim_programado_medida": HOJE + timedelta(days=extra.pop("prazo_medida", 30)),
        "vl_total_orcamento": Decimal("1000"),
        "dados": {"NOTA": numero, "ESTADO": estado, "NOME": "Cliente teste"},
        "sincronizado_em": timezone.now(),
    }
    encerrada = extra.pop("encerrada_ha", None)
    if encerrada is not None:
        campos["data_encerramento"] = HOJE - timedelta(days=encerrada)
    campos.update(extra)
    return NotaIR.objects.create(**campos)


class FaixasTests(SimpleTestCase):
    def test_faixa_de_prazo(self):
        self.assertEqual(ind.faixa_prazo(None), "sem_prazo")
        self.assertEqual(ind.faixa_prazo(-1), "vencida")
        self.assertEqual(ind.faixa_prazo(0), "a_vencer")
        self.assertEqual(ind.faixa_prazo(7), "a_vencer")
        self.assertEqual(ind.faixa_prazo(8), "no_prazo")

    def test_faixas_de_atraso_e_idade(self):
        self.assertEqual(ind.faixa_atraso(0), "")
        self.assertEqual(ind.faixa_atraso(30), "ate30")
        self.assertEqual(ind.faixa_atraso(31), "31a90")
        self.assertEqual(ind.faixa_atraso(731), "mais2")
        self.assertEqual(ind.faixa_idade(None), "sem")
        self.assertEqual(ind.faixa_idade(365), "181a365")
        self.assertEqual(ind.faixa_idade(1827), "mais5")


class IndicadoresTests(TestCase):
    def setUp(self):
        nota("1", prazo=-40, prazo_medida=-5, na_medida=60)  # vencida há 40 d, medida vencida
        nota("2", prazo=3, idade=2)  # vence em 3 dias, entrou há 2 dias
        nota("3", estado="MA", gerencia="ATIVOS", prazo=-400)  # vencida há 400 d
        nota("4", situacao=Situacao.FINALIZADA, prazo=-10, encerrada_ha=1)
        nota("5", situacao=Situacao.CANCELADA, estado="MA", encerrada_ha=50, idade=60)
        self.linhas = ind.carregar(None, {}, HOJE)

    def test_resumo(self):
        r = ind.resumo(self.linhas, HOJE)
        self.assertEqual(r["ativas"], 3)
        self.assertEqual(r["notas_vencidas"], 2, "nota encerrada não conta como vencida")
        self.assertEqual(r["notas_a_vencer"], 1)
        self.assertEqual(r["medidas_vencidas"], 1)
        self.assertEqual(r["entrantes_periodo"], 1)
        self.assertEqual(r["encerradas_periodo"], 1, "a cancelada há 50 dias está fora dos 30")
        self.assertEqual(r["atraso_mediano"], 220)
        self.assertEqual(r["valor"], Decimal("3000"))

    def test_por_dimensao_fecha_com_o_total(self):
        grupos, total = ind.por_dimensao(self.linhas, "estado", HOJE)
        self.assertEqual([g["chave"] for g in grupos], ["PA", "MA"])
        for campo in ("ativas", "vencidas", "entrantes", "encerradas", "medidas_vencidas"):
            self.assertEqual(sum(g[campo] for g in grupos), total[campo], campo)
        pa = grupos[0]
        self.assertEqual((pa["ativas"], pa["vencidas"], pa["pct_vencidas"]), (2, 1, 50.0))
        self.assertEqual(pa["saldo"], pa["entrantes"] - pa["encerradas"])

    def test_fluxo_por_mes_e_por_dia(self):
        meses = ind.fluxo(self.linhas, "mes", HOJE)
        self.assertEqual(len(meses), 24)
        self.assertEqual(meses[-1]["rotulo"], "nov/26")
        self.assertEqual(meses[-1]["entrantes"], 1)
        self.assertEqual(meses[-1]["encerradas"], 1)
        dias = ind.fluxo(self.linhas, "dia", HOJE)
        self.assertEqual(len(dias), 60)
        self.assertEqual(dias[-1]["de"], HOJE.isoformat())
        self.assertEqual(sum(d["encerradas"] for d in dias), 2)

    def test_lista_filtra_e_ordena(self):
        lista = ind.filtrar_lista(self.linhas, {})
        self.assertEqual(
            [r["nota"] for r in lista], ["3", "1", "2"], "maior atraso primeiro; só ativas"
        )
        self.assertEqual(len(ind.filtrar_lista(self.linhas, {"situacao": "encerradas"})), 2)
        self.assertEqual(len(ind.filtrar_lista(self.linhas, {"situacao": "todas"})), 5)
        vencidas_2a = ind.filtrar_lista(
            self.linhas, {"prazo_nota": "vencida", "faixa_atraso": "181a365"}
        )
        self.assertEqual([r["nota"] for r in vencidas_2a], [])
        self.assertEqual(
            [r["nota"] for r in ind.filtrar_lista(self.linhas, {"faixa_atraso": "1a2"})], ["3"]
        )
        self.assertEqual([r["nota"] for r in ind.filtrar_lista(self.linhas, {"q": "2"})], ["2"])

    def test_matriz(self):
        m = ind.matriz(self.linhas, "gerencia", "estado")
        self.assertEqual(m["colunas"], ["MA", "PA"])
        self.assertEqual(m["total"], 3)
        self.assertEqual(sum(m["totais"]), 3)


@mock.patch("django.utils.timezone.localdate", return_value=HOJE)
class GestaoViewsTests(TestCase):
    def setUp(self):
        self.pa = Distribuidora.objects.create(
            sigla="EQTL-PA", nome="Equatorial Pará", nome_catalogo="PA", uf="PA"
        )
        Distribuidora.objects.create(
            sigla="EQTL-MA", nome="Equatorial Maranhão", nome_catalogo="MA", uf="MA"
        )
        nota("1", prazo=-40, prazo_medida=-5)
        nota("2", prazo=3, idade=2, gerencia="RELACIONAMENTO")
        nota("3", estado="MA", prazo=-400)
        nota("4", situacao=Situacao.FINALIZADA, encerrada_ha=1)
        u = Usuario.objects.create_user(username="pa", password="x")
        u.perfil.tipo = Perfil.Tipo.TATICO
        u.perfil.save()
        u.perfil.distribuidoras.add(self.pa)
        self.user = u
        self.client.force_login(u)

    def test_paginas_abrem(self, _):
        for nome in ("visao_geral", "analise", "prazos", "notas"):
            with self.subTest(pagina=nome):
                self.assertEqual(self.client.get(reverse(f"gestao:{nome}")).status_code, 200)
        r = self.client.get(
            reverse("gestao:analise"), {"nivel": "gerencia", "grao": "dia", "periodo": "90"}
        )
        self.assertEqual(r.context["nivel"], "gerencia")

    def test_escopo_por_estado(self, _):
        r = self.client.get(reverse("gestao:visao_geral"))
        self.assertEqual(r.context["r"]["ativas"], 2, "usuário do PA não vê a nota do MA")
        self.assertEqual(self.client.get(reverse("gestao:nota", args=["3"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("gestao:nota", args=["1"])).status_code, 200)

    def test_numero_clicado_abre_a_mesma_quantidade_de_notas(self, _):
        r = self.client.get(reverse("gestao:prazos"))
        for g in r.context["grupos"]:
            for url, esperado in (
                (g["url_vencidas"], g["vencidas"]),
                (g["url_notas"], g["ativas"]),
            ):
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).context["total_lista"], esperado)
        visao = self.client.get(reverse("gestao:visao_geral")).context
        lista = self.client.get(visao["links"]["notas_vencidas"]).context
        self.assertEqual(lista["total_lista"], visao["r"]["notas_vencidas"])

    def test_filtros_invalidos_sao_ignorados(self, _):
        r = self.client.get(
            reverse("gestao:notas"), {"situacao": "xyz", "criada_de": "31/02", "q": "<script>"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("situacao", r.context["f"])
        self.assertEqual(r.context["f"].get("q"), "script")

    def test_ficha_mostra_linha_do_tempo_do_historico(self, _):
        NotaHistorico.objects.create(
            data=date(2026, 11, 12), nota="1", estado="PA", medida="VERDOCIN", situacao="ativa"
        )
        NotaHistorico.objects.create(
            data=date(2026, 11, 13), nota="1", estado="PA", medida="VISTOBRA", situacao="ativa"
        )
        r = self.client.get(reverse("gestao:nota", args=["1"]))
        self.assertContains(r, "Mudou de medida")
        self.assertContains(r, "VERDOCIN → VISTOBRA")

    def test_acompanhamento_idempotente_e_validado(self, _):
        url = reverse("gestao:acompanhar", args=["1"])
        chave = gerar_chave()
        for _i in range(2):
            self.client.post(url, {"texto": "Liguei para a equipe.", CAMPO_CHAVE: chave})
        a = Acompanhamento.objects.get()
        self.assertEqual((a.nota, a.autor, a.estado), ("1", self.user, "PA"))
        self.client.post(url, {"texto": "   ", CAMPO_CHAVE: gerar_chave()})
        self.assertEqual(Acompanhamento.objects.count(), 1)
        self.assertEqual(
            self.client.post(
                reverse("gestao:acompanhar", args=["3"]), {"texto": "x", CAMPO_CHAVE: gerar_chave()}
            ).status_code,
            404,
        )
        self.assertContains(
            self.client.get(reverse("gestao:nota", args=["1"])), "Liguei para a equipe."
        )

    def test_exportar(self, _):
        r = self.client.get(reverse("gestao:exportar"), {"situacao": "todas"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])
