from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
	EstadoCuentaViewSet
)

router = DefaultRouter()
router.register(r'estado_cuenta', EstadoCuentaViewSet, basename='api')

urlpatterns = [
	path('', include(router.urls))
]