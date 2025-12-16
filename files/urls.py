# files/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserFileViewSet

# Router automatycznie generuje adresy dla 'Kierownika'
# GET, POST -> /api/files/
# GET, DELETE -> /api/files/1/
router = DefaultRouter()
router.register(r"files", UserFileViewSet, basename="file")

urlpatterns = [
    path("", include(router.urls)),
]
