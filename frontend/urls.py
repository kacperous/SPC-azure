# frontend/urls.py

from django.urls import path
from .views import FrontendAppView

urlpatterns = [
    # Jak ktoś wejdzie na główny adres ('/'), pokaż mu widok 'Twarzy'
    path('', FrontendAppView.as_view(), name='frontend_app'),
]