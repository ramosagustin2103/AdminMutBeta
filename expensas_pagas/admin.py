from django.contrib import admin
from .models import *
from import_export.admin import ImportExportMixin


def hacer_pdf(modeladmin, request, queryset):

    for d in queryset:
        d.hacer_pdf()

hacer_pdf.short_description = "Hacer PDF del cupon"


def enviar_mail(modeladmin, request, queryset):

    for d in queryset:
        d.enviar_mail()

enviar_mail.short_description = "Enviar mail del cupon"





class DocumentoExpAdmin(ImportExportMixin, admin.ModelAdmin):
	actions = [
		hacer_pdf,
		enviar_mail
	]

class CobroExpAdmin(ImportExportMixin, admin.ModelAdmin):
	list_filter = ['codigo_consorcio']

admin.site.register(DocumentoExp, DocumentoExpAdmin)
admin.site.register(ClienteExp)
admin.site.register(CobroExp,CobroExpAdmin)