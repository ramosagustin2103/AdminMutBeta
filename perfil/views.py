from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from arquitectura.models import Socio, Dominio
from .forms import *
from admincu.funciones import *


# Create your views here.
@login_required
def perfil_index(request):
	try:
		socio = Socio.objects.get(usuarios=request.user)
		dominios = Dominio.objects.filter(socio=socio)
	except:
		socio = None

	return render(request, "perfil/index.html", locals())

@login_required
def perfil_edicion(request):
	if valid_demo(request.user):
		return redirect(perfil_index)
	form = userForm(
			data=request.POST or None,
			instance=request.user,
		)
	if form.is_valid():
		guardar = form.save()
		messages.add_message(request, messages.SUCCESS, "Informacion actualizada con exito")
		return redirect(perfil_index)

	pregunta = "Opciones permitidas"

	return render(request, "perfil/edicion.html", locals())

@login_required
def perfil_pass(request):
	if valid_demo(request.user):
		return redirect(perfil_index)
	form = PasswordChangeForm(request.user,	request.POST or None)
	if form.is_valid():
		guardar = form.save()
		update_session_auth_hash(request, request.user)
		messages.add_message(request, messages.SUCCESS, "Password modificada con exito")
		return redirect(perfil_index)
	else:
		if request.method == "POST":
			mensaje = 'Hubo un error al intentar modificar su password. Por favor, lea las indicaciones.'
			messages.add_message(request, messages.ERROR, )

	pregunta = "Ingrese los siguientes datos"

	
	return render(request, "perfil/edicion.html", locals())

