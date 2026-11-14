from pathlib import Path

from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config("CSIR_SECRET_KEY", default="dev-only-change-me-before-deploying")
DEBUG = config("CSIR_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config(
    "CSIR_ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=lambda value: [host.strip() for host in value.split(",") if host.strip()],
)
if not DEBUG and SECRET_KEY == "dev-only-change-me-before-deploying":
    raise ImproperlyConfigured("Defina CSIR_SECRET_KEY fora do modo de desenvolvimento.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core.apps.CoreConfig",
    "apps.integracao",
    "apps.incorporacao",
    "apps.documentos",
    "apps.gestao",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": config("CSIR_DB_ENGINE", default="django.db.backends.sqlite3"),
        "NAME": config("CSIR_DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
    }
}

AUTH_USER_MODEL = "core.Usuario"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "gestao:visao_geral"
LOGOUT_REDIRECT_URL = "login"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = Path(config("CSIR_MEDIA_ROOT", default=str(BASE_DIR / "media")))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 110 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# --- Segurança de sessão e login (especificação V2.6 / V2.15) ---
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
LOGIN_MAX_TENTATIVAS = config("CSIR_LOGIN_MAX_TENTATIVAS", default=5, cast=int)
LOGIN_BLOQUEIO_SEGUNDOS = config("CSIR_LOGIN_BLOQUEIO_SEGUNDOS", default=30 * 60, cast=int)
# Em produção com vários workers, use cache compartilhado (Redis) para o bloqueio valer
# entre processos: CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", ...}}

# --- Snowflake (somente leitura) ---
CSIR_SNOWFLAKE_CONNECTION = config("CSIR_SNOWFLAKE_CONNECTION", default="CFGKDTB-ISB76799")
CSIR_SNOWFLAKE_TABELA = config(
    "CSIR_SNOWFLAKE_TABELA", default="SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO"
)
CSIR_SNOWFLAKE_TIMEOUT = config("CSIR_SNOWFLAKE_TIMEOUT", default=300, cast=int)
CSIR_POWER_BI_URL = config(
    "CSIR_POWER_BI_URL",
    default=(
        "https://bi.equatorialenergia.com.br/reports/powerbi/EQTL%20PA%20-%20DISTRIBUIDORA/"
        "T%C3%81TICO%20DE%20PROJETOS/Gest%C3%A3o%20de%20Incorpora%C3%A7%C3%A3o%20RD"
        "?rs:Command=Render&rc:Toolbar=false"
    ),
)
CSIR_DISTRIBUIDORA_PADRAO = config("CSIR_DISTRIBUIDORA_PADRAO", default="EQTL-PA")
