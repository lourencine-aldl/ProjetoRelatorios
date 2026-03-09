"""
Django settings for MVP Relatórios.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-change-in-production')

DEBUG = os.environ.get('DEBUG', '1') == '1'

_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0')
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()]
if DEBUG:
    ALLOWED_HOSTS = ['*']  # em desenvolvimento aceita qualquer Host

# CSRF: Django 4+ exige origens confiáveis para POST (evita 403 "Verificação CSRF falhou")
_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '').strip()
if _origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _origins.split(',') if o.strip()]
else:
    # Gerar a partir de ALLOWED_HOSTS + origens comuns (porta 2026 = Docker, 8000 = interno)
    _port = os.environ.get('CSRF_TRUSTED_ORIGINS_PORT', '2026')
    _base = [f'http://127.0.0.1:{_port}', f'http://localhost:{_port}', 'http://127.0.0.1:8000']
    _from_hosts = [f'http://{h.strip()}:{_port}' for h in _hosts.split(',') if h.strip() and h.strip() != '*']
    CSRF_TRUSTED_ORIGINS = _base + _from_hosts

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'django_htmx',
    'relatorios',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'relatorios.context_processors.pbi_menu',
                'relatorios.context_processors.sidebar_filters_default',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# SQLite para dev; em Docker use DATABASE_PATH (ex.: /app/db/db.sqlite3)
_db_path = os.environ.get('DATABASE_PATH')
if _db_path:
    _db_name = str(_db_path)
else:
    _db_name = str(BASE_DIR / 'db.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _db_name,
    }
}

# Cache para relatórios (dashboard e opções de filtro) — reduz consultas repetidas
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'OPTIONS': {'MAX_ENTRIES': 500},
        'TIMEOUT': 120,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Em HTTP (sem HTTPS) o browser ignora Cross-Origin-Opener-Policy e mostra aviso.
# Desativar o cabeçalho para evitar o aviso em desenvolvimento / HTTP.
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Caminho do CSV para importação de vendas (relativo a BASE_DIR ou absoluto)
IMPORT_VENDAS_CSV_PATH = os.environ.get('IMPORT_VENDAS_CSV_PATH', str(BASE_DIR / 'dados' / 'Relatorio_Fat.csv'))
# Formato do CSV: separador (novo formato usa ";") e format (vazio = com cabeçalho; "relatorio_fat" = antigo sem cabeçalho, vírgula)
IMPORT_VENDAS_CSV_SEP = os.environ.get('IMPORT_VENDAS_CSV_SEP', ';')
IMPORT_VENDAS_CSV_FORMAT = os.environ.get('IMPORT_VENDAS_CSV_FORMAT', '').strip().lower()  # '' = header + DictReader

# Valores no banco estão em escala 1000x (ex.: valor 1000 = R$ 1,00). Use 1 se o CSV já estiver em reais (novo Relatorio_Fat).
VALOR_DIVISOR = int(os.environ.get('VALOR_DIVISOR', '1'))

# Permissões customizadas (códigos)
PERMISSAO_VER_RELATORIO_VENDAS = 'relatorios.pode_ver_relatorio_vendas'
PERMISSAO_EXPORTAR_EXCEL = 'relatorios.pode_exportar_excel'
PERMISSAO_VER_TODAS_FILIAIS = 'relatorios.pode_ver_todas_filiais'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}
