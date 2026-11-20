"""Cálculos com dinheiro.

Usamos Decimal, e não float, para valores em reais.
Com float, 0.1 + 0.2 dá 0.30000000000000004; com Decimal dá exatamente 0.30.
O MySQL guarda DECIMAL(15,2) e o PyMySQL já entrega como Decimal.
"""

import math
import re
from decimal import Decimal

CENTAVO = Decimal("0.01")

# Até 13 dígitos antes da vírgula e 2 depois: cabe em DECIMAL(15,2).
_VALOR = re.compile(r"[0-9]{1,13}(\.[0-9]{1,2})?")


def ler_valor(valor):
    """Lê um valor enviado pelo app: 10, 10.5, "10.50" ou "10,50".

    Devolve um Decimal com 2 casas, ou None se o valor for inválido
    (negativo, texto, mais de 2 casas decimais, etc.).
    """
    # No Python, True/False também são números; aqui eles não valem.
    if isinstance(valor, bool):
        return None

    if isinstance(valor, int):
        texto_valor = str(valor)
    elif isinstance(valor, float):
        if not math.isfinite(valor):
            return None

        decimal = Decimal(str(valor))
        arredondado = decimal.quantize(CENTAVO)

        # Mais de 2 casas decimais (ex.: 10.123) é recusado.
        if abs(decimal - arredondado) > Decimal("1e-9"):
            return None

        texto_valor = str(arredondado)
    elif isinstance(valor, str):
        texto_valor = valor.strip().replace(",", ".", 1)
    else:
        return None

    if not _VALOR.fullmatch(texto_valor):
        return None

    return Decimal(texto_valor).quantize(CENTAVO)


def para_numero(valor):
    """Converte o Decimal do banco para número no JSON (2500.00 → 2500, 10.50 → 10.5)."""
    if valor is None:
        return None

    decimal = Decimal(valor)
    return int(decimal) if decimal == decimal.to_integral_value() else float(decimal)


def em_reais(valor):
    """Texto para mensagens: Decimal("10000") → "10000,00"."""
    return f"{Decimal(valor).quantize(CENTAVO)}".replace(".", ",")
