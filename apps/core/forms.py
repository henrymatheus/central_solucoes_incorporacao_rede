import hashlib

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError


def _ip_cliente(request):
    return (request.META.get("REMOTE_ADDR") or "desconhecido") if request else "desconhecido"


class LoginForm(AuthenticationForm):
    """Login com mensagens genéricas (V2.7) e bloqueio por força bruta (V2.6)."""

    error_messages = {
        "invalid_login": "Usuário ou senha incorretos.",
        "inactive": "Este acesso está desativado. Fale com a equipe de Tático de Projetos.",
        "bloqueado": (
            "Muitas tentativas sem sucesso. Por segurança, o acesso foi bloqueado "
            "temporariamente. Tente novamente em %(minutos)s minutos."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bloqueado = False
        self.fields["username"].error_messages["required"] = "Informe o usuário."
        self.fields["password"].error_messages["required"] = "Informe a senha."
        self.fields["username"].widget.attrs.update(
            {
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "Usuário",
                "maxlength": "150",
            }
        )
        self.fields["username"].widget.attrs.pop("autofocus", None)
        self.fields["password"].widget.attrs.update(
            {
                "autocomplete": "current-password",
                "placeholder": "Senha",
                "data-no-trim": "",
            }
        )

    # --- controle de tentativas -------------------------------------------------
    def _chave_tentativas(self, username):
        base = f"{username.strip().lower()}|{_ip_cliente(self.request)}"
        return "login-falhas:" + hashlib.sha256(base.encode()).hexdigest()

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not username or not password:
            return self.cleaned_data
        chave = self._chave_tentativas(username)
        limite = settings.LOGIN_MAX_TENTATIVAS
        bloqueio = settings.LOGIN_BLOQUEIO_SEGUNDOS
        if (cache.get(chave) or 0) >= limite:
            self.bloqueado = True
            raise ValidationError(
                self.error_messages["bloqueado"],
                code="bloqueado",
                params={"minutos": bloqueio // 60},
            )
        try:
            cleaned = super().clean()
        except ValidationError:
            if cache.add(chave, 1, bloqueio) is False:
                try:
                    cache.incr(chave)
                except ValueError:
                    cache.set(chave, 1, bloqueio)
            raise
        cache.delete(chave)
        return cleaned

    def primeira_mensagem_erro(self):
        for erro in self.non_field_errors():
            return erro
        if self.errors:
            return "Informe usuário e senha."
        return ""
