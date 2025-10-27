"""
Django settings for spc project.
"""

from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
import os 

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("BACKEND_SECRET_KEY")

# WAŻNE: W trybie lokalnym DOCKER musisz mieć DEBUG=True, aby poprawnie
# zarządzać błędami i plikami. Zmieniamy na True:
DEBUG = True 

ALLOWED_HOSTS = ["*"] # Zostawiamy na development


# --- APPLICATION DEFINITION ---

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Zewnętrzne pakiety
    'drf_spectacular',
    'rest_framework',
    'rest_framework_simplejwt', 
    'storages',  # Azure Storage

    # Twoje aplikacje
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

SPECTACULAR_SETTINGS = {
    'TITLE': 'SPC API',
    'DESCRIPTION': 'Project SPC API documentation',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
        'DIRS': [os.path.join(BASE_DIR, 'templates')], 
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
            'sslmode': 'require' if DB_HOST.endswith('.azure.com') else 'allow'
        }
    }
}


# --- PASSWORD VALIDATION & LOCALES ---

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# --- FILE STORAGE (MEDIA & STATIC) ---

# Użyjemy globalnych zmiennych z .env do tworzenia adresów URL
AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
AZURE_CONTAINER = os.getenv('AZURE_CONTAINER')
AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'

# URL do publicznego dostępu (Media)
MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_CONTAINER}/'

# URL do plików statycznych (np. CSS)
STATIC_URL = f'https://{AZURE_CUSTOM_DOMAIN}/static/'


STORAGES = {
    # 1. Główny magazyn dla plików wgrywanych przez użytkowników (MEDIA)
    "default": {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            # AUTENTYKACJA
            "account_name": AZURE_ACCOUNT_NAME,
            "account_key": os.getenv("REMOVED_AZURE_ACCOUNT_KEY"),
            
            # WŁAŚCIWE USTAWIENIA AZURE
            "azure_container": AZURE_CONTAINER,
            # "azure_protocol": 'https', # Zawsze używaj HTTPS
            "azure_ssl": True, # Wymuszenie bezpiecznego połączenia
            
            # USTAWIENIA TOKENU SAS (Klucz do rozwiązania problemu PublicAccessNotPermitted)
            "expiration_secs": timedelta(hours=1).total_seconds(), # Token wygasa po 1h
            
            # Bezpieczeństwo i domyślny dostęp (None jest najlepsze dla SAS)
            "overwrite_files": False, # Nie nadpisuj plików
        },
    },
    
    # 2. Magazyn dla plików statycznych (STATIC)
    "staticfiles": {
        "BACKEND": "storages.backends.azure_storage.AzureStorage",
        "OPTIONS": {
            "account_name": AZURE_ACCOUNT_NAME,
            "account_key": os.getenv("REMOVED_AZURE_ACCOUNT_KEY"),
            "azure_container": "static", # Kontener na pliki statyczne
            # "azure_protocol": 'https',
            "azure_ssl": True,
            "cache_control": "public, max-age=31536000, immutable", # Długie buforowanie
        },
    }
}


# --- RESZTA USTAWIENIA ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'