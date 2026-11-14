"""Validação de dados de formulário no backend, com mensagens por campo.

O frontend também valida, mas o backend nunca confia nele: todo POST passa por aqui.
As mensagens são pensadas para o usuário e nunca expõem detalhes internos.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError


def id_numerico(valor):
    """Converte um ID vindo da requisição; devolve None se não for inteiro positivo."""
    texto = str(valor or "").strip()
    return int(texto) if texto.isdigit() and int(texto) > 0 else None


class Validador:
    def __init__(self, dados):
        self.dados = dados
        self.erros = []

    def _bruto(self, campo):
        valor = self.dados.get(campo)
        return "" if valor is None else str(valor).strip()

    def texto(self, campo, rotulo, *, obrigatorio=False, max_len=None):
        valor = self._bruto(campo)
        if obrigatorio and not valor:
            self.erros.append(f"{rotulo}: campo obrigatório.")
        elif max_len and len(valor) > max_len:
            self.erros.append(f"{rotulo}: use no máximo {max_len} caracteres.")
        return valor

    def escolha(self, campo, rotulo, opcoes, *, padrao=None):
        valor = self._bruto(campo) or padrao
        if valor not in opcoes:
            self.erros.append(f"{rotulo}: selecione uma opção válida.")
            return padrao
        return valor

    def objeto(self, campo, rotulo, queryset, *, obrigatorio=True):
        bruto = self._bruto(campo)
        if not bruto:
            if obrigatorio:
                self.erros.append(f"{rotulo}: selecione uma opção.")
            return None
        pk = id_numerico(bruto)
        obj = queryset.filter(pk=pk).first() if pk else None
        if obj is None:
            self.erros.append(f"{rotulo}: opção inválida ou sem permissão de acesso.")
        return obj

    def decimal(
        self,
        campo,
        rotulo,
        *,
        max_digits,
        casas,
        obrigatorio=False,
        padrao=Decimal("0"),
        minimo=Decimal("0"),
    ):
        bruto = self._bruto(campo).replace(",", ".")
        if not bruto:
            if obrigatorio:
                self.erros.append(f"{rotulo}: campo obrigatório.")
            return padrao
        try:
            valor = Decimal(bruto)
        except InvalidOperation:
            self.erros.append(f"{rotulo}: informe um número válido.")
            return padrao
        if not valor.is_finite():
            self.erros.append(f"{rotulo}: informe um número válido.")
            return padrao
        if minimo is not None and valor < minimo:
            self.erros.append(f"{rotulo}: o valor mínimo é {minimo}.")
            return padrao
        if -valor.as_tuple().exponent > casas:
            self.erros.append(f"{rotulo}: use no máximo {casas} casas decimais.")
            return padrao
        if abs(valor) >= Decimal(10) ** (max_digits - casas):
            self.erros.append(f"{rotulo}: valor acima do limite permitido.")
            return padrao
        return valor

    def adicionar(self, mensagem):
        self.erros.append(mensagem)

    def verificar(self):
        if self.erros:
            raise ValidationError(self.erros)
