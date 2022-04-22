from django.contrib import admin
from import_export.admin import ImportExportMixin
from .models import *
from django.contrib import messages
from contabilidad.asientos.funciones import asiento_deuda, asiento_op
import PyPDF2



def buscar_caja_pdf(modeladmin, request, queryset):
	texto_buscado = 'CAJA TERESA'
	numeros_ops_y_diferencia = []
	ops_a_revisar = []
	for op in queryset:
		pdf_op = op.pdf.path
		fichero_pdf = open(pdf_op, 'rb')
		pdf_leido = PyPDF2.PdfFileReader(fichero_pdf)
		pagina = pdf_leido.getPage(0)
		contenido_pagina = pagina.extractText()
		if texto_buscado in contenido_pagina:			
			operaciones = op.asiento.operaciones.all()
			debe = haber = 0
			for operacion in operaciones:
				debe = debe + operacion.debe
				haber = haber + operacion.haber
				diferencia = debe - haber #para el caso de las ops funciona asi porque el faltante debe darse en el haber
				f = str(op.id) + " - " + str(op.fecha_operacion) + " - " + str(diferencia)
			if diferencia == 0:
				ops_a_revisar.append(op.numero)
				messages.add_message(request, messages.SUCCESS, "Revisar: {}".format(op.id))
			else:
				numeros_ops_y_diferencia.append(f)
				messages.add_message(request, messages.SUCCESS, f)

	# messages.add_message(request, messages.SUCCESS, "las ops buscadas son {}.    Revisar: {}".format(str(numeros_ops_y_diferencia),str(ops_a_revisar)))

buscar_caja_pdf.short_description = "buscar caja"



def rehacer_asiento_deuda(modeladmin, request, queryset):
	asientos_nuevos = 0
	for deuda in queryset:
		if deuda.asiento:
			deuda.asiento.delete()
			asiento = asiento_deuda(deuda)
			asientos_nuevos += 1
	messages.add_message(request, messages.SUCCESS, "Se regeneraron {} asientos nuevos.".format(str(asientos_nuevos)))

rehacer_asiento_deuda.short_description = "Rehacer asiento"

def hacer_pdf_op(modeladmin, request, queryset):
	for op in queryset:
		op.hacer_pdf()
		messages.add_message(request, messages.SUCCESS, "Hecho.")
hacer_pdf_op.short_description = "Hacer PDF"

class GastoDeudaInline(admin.TabularInline):
	model = GastoDeuda


class DeudaAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	inlines = [GastoDeudaInline]
	actions = [rehacer_asiento_deuda]

class GastoOPInline(admin.TabularInline):
	model = GastoOP

class DeudaOPInline(admin.TabularInline):
	model = DeudaOP

class RetencionOPInline(admin.TabularInline):
	model = RetencionOP

class CajaOPInline(admin.TabularInline):
	model = CajaOP

def rehacer_asiento_op(modeladmin, request, queryset):
	asientos_nuevos = 0
	for op in queryset:
		if op.asiento:
			op.asiento.delete()
			fecha_operacion = op.fecha_operacion or op.fecha
			asiento = asiento_op(op, op.gastoop_set.all(), op.deudaop_set.all(), op.retencionop_set.all(), op.cajaop_set.all())
			asientos_nuevos += 1
	messages.add_message(request, messages.SUCCESS, "Se regeneraron {} asientos nuevos.".format(str(asientos_nuevos)))

rehacer_asiento_op.short_description = "Rehacer asiento"


class OPAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	inlines = [
		GastoOPInline,
		DeudaOPInline,
		RetencionOPInline,
		CajaOPInline,
	]
	actions = [rehacer_asiento_op, hacer_pdf_op, buscar_caja_pdf]

admin.site.register(Deuda, DeudaAdmin)
admin.site.register(OP, OPAdmin)



class GastoAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__']


class CajaOPAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__']


admin.site.register(GastoDeuda, GastoAdmin)
admin.site.register(GastoOP, GastoAdmin)
admin.site.register(CajaOP, CajaOPAdmin)