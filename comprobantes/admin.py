from django.urls import reverse
from django.contrib import admin
from django.contrib import messages
from import_export.resources import ModelResource
from import_export.admin import ImportExportMixin
from datetime import date

from .models import *
from admincu.funciones import armar_link
from .funciones import asiento_diario

import PyPDF2
import re
'''
			operaciones = r.asiento.operaciones.all()
			debe = haber = 0
			for operacion in operaciones:
				debe = debe + operacion.debe
				haber = haber + operacion.haber
				diferencia = haber - debe #para el caso de los recibo funciona asi porque el faltante debe darse en el debe
				f = str(r.numero) + "," + str(r.fecha) + ":" + str(diferencia)
			if diferencia == 0:
				r_a_revisar.append(r.numero)
			else:
				numeros_recibos_y_diferencia.append(f)
'''


def buscar_caja_pdf(modeladmin, request, queryset):
	'''se deben seleccionar recibos de la misma fecha para que el valor suma funcione correctamente'''
	texto_buscado = 'CAJA TERESA'
	for r in queryset:
		pdf_op = r.pdf.path
		fichero_pdf = open(pdf_op, 'rb')
		pdf_leido = PyPDF2.PdfFileReader(fichero_pdf)
		pagina = pdf_leido.getPage(0)
		contenido_pagina = pagina.extractText()
		if texto_buscado in contenido_pagina:
			d = 'Total'
			ubicacion1 = contenido_pagina.index(texto_buscado) + len(texto_buscado)
			ubicacion2 = contenido_pagina.index(d)
			t = contenido_pagina[ubicacion1:ubicacion2]
			n = re.sub("[^0-9,]", "", t)
			l = float(n.replace(',','.'))
			if l < 200000:
				f = str(r.id) + " - " + str(r.consorcio.id) + " - " + str(r.socio.id) + " - " + str(r.fecha) + " - " + str(r.id) + " - " + str(l)
				messages.add_message(request, messages.SUCCESS, f)
			else:
				f = str(r.numero) + "," + str(r.fecha) + ":" + str(l)
				messages.add_message(request, messages.SUCCESS, "Revisar: {}".format(f))
	

buscar_caja_pdf.short_description = "buscar caja"



def hacer_pdf(modeladmin, request, queryset):
	for comprobante in queryset:
		comprobante.hacer_pdfs()
		messages.add_message(request, messages.SUCCESS, "Hecho.")
hacer_pdf.short_description = "Hacer PDF"

def reenviar_mail(modeladmin, request, queryset):
	for comprobante in queryset:
		comprobante.enviar_mail()
		messages.add_message(request, messages.SUCCESS, "Mail enviado con exito.")
reenviar_mail.short_description = "Enviar mail de este comprobante"

def hacer_asiento_diario(modeladmin, request, queryset):
	dia = date.today()
	for comprobante in queryset:
		if comprobante.fecha != dia:
			dia = comprobante.fecha
			consorcio = comprobante.consorcio
			comprobantes_dia = Comprobante.objects.filter(consorcio=consorcio, fecha=dia)
			asiento = Asiento.objects.filter(
				comprobante_original__in=comprobantes_dia
			).distinct().first()
			if asiento:
				asiento.delete()
			asiento_diario(dia, consorcio, comprobantes_dia)
			comprobantes_dia = Comprobante.objects.filter(consorcio=consorcio, fecha=dia)
			messages.success(request, 'Asiento CREADO con exito.')

'''
	else:
		comprobante = queryset.first()
		dia = comprobante.fecha
		hoy = date.today()
		if dia == hoy:
			messages.error(request, 'El comprobante seleccionado es de hoy.')
		else:
			consorcio = comprobante.consorcio
			comprobantes_dia_con_asiento = Comprobante.objects.filter(consorcio=consorcio, fecha=dia, asiento__isnull=False)
			asiento = Asiento.objects.filter(
				comprobante_original__in=comprobantes_dia_con_asiento
			).distinct().first()
			comprobantes_dia = Comprobante.objects.filter(consorcio=consorcio, fecha=dia)
			if asiento:
				if len(asiento.comprobante_original.all()) != len(comprobantes_dia):
					asiento.delete()
					asiento_diario(dia, consorcio, comprobantes_dia)
					messages.success(request, 'Asiento RECREADO con exito.')
				else:
					messages.error(request, 'Todos los comprobantes de ese dia ya tenian asiento.')
			else:
				asiento_diario(dia, consorcio, comprobantes_dia)
'''


hacer_asiento_diario.short_description = "Hacer asiento diario"


class CobroInline(admin.TabularInline):
	model = Cobro

class CajaComprobanteInline(admin.TabularInline):
	model = CajaComprobante

class SaldosUtilizadosInlineComprobante(admin.TabularInline):
	model = Saldo
	fk_name = 'comprobante_destino'

class SaldosUtilizadosInlineCompensacion(admin.TabularInline):
	model = Saldo
	fk_name = 'compensacion_destino'

class SaldoNuevoInline(admin.TabularInline):
	model = Saldo
	fk_name = 'comprobante_origen'

class ComprobanteAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	actions = [
		reenviar_mail,
		hacer_asiento_diario,
		buscar_caja_pdf
	]
	inlines = [
		CobroInline,
		CajaComprobanteInline,
		SaldosUtilizadosInlineComprobante,
		SaldoNuevoInline
	]

class CompensacionAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	inlines = [
		CobroInline,
		SaldosUtilizadosInlineCompensacion,
	]


def consultar_preference(modeladmin, request, queryset):
	from datetime import date, timedelta
	for cobro in queryset:
		hoy = date.today()
		fecha_anterior = hoy - timedelta(days=60)
		cobro.preference.poll_status()
		if cobro.preference.paid == False and cobro.fecha < fecha_anterior:
			cobro.preference.delete()
		messages.add_message(request, messages.SUCCESS, "Hecho.")

consultar_preference.short_description = "Hacer poll status a cobro"

class CobroAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	actions = [
		consultar_preference
	]



admin.site.register(Comprobante, ComprobanteAdmin)
admin.site.register(Compensacion, CompensacionAdmin)
admin.site.register(Cobro, CobroAdmin)

class SaldoResource(ModelResource):

	class Meta:
		model = Saldo


class SaldoAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	resource_class = SaldoResource

admin.site.register(Saldo, SaldoAdmin)

class CajaComprobanteAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__']

admin.site.register(CajaComprobante, CajaComprobanteAdmin)