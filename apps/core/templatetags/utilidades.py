from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def obter(dicionario, chave):
    try:
        return dicionario.get(chave, 0)
    except AttributeError:
        return 0


@register.filter
def pct(parte, todo):
    try:
        return f"{100 * float(parte) / float(todo):.0f}%" if float(todo) else "0%"
    except (TypeError, ValueError):
        return "0%"


def _milhar(n):
    return f"{n:,.0f}".replace(",", ".")


@register.filter
def brl(valor):
    """R$ 1.234 (inteiro, pt-BR)."""
    try:
        return f"R$ {_milhar(Decimal(valor or 0))}"
    except Exception:
        return "R$ 0"


@register.filter
def brl_c(valor):
    """Compacto: R$ 1,2 mi / R$ 350 mil."""
    try:
        v = float(valor or 0)
    except (TypeError, ValueError):
        return "R$ 0"
    if abs(v) >= 1_000_000:
        return f"R$ {v / 1_000_000:.1f} mi".replace(".", ",")
    if abs(v) >= 1_000:
        return f"R$ {v / 1_000:.0f} mil"
    return f"R$ {v:.0f}"


@register.filter
def dias(valor):
    """123 → "123 d"; None → "—"."""
    if valor is None or valor == "":
        return "—"
    return f"{_milhar(int(valor))} d"


@register.filter
def milhar(valor):
    try:
        return _milhar(float(valor or 0))
    except (TypeError, ValueError):
        return "0"


@register.filter
def br_pct(valor):
    """12.5 → "12,5%"."""
    try:
        v = float(valor or 0)
    except (TypeError, ValueError):
        return "0%"
    return (f"{v:.0f}%" if v == int(v) else f"{v:.1f}%").replace(".", ",")


@register.filter
def largura(valor):
    """Percentual para CSS (sempre com ponto decimal): 12.5 → "12.5%"."""
    try:
        v = max(0.0, min(100.0, float(valor or 0)))
    except (TypeError, ValueError):
        v = 0.0
    return f"{v:.1f}%"
