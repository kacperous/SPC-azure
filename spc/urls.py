# spc/urls.py

from django.contrib import admin
from django.urls import path, include

# Importy dla logowania
from users.views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

# Importy dla serwowania plików MEDIA lokalnie (tylko w trybie DEBUG)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- Adresy API (Mózg) ---
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Podłączamy wszystkie adresy z 'files' pod '/api/'
    path('api/', include('files.urls')),
    
    # --- Adresy Aplikacji (Twarz) ---
    # Podłączamy naszą główną stronę
    path('', include('frontend.urls')),
]

# Ta linia jest potrzebna, aby pliki działały LOKALNIE w Dockerze (w Fazie 1)
# Serwuje pliki z folderu 'media'
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)