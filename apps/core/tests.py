from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.core.idempotencia import (
    CAMPO_CHAVE,
    ChaveEnvioInvalida,
    EnvioDuplicado,
    gerar_chave,
    registrar_envio,
)
from apps.core.models import EnvioFormulario, Usuario
from apps.core.validacao import Validador, id_numerico

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


@override_settings(LOGIN_MAX_TENTATIVAS=5, LOGIN_BLOQUEIO_SEGUNDOS=1800)
class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = Usuario.objects.create_user(username="analista", password="senha-forte-123")
        self.url = reverse("login")

    def _login(self, senha, **extra):
        dados = {"username": "  analista  ", "password": senha}
        dados.update(extra.pop("dados", {}))
        return self.client.post(self.url, dados, **extra)

    def test_login_assincrono_devolve_um_unico_redirecionamento(self):
        response = self._login("senha-forte-123", **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"redirect": reverse("gestao:visao_geral")})
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_remove_espacos_do_usuario(self):
        response = self._login("senha-forte-123")
        self.assertRedirects(response, reverse("gestao:visao_geral"), fetch_redirect_response=False)

    def test_next_externo_e_ignorado(self):
        response = self._login(
            "senha-forte-123", dados={"next": "https://malicioso.example/"}, **AJAX
        )
        self.assertEqual(response.json()["redirect"], reverse("gestao:visao_geral"))

    def test_next_interno_e_preservado(self):
        response = self._login("senha-forte-123", dados={"next": "/prazos/"}, **AJAX)
        self.assertEqual(response.json()["redirect"], "/prazos/")

    def test_erro_de_login_gera_mensagem_unica_e_generica(self):
        response = self._login("errada", **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Usuário ou senha incorretos."})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_campos_vazios_nao_autenticam(self):
        response = self.client.post(self.url, {"username": "   ", "password": ""}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Informe usuário e senha.")

    def test_bloqueia_apos_cinco_falhas_mesmo_com_senha_correta(self):
        for _ in range(5):
            self.assertEqual(self._login("errada", **AJAX).status_code, 400)
        response = self._login("senha-forte-123", **AJAX)
        self.assertEqual(response.status_code, 429)
        self.assertIn("bloqueado temporariamente", response.json()["error"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sucesso_zera_contador_de_falhas(self):
        for _ in range(4):
            self._login("errada", **AJAX)
        self.assertEqual(self._login("senha-forte-123", **AJAX).status_code, 200)
        self.client.logout()
        for _ in range(4):
            self._login("errada", **AJAX)
        self.assertEqual(self._login("senha-forte-123", **AJAX).status_code, 200)

    def test_login_sem_javascript_continua_funcionando(self):
        response = self._login("errada")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuário ou senha incorretos.", count=1)

    def test_pagina_de_login_tem_trava_de_envio_e_nao_cita_escola(self):
        response = self.client.get(self.url)
        self.assertContains(response, "data-async-login")
        self.assertContains(response, "js/app.js")
        self.assertNotContains(response, "Escola de Eletricistas")


class LogoutTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(username="analista", password="senha-forte-123")
        self.client.force_login(self.user)

    def test_logout_por_get_nao_e_permitido(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_por_post_encerra_sessao(self):
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class IdempotenciaTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = Usuario.objects.create_user(username="analista", password="x")

    def _request(self, chave):
        request = self.factory.post("/", {CAMPO_CHAVE: chave})
        request.user = self.user
        return request

    def test_mesma_chave_duas_vezes_e_duplicada(self):
        chave = gerar_chave()
        envio = registrar_envio(self._request(chave))
        envio.concluir("/destino/")
        with self.assertRaises(EnvioDuplicado) as ctx:
            registrar_envio(self._request(chave))
        self.assertEqual(ctx.exception.resultado_url, "/destino/")
        self.assertEqual(EnvioFormulario.objects.count(), 1)

    def test_chave_ausente_ou_malformada_e_rejeitada(self):
        for chave in ["", "curta", "<script>alert(1)</script>xxxxxxxx"]:
            with self.subTest(chave=chave), self.assertRaises(ChaveEnvioInvalida):
                registrar_envio(self._request(chave))


class ValidadorTests(TestCase):
    def test_decimal_rejeita_valores_invalidos_com_mensagem_amigavel(self):
        casos = ["abc", "NaN", "Infinity", "-1", "1.23456", "123456789012345"]
        for bruto in casos:
            with self.subTest(bruto=bruto):
                v = Validador({"valor": bruto})
                v.decimal("valor", "Valor", max_digits=12, casas=4)
                with self.assertRaises(ValidationError) as ctx:
                    v.verificar()
                mensagem = " ".join(ctx.exception.messages)
                self.assertTrue(mensagem.startswith("Valor:"))
                self.assertNotIn("decimal", mensagem.lower())

    def test_decimal_aceita_virgula_e_vazio_usa_padrao(self):
        v = Validador({"a": "10,5", "b": ""})
        self.assertEqual(v.decimal("a", "A", max_digits=12, casas=2), Decimal("10.5"))
        self.assertEqual(v.decimal("b", "B", max_digits=12, casas=2), Decimal("0"))
        v.verificar()

    def test_id_numerico(self):
        self.assertEqual(id_numerico("12"), 12)
        for valor in ["", "abc", "-1", "0", None, "1.5"]:
            self.assertIsNone(id_numerico(valor))


class PaginasDeErroTests(TestCase):
    def test_404_usa_pagina_propria(self):
        user = Usuario.objects.create_user(username="analista", password="x")
        self.client.force_login(user)
        response = self.client.get("/rota-que-nao-existe/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Página não encontrada", status_code=404)
