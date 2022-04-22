from django.contrib import admin
from .models import *

class PagoAdmin(admin.ModelAdmin):
	list_display = ['__str__']

admin.site.register(Pago, PagoAdmin)
