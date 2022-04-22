from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User
from .models import *
from contabilidad.models import *


admin.site.register(Tipo_Ocupante)
admin.site.register(Tipo_CU)
admin.site.register(Codigo_Provincia)


def cargar_plan(modeladmin, request, queryset):
	for consorcio in queryset:
		try:
			plan = Plan.objects.get(consorcio=consorcio)
		except:
			plan = None
		if not plan:
			plan = Plan(
				consorcio=consorcio,
			)
			plan.save()
			plan.cuentas.add(*Cuenta.objects.filter(consorcio__isnull=True))
			messages.add_message(request, messages.SUCCESS, "Plan cargado con exito.")

cargar_plan.short_description = "Cargar plan de cuentas basico"


def agregar_usuarios(modeladmin, request, queryset):
	for consorcio in queryset:
		prefijo = "{}.".format(consorcio.abreviatura)
		consorcio.usuarios.add(*User.objects.filter(username__icontains=prefijo))
		messages.add_message(request, messages.SUCCESS, "Usuarios cargados con exito.")

agregar_usuarios.short_description = "Agregar usuarios con la abreviatura del consorcio"



class ConsorcioAdmin(admin.ModelAdmin):
	actions = [cargar_plan, agregar_usuarios]

admin.site.register(Consorcio, ConsorcioAdmin)
