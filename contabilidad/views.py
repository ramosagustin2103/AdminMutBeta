from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from admincu.funciones import *
from consorcios.models import *
from arquitectura.models import *
from .models import *
from django_afip.models import *
from .forms import *
from .funciones import *


@group_required('contable')
def adm_index(request):
	return render(request, 'contabilidad/administracion.html', locals())


@group_required('contable')
def cont_index(request):
	try:
		ejercicio = Ejercicio.objects.get(consorcio=consorcio(request), activo=True)
	except:
		ejercicio = None

	if ejercicio:
		asientos = Asiento.objects.filter(
				consorcio=consorcio(request),
				fecha_asiento__range=[ejercicio.inicio, ejercicio.cierre]
			).order_by('fecha_asiento', 'id')

	return render(request, 'contabilidad/index.html', locals())



