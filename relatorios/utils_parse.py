# -*- coding: utf-8 -*-
"""
Normalização de valores pt-BR para import CSV.
- Decimais com vírgula → Decimal
- Datas "01-fev-2024 00:00:00" → datetime
- Códigos/IDs → string (evitar notação científica)
"""
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime

MESES_PT = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
}


def parse_decimal_br(value):
    """Converte string para Decimal. Aceita pt-BR (3,14), ISO (2159.28) e formato 192.530.518 (ponto como milhar, último grupo 3 dígitos = decimal)."""
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return None
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    s = str(value).strip()
    # Formato pt-BR só pontos (ex.: 7.459.944 = 7459,944): milhares + último grupo de 3 dígitos = decimal
    if ',' not in s and '.' in s:
        parts = s.split('.')
        if len(parts) >= 2 and len(parts[-1]) == 3 and parts[-1].isdigit():
            try:
                inteiro = int(''.join(parts[:-1]))  # "192" + "530" = 192530
                decimal = int(parts[-1]) / 1000   # 518 → 0.518
                return Decimal(str(inteiro + decimal))
            except (ValueError, InvalidOperation):
                pass
    # Formato ISO (ponto decimal, ex: 2159.28): usar direto
    if ',' not in s:
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            pass
    # Formato pt-BR: vírgula decimal, ponto milhares
    s = s.replace('.', '').replace(',', '.')
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def safe_decimal_for_db(value, max_digits=16, decimal_places=4, default=None):
    """Retorna Decimal válido para o banco (sem NaN/Inf, dentro de max_digits/decimal_places)."""
    if value is None:
        return default
    try:
        d = value if isinstance(value, Decimal) else Decimal(str(value))
        if d.is_nan() or d.is_infinite():
            return default
        quantize = Decimal(10) ** -decimal_places
        max_val = Decimal(10) ** (max_digits - decimal_places) - quantize
        if d > max_val:
            d = max_val
        elif d < -max_val:
            d = -max_val
        try:
            return d.quantize(quantize)
        except InvalidOperation:
            return default
    except (InvalidOperation, ValueError, TypeError):
        return default


def parse_date_br(value):
    """Converte data pt-BR (ex: '01-fev-2024 00:00:00') para datetime."""
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return None
    if hasattr(value, 'isoformat'):  # já é date/datetime
        return value
    s = str(value).strip()
    # 01-fev-2024 00:00:00
    m = re.match(r'(\d{1,2})-([a-z]{3})-(\d{4})\s*(\d{2}:\d{2}:\d{2})?', s, re.I)
    if m:
        dia, mes_str, ano = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
        mes = MESES_PT.get(mes_str)
        if mes:
            hora, minu, seg = 0, 0, 0
            if m.group(4):
                parts = m.group(4).split(':')
                hora, minu = int(parts[0]), int(parts[1])
                seg = int(parts[2]) if len(parts) > 2 else 0
            return datetime(ano, mes, dia, hora, minu, seg)
    # ISO, Y/m/d (ex: 2021/03/01 00:00:00.000000000), DD/MM/YYYY
    s_short = s[:19] if len(s) >= 19 else (s[:10] if len(s) >= 10 else s)
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y'):
        try:
            return datetime.strptime(s_short, fmt)
        except ValueError:
            continue
    return None


def parse_codigo(value):
    """Mantém código como string; evita notação científica (ex: 1,72E+09)."""
    if value is None:
        return ''
    s = str(value).strip()
    if not s:
        return ''
    # Se veio como float científico, converter para int e depois string
    try:
        f = float(s.replace(',', '.'))
        if 1e10 > abs(f) == int(f):
            return str(int(f))
    except (ValueError, TypeError):
        pass
    return s
