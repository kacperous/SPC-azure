from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
import os 

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- ŚRODOWISKO I BEZPIECZEŃSTWO ---
SECRET_KEY = os.getenv("BACKEND_SECRET_KEY")
DEBUG = os.environ.get('DEBUG', 'False') == 'True'  # ZAWSZE False w produkcji

ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 
    'localhost,127.0.0.1,0.0.0.0'  # ← DODAJ te 3!
).split(',')

# CSRF - dla Azure Container Apps
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS', 
    'http://localhost'
).split(',')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- APPLICATION DEFINITION ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',
    'corsheaders', 
    'storages',
    'rest_framework_simplejwt', 
    'drf_spectacular',
    
    'users',
    'files',
    'logs',
    'frontend',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated', 
    ]
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'spc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'spc.wsgi.application'

# --- DATABASE (AZURE POSTGRESQL) ---
DB_HOST = os.getenv('POSTGRES_HOST', 'db_spc') 

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': DB_HOST, 
        'PORT': os.getenv('POSTGRES_PORT', '5432'),     
        'OPTIONS': {
            'sslmode': 'require' if 'azure.com' in DB_HOST else 'allow' 
        }
    }
}

# --- PODSTAWOWE USTAWIENIA ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Warsaw'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- AZURE BLOB STORAGE (tylko MEDIA) ---
AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
AZURE_CONTAINER = os.getenv('AZURE_CONTAINER', 'media')
AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'

# URL do plików wgrywanych przez użytkowników
MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_CONTAINER}/'

# Magazyn TYLKO dla MEDIA (wgrane pliki użytkowników)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            "account_name": AZURE_ACCOUNT_NAME,
            "account_key": os.getenv("AZURE_ACCOUNT_KEY"),
            "azure_container": AZURE_CONTAINER,
            "azure_ssl": True, 
            "expiration_secs": timedelta(hours=1).total_seconds(),
            "overwrite_files": False,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    }
}

# STATIC - minimalna konfiguracja (Django domyślnie)
STATIC_URL = '/static/'
