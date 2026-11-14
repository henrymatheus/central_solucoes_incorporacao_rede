from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from apps.core.forms import LoginForm


def _requisicao_assincrona(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


class LoginPage(LoginView):
    template_name = "registration/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if _requisicao_assincrona(self.request):
            # Uma única URL de destino, já validada por get_success_url() (next seguro).
            return JsonResponse({"redirect": response.url})
        return response

    def form_invalid(self, form):
        if _requisicao_assincrona(self.request):
            status = 429 if form.bloqueado else 400
            return JsonResponse({"error": form.primeira_mensagem_erro()}, status=status)
        return super().form_invalid(form)


@require_POST
def sair(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "Sessão encerrada.")
    return redirect("login")
