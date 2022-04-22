from django.contrib import admin
from .models import *
from django.contrib import messages
from import_export.admin import ImportExportMixin

class AsientoAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
admin.site.register(Asiento, AsientoAdmin)

def imprimir_saldo(modeladmin, request, queryset):
	for cuenta in queryset:
		ejercicio = Ejercicio.objects.get(id=2)
		fecha_fin = "2018-05-28"
		saldo = cuenta.saldo(ejercicio=ejercicio, fecha_fin=fecha_fin)
		messages.add_message(request, messages.SUCCESS, "Saldo: {}.".format(saldo))

imprimir_saldo.short_description = "Imprimir saldo"
class CuentaAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	actions = [imprimir_saldo]

admin.site.register(Cuenta, CuentaAdmin)

admin.site.register(Plan)
admin.site.register(Ejercicio)