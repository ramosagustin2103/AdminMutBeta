from django.contrib import admin
from .models import *
from .manager import *
from django.contrib import messages

admin.site.register(Reporte)
admin.site.register(Subtotal)

def hacer_pdfs(modeladmin, request, queryset):
	for cierre in queryset:
		statics = request.build_absolute_uri()
		resultadosManager = ResultadosManager(cierre)
		resultadosManager.hacer_pdf(statics)
		cierreManager = CierreManager(cierre)
		cierreManager.hacer_pdf(statics)
		messages.add_message(request, messages.SUCCESS, "PDFS realizados con exito.")

hacer_pdfs.short_description = "Hacer pdfs de reportes"

class CierreAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	actions = [hacer_pdfs]

admin.site.register(Cierre, CierreAdmin)
