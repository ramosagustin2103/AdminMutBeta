from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.conf.urls.static import static
from .views import *


urlpatterns = [
    path('', front, name='front'),
    path('el_json_para_huevo/<int:pk>/' , el_json_para_huevo, name='el_json_para_huevo' ),
    path('admincudj/', admin.site.urls),
    path('recuperar-pass/', include('django.contrib.auth.urls')),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('signup/', SignUp.as_view(), name='signup'),
    path('mercadopago/', include(('django_mercadopago.urls', 'mercadopago'), namespace='mp')),
    path('terms/', include('termsandconditions.urls')),
    path('maintenance-mode/', include('maintenance_mode.urls')),
    path('home', home, name='home'),
    path('biblioteca/', include('biblioteca.urls')),
    path('perfil/', include('perfil.urls')),
    path('mantenimiento/', mantenimiento, name='mantenimiento'),
    path('parametros/', include('arquitectura.urls')),
    path('facturacion/', include('creditos.urls')),
    path('cobranzas/', include('comprobantes.urls')),
    path('deudas/', include('op.urls_deudas')),
    path('pagos/', include('op.urls_pagos')),
    path('administracion/', include('contabilidad.urlsadmin')),
    path('contabilidad/', include('contabilidad.urls')),
    path('reportes/', include('reportes.urls')),
    path('resumenes/', include('resumenes.urls')),
    path('socio/', include(('socio.urls', 'socio'), namespace='socio')),
    path('superusuario/', include('consorcios.urls')),
    path('herramientas/', include('herramientas.urls')),
    path('api/', include('api.urls'))

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
