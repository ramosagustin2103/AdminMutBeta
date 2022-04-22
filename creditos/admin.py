from django.contrib import admin
from django.contrib import messages
from .models import *
from django.urls import reverse
from admincu.funciones import armar_link
from import_export.resources import ModelResource
from import_export.admin import ImportExportMixin
from expensas_pagas.models import DocumentoExp
from expensas_pagas.manager import *


def cobro_exp(modeladmin, request, queryset):
	e = NewExp()
	d = e.cobros_exp()
	messages.success(request, d)

cobro_exp.short_description = "cobro_exp"





def inf_deuda_2(modeladmin, request, queryset):
	liquidacion = queryset.first()
	e = NewExp()
	queryset = Factura.objects.filter(liquidacion=liquidacion)
	e.codigo_cliente = liquidacion.consorcio.exp.first().codigo_exp
	d = e.inf_deuda_generator(queryset)

	messages.success(request, d)

inf_deuda_2.short_description = "inf_deuda_2"



def obtener_ses_exp(modeladmin, request, queryset):
	e = NewExp()
	d= e.StartSesion()
	messages.success(request, d)

obtener_ses_exp.short_description = "start_sesion"
	

def obtener_barcode_exp(modeladmin, request, queryset):
	e = NewExp()
	d= e.request_generator(c=queryset.first(), dato_solicitado ='barcode' )
	messages.success(request, d)

obtener_barcode_exp.short_description = "barcode"
	

def obtener_codigo_exp(modeladmin, request, queryset):
	e = NewExp()
	d= e.request_generator(c=queryset.first(), dato_solicitado ='codigo' )
	messages.success(request, d)

obtener_codigo_exp.short_description = "codigo"
	

def obtener_cupon(modeladmin, request, queryset):
	e = NewExp()
	for c in queryset:
		d= e.cupon_creator(c)
		messages.success(request, d)

obtener_cupon.short_description = "cupon"
	

def obtener_informe_deuda(modeladmin, request, queryset):
	e = NewExp()
	d= e.request_inf_deuda()
	messages.success(request, d)

obtener_informe_deuda.short_description = "informe deuda"
	


def obtener_barcode_exp_liquidacion(modeladmin, request, queryset):
	for liquidacion in queryset:
		for factura in liquidacion.factura_set.all():
			e = NewExp()
			d= e.request_generator(c=factura, dato_solicitado ='barcode' )
			print(d)
			messages.success(request, d)

obtener_barcode_exp_liquidacion.short_description = "barcode_liquidacion"



def procesar_liquidacion(modeladmin, request, queryset):
	for liquidacion in queryset:
		if liquidacion.estado == "en_proceso":
			for factura in liquidacion.factura_set.filter(receipt__receipt_number__isnull=True):
				creditos = factura.incorporar_creditos()

				factura.validar_factura()

			liquidacion.confirmar()
			messages.success(request, "Liquidacion procesada")
		else:
			messages.success(request, "La liquidacion no estaba en proceso")

procesar_liquidacion.short_description = "Procesar liquidacion"


def procesar_liquidacion_exp(modeladmin, request, queryset):
	for liquidacion in queryset:
		for d in liquidacion.factura_set.all():
			Exp().barcode(d)
			d.exp.first().hacer_pdf()
			messages.success(request, 'hecho')

procesar_liquidacion_exp.short_description = "Procesar exp"


def eliminar_cupon_exp(modeladmin, request, queryset):
	for liquidacion in queryset:
		for d in liquidacion.factura_set.all():
			d.exp.first().delete()
			messages.success(request, 'hecho')

eliminar_cupon_exp.short_description = "eliminar cupon exp"

def procesar_facturas_exp(modeladmin, request, queryset):
		for d in queryset:
			Exp().barcode(d)
			d.exp.first().hacer_pdf()
			messages.success(request, 'hecho')

procesar_facturas_exp.short_description = "Procesar exp"

def enviar_mail_liquidacion(modeladmin, request, queryset):
	for liquidacion in queryset: 
		for factura in liquidacion.factura_set.all():
			factura.enviar_mail()
			messages.success(request, 'Enviado')

enviar_mail_liquidacion.short_description = "Enviar mail de esta liquidacion"


def enviar_mail_factura(modeladmin, request, queryset):
	for factura in queryset:
		factura.enviar_mail()
		messages.success(request, 'Enviado')

enviar_mail_factura.short_description = "Enviar mail de esta factura"



def hacer_pdf_factura(modeladmin, request, queryset):
	for factura in queryset:
		factura.hacer_pdf()
		messages.success(request, 'hecho')

hacer_pdf_factura.short_description = "hacer pdf de esta factura"



class FacturaAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	actions = [enviar_mail_factura, procesar_facturas_exp, obtener_barcode_exp, obtener_codigo_exp, obtener_ses_exp, obtener_informe_deuda, obtener_cupon, hacer_pdf_factura, cobro_exp]

admin.site.register(Factura, FacturaAdmin)


class LiquidacionAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	actions = [procesar_liquidacion, procesar_liquidacion_exp, enviar_mail_liquidacion, eliminar_cupon_exp, obtener_barcode_exp_liquidacion, inf_deuda_2]

admin.site.register(Liquidacion, LiquidacionAdmin)


class CreditoResource(ModelResource):

	class Meta:
		model = Credito


class CreditoAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	resource_class = CreditoResource

admin.site.register(Credito, CreditoAdmin)