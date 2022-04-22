from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from admincu.funciones import *
from .models import *
from .forms import *
from arquitectura.models import *
from django_afip import models
from django_afip.models import TaxPayer

@group_required('superusuario')
def cons_index(request):

	consorcios = Consorcio.objects.all().order_by('-id')[:5]

	return render(request, 'superusuario/consorcios/index.html', locals())


@group_required('superusuario')
def cons_registro(request):

	consorcios = Consorcio.objects.all()

	return render(request, 'superusuario/consorcios/registro.html', locals())


@group_required('superusuario')
def cons_nuevo_1(request, cont=None):
	try:
		cont = TaxPayer.objects.get(id=cont)
	except:
		cont = None

	form = contribuyenteForm(
			request.POST or None,
			request.FILES or None,
			instance=cont,

		)
	pregunta = "Seleccione las siguientes opciones"
	if form.is_valid():
		contribuyente = form.save()
		# models.populate_all()
		# contribuyente.fetch_points_of_sales()
		return redirect(cons_nuevo_2, contribuyente=contribuyente.id)
	else:
		messages.add_message(request, messages.ERROR, 'Debes rellenar todos los campos para poder continuar') if request.method == "POST" else None

	return render(request, 'superusuario/consorcios/nuevo.html', locals())

@group_required('superusuario')
def cons_nuevo_2(request, contribuyente):
	try:
		contribuyente = TaxPayer.objects.get(id=contribuyente)
	except:
		messages.add_message(request, messages.ERROR, 'Error, vuelva a intentar')
		return redirect(cons_index)

	form = consorcioForm(
			data=request.POST or None,
		)
	pregunta = "Seleccione las siguientes opciones"
	if form.is_valid():
		cons = form.save(commit=False)
		cons.contribuyente = contribuyente
		cons.save()
		return redirect(cons_nuevo_3, cons=cons.id)
	else:
		messages.add_message(request, messages.ERROR, 'Debes rellenar todos los campos para poder continuar') if request.method == "POST" else None

	return render(request, 'superusuario/consorcios/nuevo.html', locals())



@group_required('superusuario')
def cons_nuevo_3(request, cons):
	try:
		cons = Consorcio.objects.get(id=cons)
	except:
		return redirect(cons_index)

	form = ingForm(
			consorcio=cons,
			data=request.POST or None,
		)

	pregunta = "Seleccione las siguientes opciones"
	if form.is_valid():
		cons = form.save()
		return redirect(cons_index)
	else:
		messages.add_message(request, messages.ERROR, 'Debes rellenar todos los campos para poder continuar') if request.method == "POST" else None

	return render(request, 'superusuario/consorcios/nuevo.html', locals())


@group_required('superusuario')
def us_index(request):

	return render(request, 'superusuario/usuarios/index.html', locals())


@group_required('superusuario')
def us_registro(request):

	return render(request, 'superusuario/usuarios/registro.html', locals())


@group_required('superusuario')
def us_nuevo(request):

	return render(request, 'superusuario/usuarios/nuevo.html', locals())