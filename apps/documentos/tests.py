from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.idempotencia import CAMPO_CHAVE, gerar_chave
from apps.core.models import Distribuidora, Perfil, Usuario
from apps.documentos.models import DocumentoModelo, RegistroDownload


class DocumentosTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.distribuidora = Distribuidora.objects.create(
            sigla="EQTL-PA", nome="Equatorial Pará", nome_catalogo="PARÁ", uf="PA"
        )
        self.dev = Usuario.objects.create_user(username="dev", password="senha-forte")
        self.dev.perfil.tipo = Perfil.Tipo.DEV
        self.dev.perfil.save()
        self.client.force_login(self.dev)

    def _dados(self, **extra):
        dados = {
            "titulo": "Checklist POP.00813",
            "categoria": "CHECKLIST",
            "arquivo": SimpleUploadedFile("checklist.xlsx", b"conteudo"),
            CAMPO_CHAVE: gerar_chave(),
        }
        dados.update(extra)
        return dados

    def test_dois_cliques_em_publicar_geram_uma_versao(self):
        dados = self._dados()
        self.client.post(reverse("documentos:enviar"), dados)
        dados["arquivo"] = SimpleUploadedFile("checklist.xlsx", b"conteudo")
        self.client.post(reverse("documentos:enviar"), dados)
        self.assertEqual(DocumentoModelo.objects.count(), 1)

    def test_nova_publicacao_cria_versao_e_arquiva_anterior(self):
        self.client.post(reverse("documentos:enviar"), self._dados())
        self.client.post(reverse("documentos:enviar"), self._dados())
        versoes = list(DocumentoModelo.objects.order_by("versao").values_list("versao", "vigente"))
        self.assertEqual(versoes, [(1, False), (2, True)])

    def test_distribuidora_invalida_extensao_e_vazio_sao_rejeitados(self):
        casos = [
            {"distribuidora": "abc"},
            {"distribuidora": "999"},
            {"arquivo": SimpleUploadedFile("virus.exe", b"MZ")},
            {"arquivo": SimpleUploadedFile("vazio.pdf", b"")},
            {"titulo": "   "},
        ]
        for extra in casos:
            with self.subTest(extra=list(extra)):
                resposta = self.client.post(reverse("documentos:enviar"), self._dados(**extra))
                self.assertEqual(resposta.status_code, 200)
        self.assertFalse(DocumentoModelo.objects.exists())

    def test_somente_dev_publica(self):
        usuario = Usuario.objects.create_user(username="tatico", password="senha-forte")
        self.client.force_login(usuario)
        resposta = self.client.post(reverse("documentos:enviar"), self._dados())
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(DocumentoModelo.objects.exists())

    def test_download_registra_log_e_arquivo_ausente_responde_404(self):
        documento = DocumentoModelo.objects.create(titulo="Termo", categoria="TERMO")
        documento.arquivo.save("termo.pdf", ContentFile(b"pdf"))
        url = reverse("documentos:download", args=[documento.pk])
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        b"".join(resposta.streaming_content)
        resposta.close()  # libera o arquivo (Windows) antes de apagá-lo
        self.assertEqual(RegistroDownload.objects.count(), 1)

        documento.arquivo.storage.delete(documento.arquivo.name)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(RegistroDownload.objects.count(), 1)
