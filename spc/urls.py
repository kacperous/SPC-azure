# spc/urls.py

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularSwaggerView
from users.views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

# Importy dla serwowania plików MEDIA lokalnie (tylko w trybie DEBUG)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('api/users/', include('users.urls')),

    path('api/', include('files.urls')),
    path('api/', include('logs.urls')),

    path('', include('frontend.urls')),
]