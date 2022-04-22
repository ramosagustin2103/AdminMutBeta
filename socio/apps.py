from django.apps import AppConfig


class SocioConfig(AppConfig):
	name = 'socio'


	def ready(self):
		# signals are imported, so that they are defined and can be used
		from . import signals