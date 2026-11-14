from django import template
from django.utils.html import format_html

from apps.core.idempotencia import CAMPO_CHAVE, gerar_chave

register = template.Library()


@register.simple_tag
def chave_envio():
    """Campo oculto com chave de idempotência nova a cada renderização do formulário."""
    return format_html('<input type="hidden" name="{}" value="{}">', CAMPO_CHAVE, gerar_chave())
