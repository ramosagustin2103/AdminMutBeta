from datetime import date, timedelta
from contabilidad.models import *
from django.db import transaction
from django.template.loader import render_to_string
from weasyprint import HTML
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.db.models import Q

from creditos.models import Credito
from .models import *

class Logo:

	def logo_as_data_uri(self):

		"""Logo del auditor."""

		import base64
		import os
		if self.cierre.logo_auditor:

			_, ext = os.path.splitext(self.cierre.logo_auditor.file.name)
			with open(self.cierre.logo_auditor.file.name, 'rb') as f:
				data = base64.b64encode(f.read())

			return 'data:image/{};base64,{}'.format(
				ext[1:],  # Remove the leading dot.
				data.decode()
			)
		return

class CierreManager(Logo):

	""" Manager para ver o procesar """

	def __init__(
			self,
			cierre, # Objeto tipo cierre, tiene todo lo necesario para trabajar
		):
		self.cierre = cierre
		self.fecha_fin = cierre.periodo
		self.consorcio = cierre.consorcio
		self.cuentas = Plan.objects.get(consorcio=self.consorcio).cuentas.filter(nivel=4)
		self.ejercicio = Ejercicio.objects.get(consorcio=self.consorcio, activo=True)

		self.anteriores = Cierre.objects.filter(consorcio=self.consorcio, confirmado=True, periodo__lt=self.fecha_fin).order_by('-periodo')[:5]
		if self.anteriores:
			self.fecha_inicio = self.anteriores.first().periodo + timedelta(days=1)
		else:
			self.fecha_inicio = self.ejercicio.inicio


	def sumar(self, subtotales):

		""" Hace Totales """

		return sum([s.total for s in subtotales])

	def hacer_activo(self):

		""" Retorna objetos de tipo Subtotal """

		if self.cierre.confirmado:
			return self.cierre.subtotales.filter(cuenta__numero__range=[100000,199999]).order_by('cuenta__numero')

		cuentas_activo = self.cuentas.filter(numero__range=[100000,199999]).order_by('numero')
		subtotales = []
		suma = 0
		for c in cuentas_activo:
			suma = c.saldo(ejercicio=self.ejercicio, fecha_fin=self.fecha_fin)
			if c.numero == "112101" and self.anteriores:
				# Filtrar los creditos impagos a la fecha de cierre de periodo y consultar brutos
				# Filtro base
				filtro = {
					'consorcio': self.consorcio,
					'periodo__range': [self.fecha_inicio, self.fecha_fin],
					'fecha__range': [self.fecha_inicio, self.fecha_fin],
				}
				# Agregar impagos a la fecha de hoy
				filtro_impagos = filtro.copy()
				filtro_impagos.update({'fin__isnull': True})

				# Agregar impagos a la fecha del cierre
				filtro_post_pagos = filtro.copy()
				filtro_post_pagos.update({'fin__gt': self.fecha_fin})


				creditos = Credito.objects.filter(
						Q(**filtro_impagos) | Q(**filtro_post_pagos)
					)
				saldo_mensuales = sum([c.bruto for c in creditos])
				# operaciones = c.operaciones(ejercicio=self.ejercicio, fecha_inicio=self.fecha_inicio, fecha_fin=self.fecha_fin)
				# saldo_debe = c.saldo_debe(operaciones) # Lo que esta en el debe son los aumentos de esta cuenta en el mes


				subtotales.append(Subtotal(
					cierre=self.cierre,
					cuenta=Cuenta.objects.get(numero=112101),
					total=saldo_mensuales
				))
				subtotales.append(Subtotal(
					cierre=self.cierre,
					cuenta=Cuenta.objects.get(numero=112102),
					total=suma - saldo_mensuales
				))
			else:
				subtotales.append(Subtotal(
					cierre=self.cierre,
					cuenta=c,
					total=suma
				))
		return subtotales

	def hacer_pasivo(self):

		""" Retorna objetos de tipo Subtotal """

		if self.cierre.confirmado:
			return self.cierre.subtotales.filter(cuenta__numero__range=[2000000,299999]).order_by('cuenta__numero')

		cuentas_pasivo = self.cuentas.filter(numero__range=[2000000,299999]).order_by('numero')
		subtotales = []
		for c in cuentas_pasivo:
			subtotales.append(Subtotal(
				cierre=self.cierre,
				cuenta=c,
				total=c.saldo(ejercicio=self.ejercicio, fecha_fin=self.fecha_fin)
			))
		return subtotales

	def hacer_resultados_positivos(self, total=False):

		""" Retorna objetos de tipo Subtotal """


		if self.cierre.confirmado:
			return self.cierre.subtotales.filter(cuenta__numero__range=[400000,499999]).order_by('cuenta__numero')

		cuentas_resultados_positivos = self.cuentas.filter(numero__range=[400000,499999]).order_by('numero')
		subtotales = []
		for c in cuentas_resultados_positivos:
			if total:
				valor = c.saldo(ejercicio=self.ejercicio, fecha_fin=self.fecha_fin)
			else:
				valor = c.saldo(ejercicio=self.ejercicio, fecha_inicio=self.fecha_inicio, fecha_fin=self.fecha_fin)
			subtotales.append(Subtotal(
				cierre=self.cierre,
				cuenta=c,
				total=valor
			))
		return subtotales

	def hacer_resultados_negativos(self, total=False):

		""" Retorna objetos de tipo Subtotal """


		if self.cierre.confirmado:
			return self.cierre.subtotales.filter(cuenta__numero__gte=500000).order_by('cuenta__numero')

		cuentas_resultados_negativos = self.cuentas.filter(numero__gte=500000).order_by('numero')
		subtotales = []
		for c in cuentas_resultados_negativos:
			if total:
				valor = c.saldo(ejercicio=self.ejercicio, fecha_fin=self.fecha_fin)
			else:
				valor = c.saldo(ejercicio=self.ejercicio, fecha_inicio=self.fecha_inicio, fecha_fin=self.fecha_fin)
			subtotales.append(Subtotal(
				cierre=self.cierre,
				cuenta=c,
				total=-valor
			))
		return subtotales

	def hacer_patrimonio(self):

		""" Retorna objetos de tipo Subtotal """

		if self.cierre.confirmado:
			return self.cierre.subtotales.filter(cuenta__numero__range=[300000,399999]).order_by('cuenta__numero')

		cuentas_patrimonio = self.cuentas.filter(numero__range=[300000,399999]).order_by('numero')
		subtotales = []
		for c in cuentas_patrimonio:
			total = c.saldo(ejercicio=self.ejercicio, fecha_fin=self.fecha_fin)
			if c.numero == "321001":
				total += sum([s.total for s in self.hacer_resultados_positivos(total=True)])
				total += sum([s.total for s in self.hacer_resultados_negativos(total=True)])
			subtotales.append(Subtotal(
				cierre=self.cierre,
				cuenta=c,
				total=total
			))
		return subtotales

	def hacer_pdf(self, statics):

		cierre = self.cierre
		logo_auditor = self.logo_as_data_uri()
		subtotales_activo = self.hacer_activo()
		suma_activo = self.sumar(subtotales_activo)
		subtotales_pasivo = self.hacer_pasivo()
		suma_pasivo = self.sumar(subtotales_pasivo)
		subtotales_patrimonio = self.hacer_patrimonio()
		suma_patrimonio = self.sumar(subtotales_patrimonio)
		suma_pasivo_patrimonio = suma_pasivo + suma_patrimonio

		# Generacion del PDF de Sit Pat
		html_string_sit_pat = render_to_string('reportes/pdfs/situacion-patrimonial.html', locals())
		html_sit_pat = HTML(string=html_string_sit_pat, base_url=statics)

		ruta = "{}_sit_pat_{}.pdf".format(
			self.consorcio.abreviatura,
			str(cierre.periodo)
			)
		pdf = html_sit_pat.write_pdf()

		# Cargar estado de Sit Pat
		reporte = Reporte(
				consorcio=self.consorcio,
				cierre=cierre,
				nombre="Situacion Patrimonial al {}/{}/{}.pdf".format(str(cierre.periodo.day), str(cierre.periodo.month), str(cierre.periodo.year)),
				automatico=True
			)
		reporte.ubicacion = SimpleUploadedFile(ruta, pdf, content_type='application/pdf')
		reporte.save()

	@transaction.atomic
	def guardar(self, statics):

		""" Guarda el estado de situacion patrimonial y los subtotales patrimoniales """

		cierre = self.cierre

		self.hacer_pdf(statics)

		subtotales_activo = self.hacer_activo()
		subtotales_pasivo = self.hacer_pasivo()
		subtotales_patrimonio = self.hacer_patrimonio()

		Subtotal.objects.bulk_create(subtotales_activo)
		Subtotal.objects.bulk_create(subtotales_pasivo)
		Subtotal.objects.bulk_create(subtotales_patrimonio)

		cierre.confirmado = True
		cierre.mails = True
		cierre.save()

class ResultadosManager(Logo):


	def __init__(
			self,
			cierre, # Objeto tipo cierre, tiene todo lo necesario para trabajar
		):


		self.cierre = cierre
		self.fecha_fin = cierre.periodo
		self.consorcio = cierre.consorcio
		self.cuentas = Plan.objects.get(consorcio=self.consorcio).cuentas.filter(nivel=4)
		self.ejercicio = Ejercicio.objects.get(consorcio=self.consorcio, activo=True)

		cierres_anteriores = Cierre.objects.filter(consorcio=self.consorcio, confirmado=True, periodo__lt=self.fecha_fin).order_by('-periodo')[:5]
		anteriores_id = [c.id for c in cierres_anteriores]
		self.anteriores = Cierre.objects.filter(id__in=anteriores_id).order_by('periodo')
		if self.anteriores:
			self.fecha_inicio = self.anteriores.first().periodo + timedelta(days=1)
		else:
			self.fecha_inicio = self.fecha_fin.replace(day=1)

	def hacer_columnas(self):

		""" Crea las columnas de la tabla """

		columnas = [a.periodo for a in self.anteriores]
		columnas.append(self.fecha_fin)
		return columnas

	def hacer_filas_resultados(self):

		""" Crea la tabla """

		cuentas = {
			cuenta: [] for cuenta in self.cuentas.filter(numero__range=[400000, 499999]).order_by('numero')
		}
		cuenta_ingresos = Cuenta.objects.get(numero=499999)
		cuentas[cuenta_ingresos] = []

		cuentas.update({
			cuenta: [] for cuenta in self.cuentas.filter(numero__gte=500000).order_by('numero')
		})
		cuenta_gastos = Cuenta.objects.get(numero=599999)
		cuentas[cuenta_gastos] = []
		cuenta_total = Cuenta.objects.get(numero=999999)
		cuentas[cuenta_total] = []

		subtotales = []
		iteraciones = 1
		for a in self.anteriores:
			manager = CierreManager(a)
			suma_positiva = 0
			for s in manager.hacer_resultados_positivos():
				try:
					cuentas[s.cuenta].append(s.total)
					suma_positiva += s.total
				except:
					pass
			cuentas[cuenta_ingresos].append(suma_positiva)
			suma_negativa = 0
			for s in manager.hacer_resultados_negativos():
				try:
					cuentas[s.cuenta].append(s.total)
					suma_negativa += s.total
				except:
					pass
			cuentas[cuenta_gastos].append(suma_negativa)
			cuentas[cuenta_total].append(suma_positiva + suma_negativa)
			for c, v in cuentas.items():
				if not len(v) == iteraciones:
					cuentas[c].append(0)
			iteraciones += 1



		manager = CierreManager(self.cierre)
		suma_positiva = 0
		for s in manager.hacer_resultados_positivos():
			try:	
				cuentas[s.cuenta].append(s.total)
				suma_positiva += s.total
			except:
				pass
		cuentas[cuenta_ingresos].append(suma_positiva)
		suma_negativa = 0
		for s in manager.hacer_resultados_negativos():
			try:
				cuentas[s.cuenta].append(s.total)
				suma_negativa += s.total
			except:
				pass			
		cuentas[cuenta_gastos].append(suma_negativa)
		cuentas[cuenta_total].append(suma_positiva + suma_negativa)
		for c, v in cuentas.items():
			if not len(v) == iteraciones:
				cuentas[c].append(0)

		retorno = []
		for key, value in cuentas.items():
			retorno.append([key, value])
		return sorted(retorno, key=lambda x: x[0].numero)

	def hacer_pdf(self, statics):

		cierre = self.cierre
		columnas = self.hacer_columnas()
		resultados = self.hacer_filas_resultados()
		logo_auditor = self.logo_as_data_uri()

		# Generacion del PDF de Resultados
		html_string_rdos = render_to_string('reportes/pdfs/resultados.html', locals())
		html_rdos = HTML(string=html_string_rdos, base_url=statics)
		pdf = html_rdos.write_pdf()

		# Cargar estado de Resultados
		reporte = Reporte(
				consorcio=self.consorcio,
				cierre=cierre,
				nombre="Resultados mensuales {}-{}.pdf".format(str(cierre.periodo.year), str(cierre.periodo.month)),
				automatico=True
			)
		reporte.save()
		ruta = "{}_rdos_{}.pdf".format(
			self.consorcio.abreviatura,
			str(cierre.periodo)
			)

		reporte.ubicacion = SimpleUploadedFile(ruta, pdf, content_type='application/pdf')
		reporte.save()


	@transaction.atomic
	def guardar(self, statics):

		""" Guarda el estado de resultados y subtotales de resultados. Coloca total y confirmado y mails y guarda el cierre  """

		cierre = self.cierre

		self.hacer_pdf(statics)

		cierreManager = CierreManager(cierre)

		subtotales_resultados_positivos = cierreManager.hacer_resultados_positivos()
		Subtotal.objects.bulk_create(subtotales_resultados_positivos)
		suma_resultados_positivos = cierreManager.sumar(subtotales_resultados_positivos)

		subtotales_resultados_negativos = cierreManager.hacer_resultados_negativos()
		Subtotal.objects.bulk_create(subtotales_resultados_negativos)
		suma_resultados_negativos = cierreManager.sumar(subtotales_resultados_negativos)

		cierre.total = suma_resultados_positivos + suma_resultados_negativos
		cierre.save()