# frontend/urls.py

from django.urls import path
from .views import FrontendAppView, UserView

urlpatterns = [
    # Jak ktoś wejdzie na główny adres ('/'), pokaż mu widok 'Twarzy'
    path('', FrontendAppView.as_view(), name='frontend_app'),
    path('userView.html', UserView.as_view(), name='user_view'),
]