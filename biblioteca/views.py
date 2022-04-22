# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import HttpResponse
from .models import *
from admincu.funciones import *
from .forms import *
from django.db import transaction
from django.db.models import Q


@login_required
def bib_index(request):

	categorias = Categoria.objects.filter(
				Q(consorcio=consorcio(request)) | Q(consorcio__isnull=True)
			).order_by('-consorcio')

	return render(request, "biblioteca/index.html", locals())


@group_required('administrativo', 'contable')
@transaction.atomic
def bib_nuevo(request, tipo, instance=None):
	if valid_demo(request.user):
		return redirect('biblioteca')

	nameForm = '{}Form'.format(tipo)
	try:
		form = eval(nameForm)(
			data=request.POST or None,
			files=request.FILES or None,
			consorcio=consorcio(request),
			)
	except :
		messages.add_message(request, messages.ERROR, "Hubo un error al intentar cargar objetos")
		return redirect('biblioteca')


	pregunta = 'Agregar {}'.format(tipo.lower())

	if form.is_valid():
		if tipo == 'Libro':
			formatos = ['pdf', 'doc', 'docx', 'jpg']
			nombre = str(request.FILES['ubicacion'])
			formato = nombre[::-1].split('.', 1)[0][::-1]
			categoria = form.cleaned_data['categoria']
			if formato in formatos:
				if (categoria.galeria and formato == "jpg") \
				or (not categoria.galeria and not formato == "jpg"):
					libro = form.save(commit=False)
					libro.consorcio = consorcio(request)
					libro.save()
					libro.compartido.add(*Group.objects.all())
					messages.add_message(request, messages.SUCCESS, "Documento subido con exito.")
					return redirect('biblioteca')
				else:
					messages.add_message(request, messages.ERROR, "No se permite el formato del archivo en la categoria seleccionada.")
			else:
				messages.add_message(request, messages.ERROR, "No se permite el formato del archivo que desea subir.")
		elif tipo == 'Categoria':
			categoria = form.save(commit=False)
			categoria.consorcio = consorcio(request)
			categoria.icono = 'fa fa-bank'
			categoria.save()
			categoria.compartido.add(*Group.objects.all())
			messages.add_message(request, messages.SUCCESS, "Categoria agregada con exito.")
			return redirect('biblioteca')

	return render(request, "biblioteca/nuevo.html", locals())

@group_required('administrativo', 'contable')
@transaction.atomic
def bib_eliminar(request, tipo, instance):
	try:
		objeto = eval(tipo).objects.get(consorcio=consorcio(request), slug=instance)
	except:
		messages.add_message(request, messages.ERROR, "Hubo un error al intentar eliminar el objeto")
		return redirect('biblioteca')

	if tipo == 'Categoria':
		Libro.objects.filter(categoria=objeto).delete()

	objeto.delete()
	mensaje = "{} eliminado con exito".format(tipo)
	messages.add_message(request, messages.SUCCESS, mensaje)

	return redirect('biblioteca')


@login_required
def bib_descargar(request, slug):
	try:
		archivo = Libro.objects.get(slug=slug)
	except:
		messages.add_message(request, messages.ERROR, "No se encontro el archivo que desea descargar")
		return redirect('biblioteca')

	if request.user.groups.all()[0] in archivo.compartido.all():
		response = HttpResponse(archivo.ubicacion, content_type='application/force-download')
		content = "attachment; filename={}".format(archivo.slug)
		response['Content-Disposition'] = content
		return response
	else:
		messages.add_message(request, messages.ERROR, "No se encontro el archivo que desea descargar")
		return redirect('biblioteca')