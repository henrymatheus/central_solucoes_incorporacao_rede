from pathlib import PurePath

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.core.idempotencia import ChaveEnvioInvalida, EnvioDuplicado, registrar_envio
from apps.core.models import Distribuidora
from apps.core.permissions import is_dev, usuario_tem_distribuidora
from apps.core.validacao import Validador
from apps.documentos.models import DocumentoModelo, RegistroDownload

EXTENSOES_PERMITIDAS = {
    "pdf", "doc", "docx", "xls", "xlsx", "xlsm", "csv", "ppt", "pptx",
    "txt", "zip", "dwg", "dxf", "png", "jpg", "jpeg",
}  # fmt: skip
TAMANHO_MAXIMO_MB = 50


def _abrir_arquivo(campo_arquivo):
    """Abre o arquivo do storage; 404 claro se ele não existir mais."""
    if not campo_arquivo:
        raise Http404("O arquivo não está disponível.")
    try:
        return campo_arquivo.open("rb")
    except (FileNotFoundError, OSError) as exc:
        raise Http404("O arquivo não foi encontrado no armazenamento.") from exc


@login_required
def lista_documentos(request):
    documentos = DocumentoModelo.objects.filter(vigente=True).select_related(
        "distribuidora", "enviado_por"
    )
    perfil = getattr(request.user, "perfil", None)
    if not is_dev(request.user):
        permitidas = perfil.distribuidoras.all() if perfil else []
        documentos = documentos.filter(
            Q(distribuidora__in=permitidas) | Q(distribuidora__isnull=True)
        )
    if busca := request.GET.get("q", "").strip():
        documentos = documentos.filter(titulo__icontains=busca)
    if categoria := request.GET.get("categoria"):
        documentos = documentos.filter(categoria=categoria)
    return render(
        request,
        "documentos/lista.html",
        {
            "documentos": documentos,
            "categorias": DocumentoModelo.CATEGORIAS,
            "pode_publicar": is_dev(request.user),
        },
    )


@login_required
@require_GET
def baixar_documento(request, pk):
    documento = get_object_or_404(DocumentoModelo, pk=pk, vigente=True)
    if documento.distribuidora_id and not usuario_tem_distribuidora(
        request.user, documento.distribuidora
    ):
        raise PermissionDenied("Seu perfil não tem acesso a este documento.")
    arquivo = _abrir_arquivo(documento.arquivo)
    RegistroDownload.objects.create(documento=documento, usuario=request.user)
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=documento.arquivo.name.rsplit("/", 1)[-1],
    )


def _validar_arquivo(validador, arquivo):
    if not arquivo:
        validador.adicionar("Arquivo: selecione o arquivo a publicar.")
        return
    extensao = PurePath(arquivo.name).suffix.lower().lstrip(".")
    if extensao not in EXTENSOES_PERMITIDAS:
        validador.adicionar(
            "Arquivo: formato não permitido. Use " + ", ".join(sorted(EXTENSOES_PERMITIDAS)) + "."
        )
    if arquivo.size > TAMANHO_MAXIMO_MB * 1024 * 1024:
        validador.adicionar(f"Arquivo: o tamanho máximo é {TAMANHO_MAXIMO_MB} MB.")
    if arquivo.size == 0:
        validador.adicionar("Arquivo: o arquivo enviado está vazio.")


@login_required
def enviar_documento(request):
    if not is_dev(request.user):
        raise PermissionDenied("Somente Desenvolvedor pode publicar documentos modelo.")
    distribuidoras = Distribuidora.objects.filter(ativa=True)
    if request.method == "POST":
        try:
            with transaction.atomic():
                envio = registrar_envio(request)
                v = Validador(request.POST)
                titulo = v.texto("titulo", "Título", obrigatorio=True, max_len=180)
                categoria = v.escolha(
                    "categoria", "Categoria", dict(DocumentoModelo.CATEGORIAS), padrao="OUTRO"
                )
                descricao = v.texto("descricao", "Descrição", max_len=2000)
                distribuidora = v.objeto(
                    "distribuidora", "Distribuidora", distribuidoras, obrigatorio=False
                )
                arquivo = request.FILES.get("arquivo")
                _validar_arquivo(v, arquivo)
                v.verificar()

                anteriores = DocumentoModelo.objects.select_for_update().filter(
                    titulo=titulo, categoria=categoria
                )
                versao = (anteriores.aggregate(maior=Max("versao"))["maior"] or 0) + 1
                anteriores.filter(vigente=True).update(vigente=False)
                DocumentoModelo.objects.create(
                    titulo=titulo,
                    categoria=categoria,
                    descricao=descricao,
                    arquivo=arquivo,
                    versao=versao,
                    distribuidora=distribuidora,
                    enviado_por=request.user,
                )
                envio.concluir(reverse("documentos:lista"))
            messages.success(request, f"Documento publicado como versão {versao}.")
            return redirect("documentos:lista")
        except EnvioDuplicado as dup:
            messages.info(request, str(dup))
            return redirect(dup.resultado_url or "documentos:lista")
        except ChaveEnvioInvalida as exc:
            messages.error(request, str(exc))
        except ValidationError as exc:
            for mensagem in exc.messages:
                messages.error(request, mensagem)
        except IntegrityError:
            messages.error(
                request,
                "Outra publicação deste documento foi concluída ao mesmo tempo. "
                "Confira a lista e tente novamente.",
            )
    return render(
        request,
        "documentos/enviar.html",
        {
            "categorias": DocumentoModelo.CATEGORIAS,
            "distribuidoras": distribuidoras,
            "dados": request.POST if request.method == "POST" else {},
            "extensoes": ",".join(f".{ext}" for ext in sorted(EXTENSOES_PERMITIDAS)),
            "tamanho_maximo_mb": TAMANHO_MAXIMO_MB,
        },
    )
