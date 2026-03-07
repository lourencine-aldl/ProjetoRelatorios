# -*- coding: utf-8 -*-
"""Filtros de formatação pt-BR para templates."""
from django import template
from decimal import Decimal

register = template.Library()

# Limiar a partir do qual usar abreviação (milhões) nos cards
_ABREV_LIMIAR = Decimal('999999')   # >= 1 milhão → "1,23 mi"


def _format_decimal(value, decimals=2):
    """Formata número com vírgula decimal e ponto para milhares (pt-BR)."""
    if value is None:
        return '0,00'
    try:
        n = Decimal(str(value))
        s = f'{n:,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        return s
    except (ValueError, TypeError):
        return '0,00'


def _abreviar(n):
    """Retorna tupla (número escalado, sufixo): (1,74, 'tri'), (134, 'mi'), etc."""
    if n is None:
        return (Decimal('0'), '')
    try:
        x = Decimal(str(n))
    except (ValueError, TypeError):
        return (Decimal('0'), '')
    x = abs(x)
    if x >= Decimal('1e12'):
        return (x / Decimal('1e12'), ' tri')
    if x >= Decimal('1e9'):
        return (x / Decimal('1e9'), ' bi')
    if x >= Decimal('1e6'):
        return (x / Decimal('1e6'), ' mi')
    if x >= Decimal('1e3'):
        return (x / Decimal('1e3'), ' mil')
    return (x, '')


@register.filter
def br_currency(value):
    """R$ 1.234,56 (valor monetário com 2 decimais)."""
    if value is None:
        return 'R$ 0,00'
    return 'R$ ' + _format_decimal(value, 2)


@register.filter
def br_currency_short(value):
    """Valor em R$ com 2 decimais; acima de 1 mi usa abreviação (mi, bi, tri)."""
    if value is None:
        return 'R$ 0,00'
    try:
        n = Decimal(str(value))
    except (ValueError, TypeError):
        return 'R$ 0,00'
    num, sufixo = _abreviar(n)
    if sufixo:
        s = _format_decimal(num, 2) + sufixo
        return ('R$ ' + s) if n >= 0 else '- R$ ' + s
    return 'R$ ' + _format_decimal(value, 2)


@register.filter
def br_decimal(value, decimals=2):
    """1.234,56 (decimal pt-BR)."""
    return _format_decimal(value, int(decimals) if decimals else 2)


@register.filter
def br_decimal_short(value, decimals=2):
    """Decimal pt-BR; acima de 1 mi usa abreviação (mi, bi, tri)."""
    if value is None:
        return '0,00'
    try:
        n = Decimal(str(value))
    except (ValueError, TypeError):
        return '0,00'
    num, sufixo = _abreviar(n)
    dec = int(decimals) if decimals else 2
    if sufixo:
        return _format_decimal(num, dec) + sufixo
    return _format_decimal(value, dec)


def _format_int_sep(value):
    """Formata inteiro com separador de milhares (pt-BR: ponto). Ex: 4470000 -> 4.470.000."""
    if value is None:
        return '0'
    try:
        n = int(Decimal(str(value)))
        return f'{n:,}'.replace(',', '.')
    except (ValueError, TypeError):
        return '0'


@register.filter
def br_int(value):
    """1234 (inteiro, sem decimais)."""
    if value is None:
        return '0'
    try:
        return str(int(Decimal(str(value))))
    except (ValueError, TypeError):
        return '0'


@register.filter
def br_int_sep(value):
    """Inteiro com separador de milhares (pt-BR), sem casa decimal. Ex: 4.470.000."""
    return _format_int_sep(value)


@register.filter
def br_decimal_sep(value, decimals=2):
    """Número com separador de milhares e casas decimais (pt-BR). Ex: 14.610.000,50."""
    if value is None:
        return _format_decimal(0, int(decimals) if decimals else 2)
    return _format_decimal(value, int(decimals) if decimals else 2)


@register.filter
def is_negative(value):
    """Retorna True se o valor for negativo (para estilizar em vermelho)."""
    if value is None:
        return False
    try:
        return Decimal(str(value)) < 0
    except (ValueError, TypeError):
        return False


@register.filter
def br_int_short(value):
    """Inteiro; acima de 1 mi usa abreviação (mil, mi, bi, tri)."""
    if value is None:
        return '0'
    try:
        n = Decimal(str(value))
        x = abs(n)
    except (ValueError, TypeError):
        return '0'
    num, sufixo = _abreviar(n)
    if sufixo:
        return _format_decimal(num, 2) + sufixo
    return str(int(n))
