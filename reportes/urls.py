from django.urls import path
from .views import *


urlpatterns = [
	path('', Index.as_view(), name='reportes'),
	path('nuevo/periodo', NuevoPeriodo.as_view(), name='cierre-nuevo'),
	path('nuevo/<int:pk>/', NuevoProcesamiento.as_view(), name='cierre-procesamiento'),
	path('eliminar/<int:pk>/', CierreEliminar.as_view(), name='cierre-eliminar'),
	path('confirmar/<int:pk>/', CierreConfirmar.as_view(), name='cierre-confirmar'),
	path('ver/<int:pk>/', CierreVer.as_view(), name='cierre-ver'),

	path('archivos/<int:pk>/', ArchivoGuardar.as_view(), name='archivo-guardar'), # pk no es una instancia de reporte. Es solo para agregar al reporte el cierre y que use el HeaderExceptMixin
	path('archivos/eliminar/<int:pk>/', ArchivoEliminar.as_view(), name='archivo-eliminar'),
	path('descargar/<int:pk>/', PDFReporte.as_view(), name='archivo-descargar'),

]
