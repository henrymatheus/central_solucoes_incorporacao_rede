"""Proteção de backend contra submissão repetida de formulários.

Uso na view (sempre dentro da mesma transação que cria o registro, para que uma
falha de validação desfaça também o registro da chave e o usuário possa tentar de novo):

    try:
        with transaction.atomic():
            envio = registrar_envio(request)
            ...  # valida e cria
            envio.concluir(url_do_resultado)
    except EnvioDuplicado as dup:
        return redirect(dup.resultado_url or fallback)
    except ChaveEnvioInvalida as exc:
        messages.error(request, str(exc))

No template: ``{% load seguranca %}{% chave_envio %}`` dentro do <form>.
"""

import re
import secrets

from django.db import IntegrityError, transaction

from apps.core.models import EnvioFormulario

CAMPO_CHAVE = "idempotency_key"
_FORMATO_CHAVE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
MENSAGEM_DUPLICADO = "Esta solicitação já foi processada. Nenhum registro duplicado foi criado."


class ChaveEnvioInvalida(Exception):
    def __init__(self):
        super().__init__("O formulário expirou. Recarregue a página e tente novamente.")


class EnvioDuplicado(Exception):
    def __init__(self, resultado_url=""):
        super().__init__(MENSAGEM_DUPLICADO)
        self.resultado_url = resultado_url


def gerar_chave():
    return secrets.token_urlsafe(24)


class _Envio:
    def __init__(self, registro):
        self._registro = registro

    def concluir(self, resultado_url=""):
        if resultado_url:
            self._registro.resultado_url = str(resultado_url)[:300]
            self._registro.save(update_fields=["resultado_url"])


def registrar_envio(request):
    """Reserva a chave do formulário. Lança EnvioDuplicado se ela já foi usada."""
    chave = (request.POST.get(CAMPO_CHAVE) or "").strip()
    if not _FORMATO_CHAVE.match(chave):
        raise ChaveEnvioInvalida()
    usuario = request.user if request.user.is_authenticated else None
    try:
        with transaction.atomic():
            registro = EnvioFormulario.objects.create(chave=chave, usuario=usuario)
    except IntegrityError:
        existente = EnvioFormulario.objects.filter(chave=chave).first()
        raise EnvioDuplicado(existente.resultado_url if existente else "") from None
    return _Envio(registro)
