from import_export.resources import ModelResource
from import_export.admin import ImportExportMixin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib import admin
from .models import *

class UserResource(ModelResource):
	def after_save_instance(self, instance, using_transactions, dry_run):
		instance.set_password(instance.username)
		instance.save()

	class Meta:
		model = User


class UserAdmin(ImportExportMixin, UserAdmin):
	resource_class = UserResource

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

class SocioResource(ModelResource):

    class Meta:
        model = Socio

    def for_delete(self, row, instance):
        return self.fields['nombre'].clean(row) == ''


def codigo(modeladmin, request, queryset):
	for socio in queryset:
		socio.generar_codigo()

	messages.add_message(request, messages.SUCCESS, "Hecho.")

codigo.short_description = "Generar codigo de creacion a Socio"

class SocioAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	ordering = ['-nombre']
	actions = [codigo]
	resource_class = SocioResource

admin.site.register(Socio, SocioAdmin)

class DominioResource(ModelResource):

    class Meta:
        model = Dominio

    def for_delete(self, row, instance):
        return self.fields['numero'].clean(row) == ''

class DominioAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']
	ordering = ['-numero']
	resource_class = DominioResource


admin.site.register(Dominio, DominioAdmin)

class CajaAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']

class IngresoAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']

class GastoAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']

class AcreedorAdmin(ImportExportMixin, admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']

class GrupoAdmin(admin.ModelAdmin):
	list_display = ['__str__', 'consorcio']
	list_filter = ['consorcio']


admin.site.register(Acreedor, AcreedorAdmin)
admin.site.register(Caja, CajaAdmin)
admin.site.register(Gasto, GastoAdmin)
admin.site.register(Ingreso, IngresoAdmin)
admin.site.register(Grupo, GrupoAdmin)
admin.site.register(Relacion)
admin.site.register(Accesorio)


