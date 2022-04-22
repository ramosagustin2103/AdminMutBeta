from django.contrib import admin
from import_export.resources import ModelResource
from import_export.admin import ImportExportMixin
from django.contrib import messages
import PyPDF2
from .models import *
import re


def buscar_caja_pdf(modeladmin, request, queryset):
	texto_buscado = 'CAJA ANA'
	texto_buscado_secundario = 'CAJA TERESA'
	tr_mutuas = []
	tr_a_revisar = []
	tr_como_destino = []
	for tr in queryset:
		pdf_tr = tr.pdf.path
		fichero_pdf = open(pdf_tr, 'rb')
		pdf_leido = PyPDF2.PdfFileReader(fichero_pdf)
		pagina = pdf_leido.getPage(0)
		contenido_pagina = pagina.extractText()
		if texto_buscado in contenido_pagina:
			if not texto_buscado_secundario in contenido_pagina:			
				operaciones = tr.asiento.operaciones.all()
				debe = haber = 0
				for operacion in operaciones:
					debe = debe + operacion.debe
					haber = haber + operacion.haber
				if debe > haber:
					diferencia = debe - haber #si debe es mayor a haber entonces origen es texto buscado y viceversa 
					c = 'Caja destino:'
					ubicacion1 = contenido_pagina.index(c) + len(c)
					t = contenido_pagina[ubicacion1:]
					e = re.sub('- PRADERAS DE SAN LORENZO',"", t).strip()
					y = re.sub(r'[0-9,]+', '', e)
					f = 'id-' + str(tr.consorcio)+ '-' + str(tr.fecha) + '-' + str(tr.id) + '-origen- ' + str(y) + '-' + str(diferencia)
					messages.add_message(request, messages.SUCCESS, f)
				if haber > debe:
					diferencia = haber - debe 
					f = str(tr.id) + "-valor:" + str(diferencia)
					tr_como_destino.append(f)
				if debe == haber:
					tr_a_revisar.append(tr.numero)
			else:
				tr_mutuas.append(tr.numero)
    					
	messages.add_message(request, messages.SUCCESS, "las transferencias mutuas son :  {}    las a revisar:  {}    las que tienen su caja como destino son.   {}".format(str(tr_mutuas), str(tr_a_revisar), str(tr_como_destino)))



def buscar_asiento_desbalanceado(modeladmin, request, queryset):
	trs = []
	for tr in queryset:
		debe = haber = 0
		for operacion in tr.asiento.operaciones.all():
			debe = debe + operacion.debe
			haber = haber + operacion.haber
		if debe != haber:
			trs.append[tr.id]
	messages.add_message(request, messages.SUCCESS, "transferencias desbalanceadas   ids:{}".format(str(trs)))


class BienvenidaResource(ModelResource):

    class Meta:
        model = Bienvenida

def enviar_bienvenida(modeladmin, request, queryset):
	for bienvenida in queryset:
		bienvenida.enviar()

	messages.add_message(request, messages.SUCCESS, "Enviado con exito.")

enviar_bienvenida.short_description = "Enviar mail de bienvenida"

class BienvenidaAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__']
	actions = [enviar_bienvenida]
	resource_class = BienvenidaResource

admin.site.register(Bienvenida, BienvenidaAdmin)


class CajaTransferenciaInline(admin.TabularInline):
	model = CajaTransferencia

class TransferenciaAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	actions = [buscar_caja_pdf, buscar_asiento_desbalanceado]
	inlines = [
		CajaTransferenciaInline,
	]

admin.site.register(Transferencia, TransferenciaAdmin)


class CajaTransferenciaResource(ModelResource):

    class Meta:
        model = CajaTransferencia


class CajaTransferenciaAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	resource_class = CajaTransferenciaResource

admin.site.register(CajaTransferencia, CajaTransferenciaAdmin)