from __future__ import unicode_literals
from datetime import datetime, date, timedelta
from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models import Sum
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from django.core.validators import RegexValidator
from django_afip.models import PointOfSales, DocumentType, ConceptType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.template.loader import render_to_string
from weasyprint import HTML

from consorcios.models import *
from contabilidad.models import *


class Relacion(models.Model):

	""" Retenciones """

	nombre = models.CharField(max_length=30)
	cuenta_contable = models.ForeignKey(Cuenta, on_delete=models.CASCADE)

	def __str__(self):
		return self.nombre


class Caja(models.Model):

	""" Tesoro """

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	primario = models.BooleanField(default=False) # Unicamente para mercadopago
	nombre = models.CharField(max_length=30)
	entidad = models.CharField(max_length=30, blank=True, null=True)
	# Saldo a fecha determinada
	fecha = models.DateField(blank=True, null=True)
	saldo = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
	cuenta_contable = models.ForeignKey(Cuenta, on_delete=models.CASCADE)

	def __str__(self):
		nombre = self.nombre
		if self.entidad:
			nombre += " - {}".format(self.entidad)
		return nombre

	def movimientos(self, fin=date.today()):

		""" Retorna un diccionario de movimientos ordenados por fecha """

		datos = []

		datos.append({self.fecha: ['Saldo Inicial' ,'', self.saldo, 0]})

		cajacomprobantes = self.cajacomprobante_set.filter(fecha__range=[self.fecha ,fin])
		for caja in cajacomprobantes:
			if caja.valor >= 0:
				if caja.caja.primario:
					referencia = ""
					try:
						preference = caja.comprobante.cobro_set.first().preference
						if preference:
							referencia = preference.payments.filter(status="approved").first().mp_id
					except:
						pass
				else:
					referencia = caja.referencia
				datos.append({caja.fecha: [caja.nombre, referencia, caja.valor, 0]})
			else:
				nombre = 'Anulacion de {}'.format(caja.nombre)
				datos.append({caja.fecha: [nombre, caja.referencia, 0, -caja.valor]})


		cajaops = self.cajaop_set.filter(fecha__range=[self.fecha ,fin])
		for caja in cajaops:
			if caja.valor >= 0:
				datos.append({caja.fecha: [caja.nombre, caja.referencia, 0, caja.valor]})
			else:
				datos.append({caja.fecha: [caja.nombre, caja.referencia, -caja.valor, 0]})


		cajatransferenciaorigen = self.transferencia_origen.filter(fecha__range=[self.fecha ,fin])
		for caja in cajatransferenciaorigen:
			datos.append({caja.fecha: [caja.nombre, caja.referencia, 0, caja.valor]})

		cajatransferenciadestino = self.transferencia_destino.filter(fecha__range=[self.fecha ,fin])
		for caja in cajatransferenciadestino:
			datos.append({caja.fecha: [caja.nombre, caja.referencia, caja.valor, 0]})

		# Creacion del diccionario con las fechas
		fechas = {
			next(iter(movimiento)): [] for movimiento in datos
		}

		# Incorporacion de operaciones a las fechas
		for dato in datos:
			fecha = next(iter(dato))
			valores = list(dato.values())[0]
			fechas[fecha].append(valores)

		# Diccionario de retorno
		operaciones = {}
		saldo = 0
		numero = 1
		for fecha, movimientos in sorted(fechas.items()):
			data = {}
			for m in movimientos:
				saldo += m[2]
				saldo -= m[3]
				m.append(saldo)
				data.update({numero: m})
				numero += 1
			operaciones.update({fecha: data})

		return operaciones


class Ingreso(models.Model):

	""" Recursos """

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	primario = models.BooleanField(default=False)
	nombre = models.CharField(max_length=30)
	# False = Homogeneo, True = Prorrateo segun superficie de lote
	prorrateo = models.BooleanField(default=False)
	prioritario = models.BooleanField(default=False)
	cuenta_contable = models.ForeignKey(Cuenta, on_delete=models.CASCADE)

	def __str__(self):
		return self.nombre


class Accesorio(models.Model):

	""" Accesorios de intereses y descuentos """

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	nombre = models.CharField(max_length=15)
	plazo = models.PositiveIntegerField(blank=True, null=True)
	CLASE_CHOICES = (
			('interes', 'Interes'),
			('descuento', 'Descuento'),
			('bonificacion', 'Bonificacion'),
		)
	clase = models.CharField(max_length=15, choices=CLASE_CHOICES)
	FIJO = 'fijo'
	TASA = 'tasa'
	TIPO_CHOICES = (
			(FIJO, 'Monto fijo'),
			(TASA, 'Tasa')
		)
	tipo = models.CharField(max_length=15, choices=TIPO_CHOICES ,default=TASA)
	monto = models.IntegerField(blank=True, null=True)

	DIARIO = 1
	SEMANAL = 7
	QUINCENAL = 15
	MENSUAL = 30
	BIMESTRAL = 60
	TRIMESTRAL = 90
	SEMESTRAL = 120
	BASES_CHOICES = (
			(DIARIO, 'Diario'),
			(SEMANAL, 'Semanal'),
			(QUINCENAL, 'Quincenal'),
			(MENSUAL, 'Mensual'),
			(BIMESTRAL, 'Bimestral'),
			(TRIMESTRAL, 'Trimestral'),
			(SEMESTRAL, 'Semestral'),
		)
	reconocimiento = models.IntegerField(choices=BASES_CHOICES, default=DIARIO)
	base_calculo = models.IntegerField(choices=BASES_CHOICES, default=MENSUAL)
	ingreso = models.ManyToManyField(Ingreso, blank=True)
	CONDICION_CHOICES = (
			(None, 'Sin condicion'),
			('grupo', 'Pertenencia a un grupo'),
	)
	condicion = models.CharField(max_length=15, blank=True, null=True, choices=CONDICION_CHOICES)
	finalizacion = models.DateField(blank=True, null=True)
	cuenta_contable = models.ForeignKey(Cuenta, on_delete=models.CASCADE)


	@property
	def descripcion(self):
		nombre = self.nombre
		tipos = {k: v for k, v in self.TIPO_CHOICES}
		tipo = tipos[self.tipo]
		monto = str(self.monto)
		detalle = '{}: {} de {}'.format(nombre, tipo, monto)
		if self.tipo == 'tasa':
			bases = {k: v for k, v in self.BASES_CHOICES}
			base_calculo = bases[self.base_calculo].lower()
			detalle += '% {}'.format(base_calculo)
		plazo = str(self.plazo)
		detalle += '. Plazo de {} dias.'.format(plazo)
		return detalle

	def __str__(self):
		return self.nombre


class Gasto(models.Model):

	""" Erogaciones """

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	primario = models.BooleanField(default=False)
	nombre = models.CharField(max_length=50)
	cuenta_contable = models.ForeignKey(Cuenta, on_delete=models.CASCADE)

	def __str__(self):
		return self.nombre


class Socio(models.Model):

	""" Socios y NO SOCIOS. Quedo con el nombre de socio por intempestividad """

	# Usuarios diferentes por mas que tenga dos clubes (No se compensan unos con otros)
	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	# Socio o cliente
	es_socio = models.BooleanField(default=True)
	usuarios = models.ManyToManyField(User, blank=True)
	# Nombre del socio
	nombre = models.CharField(max_length=80)
	apellido = models.CharField(max_length=80)
	fecha_nacimiento = models.DateField(blank=True, null=True)
	es_extranjero = models.BooleanField(default=False)
	# Tipo de documento segun tabla de AFIP
	tipo_documento = models.ForeignKey(DocumentType, blank=True, null=True, on_delete=models.CASCADE)
	numero_documento = models.CharField(max_length=13, blank=True, null=True)
	telefono = models.CharField(max_length=30, blank=True, null=True)
	domicilio = models.CharField(max_length=100, blank=True, null=True)
	localidad = models.CharField(max_length=100, blank=True, null=True)
	provincia = models.ForeignKey(Codigo_Provincia, blank=True, null=True, on_delete=models.CASCADE)
	# Agregados
	profesion = models.CharField(max_length=40, blank=True, null=True)
	baja = models.DateField(blank=True, null=True)
	codigo = models.CharField(max_length=5, blank=True, null=True)
	mail = models.EmailField(blank=True, null=True)

	def __str__(self):
		nombre = '{}, {}'.format(self.apellido, self.nombre)
		return nombre

	@property
	def nombre_completo(self):
		return '{}, {}'.format(self.apellido, self.nombre)


	def get_saldos(self, fecha=None):
		fecha = fecha if fecha else date.today()
		saldos = self.saldo_set.filter(padre__isnull=True, fecha__lte=fecha) # Capta los saldos padre
		saldos_utilizados = []
		for s in saldos:
			if not float(s.saldo(fecha)) > 0.00:
				saldos_utilizados.append(s.id)

		saldos = saldos.exclude(id__in=saldos_utilizados)
		return saldos

	def generar_codigo(self):
		from admincu.funciones import generador_codigo
		self.codigo = generador_codigo(Socio, 'codigo')
		self.save()

	def hacer_pdf(self):

		""" Realiza el PDF del codigo para realizacion de usuario """

		if not self.codigo:
			self.generar_codigo()
		socio = self
		html_string = render_to_string('arquitectura/pdfs/codigo-socio.html', locals())
		html = HTML(string=html_string, base_url='https://www.admincu.com/parametros/')
		return html.write_pdf()


	def cuenta_corriente(self, fin=date.today()):

		""" Retorna un diccionario de movimientos ordenados por fecha """

		from creditos.models import Credito

		if self.es_socio:
			creditos = Credito.objects.filter(dominio__in=self.socio.all(), padre__isnull=True, fecha__lte=fin)
		else:
			creditos = Credito.objects.filter(socio=self, padre__isnull=True, fecha__lte=fin)

		datos = []

		for credito in creditos:
			# Se agrega el credito
			datos.append({credito.fecha: [credito, credito.nombre, credito.bruto, 0]})

			# Se capta el cobro si es que tiene
			cobros = credito.cobro_set.all().exclude(mercado_pago__isnull=False, comprobante__isnull=True).exclude(preference__isnull=False, comprobante__isnull=True)
			if cobros:
				for cobro in cobros:
					# Se coloca el descuento realizado
					if cobro.int_desc < 0:
						datos.append({cobro.fecha: [credito, "Descuento realizado", 0, -cobro.int_desc]})
					# Se coloca el interes realizado
					elif cobro.int_desc > 0:
						datos.append({cobro.fecha: [credito, "Interes generado", cobro.int_desc, 0]})

					if cobro.subtotal > 0:
						datos.append({cobro.fecha: [credito, cobro.nombre, 0, cobro.subtotal]})
					else:
						datos.append({cobro.fecha: [credito, cobro.nombre, -cobro.subtotal, 0]})

			# Se capta si no esta finalizado a la fecha
			if not credito.fin or credito.fin > fin:
				int_desc = credito.int_desc(fecha_operacion=fin)
				# Se coloca el descuento a la fecha
				if int_desc < 0:
					datos.append({fin: [credito, "Descuento a la fecha", 0, -int_desc]})
				# Se coloca el interes a la fecha
				elif int_desc > 0:
					datos.append({fin: [credito, "Interes a la fecha", int_desc, 0]})

			# Se capta si tiene hijos
			hijos = credito.hijos.all()
			if hijos:
				for h in hijos:
					# Se capta el cobro si es que tiene
					cobros = h.cobro_set.filter(comprobante__isnull=False)
					if cobros:
						for cobro in cobros:
							# Se coloca el descuento realizado
							if cobro.int_desc < 0:
								datos.append({cobro.fecha: [h, "Descuento realizado", 0, -cobro.int_desc]})
							# Se coloca el interes realizado
							elif cobro.int_desc > 0:
								datos.append({cobro.fecha: [h, "Interes generado", cobro.int_desc, 0]})

							if cobro.subtotal > 0:
								datos.append({cobro.fecha: [credito, cobro.nombre, 0, cobro.subtotal]})
							else:
								datos.append({cobro.fecha: [credito, cobro.nombre, -cobro.subtotal, 0]})

					# Se capta si no esta finalizado a la fecha
					if not h.fin or h.fin > fin:
						int_desc = h.int_desc(fecha_operacion=fin)
						# Se coloca el descuento a la fecha
						if int_desc < 0:
							datos.append({fin: [h, "Descuento a la fecha", 0, -int_desc]})
						# Se coloca el interes a la fecha
						elif int_desc > 0:
							datos.append({fin: [h, "Interes a la fecha", int_desc, 0]})



		saldos = self.saldo_set.filter(
				fecha__lte=fin,
				padre__isnull=True
				)

		for saldo in saldos:
			# Se agrega el saldo
			datos.append({saldo.fecha: ["Saldo a favor", saldo.nombre, 0, saldo.subtotal]})
			hijos = saldo.hijos.all()
			if hijos:
				for h in hijos:
					if h.subtotal < 0:
						datos.append({h.fecha: ["Utilizacion de saldo", h.nombre, -h.subtotal, 0]})
					else:
						datos.append({h.fecha: ["Utilizacion de saldo", h.nombre, 0, h.subtotal]})


		# Creacion del diccionario con las fechas
		fechas = {
			next(iter(movimiento)): [] for movimiento in datos
		}

		# Incorporacion de operaciones a las fechas
		for dato in datos:
			fecha = next(iter(dato))
			valores = list(dato.values())[0]
			fechas[fecha].append(valores)

		# Diccionario de retorno
		operaciones = {}
		saldo = 0
		numero = 1
		for fecha, movimientos in sorted(fechas.items()):
			data = {}
			for m in movimientos:
				saldo += m[2]
				saldo -= m[3]
				m.append(saldo)
				data.update({numero: m})
				numero += 1
			operaciones.update({fecha: data})


		return operaciones

	class Meta:
		ordering = ['apellido']


class Dominio(models.Model):

	""" Lotes """

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	# Charfield por si es un edificio y la numeracion lleva letra
	numero = models.CharField(max_length=5)
	# Socio ocupante
	socio = models.ForeignKey(Socio, blank=True, null=True, on_delete=models.CASCADE, related_name='socio')
	# Socio propietario
	propietario = models.ForeignKey(Socio, blank=True, null=True, on_delete=models.CASCADE, related_name='propietario')
	# Identificacion del parentezco del socio ocupante con el lote.
	padre = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL, related_name='hijos')
	identificacion = models.ForeignKey(Tipo_Ocupante, blank=True, null=True, on_delete=models.CASCADE)
	superficie_total = models.DecimalField(max_digits=9, decimal_places=3, blank=True, null=True)
	superficie_cubierta = models.DecimalField(max_digits=9, decimal_places=3, blank=True, null=True)
	# Datos de Domicilio
	domicilio_calle = models.CharField(max_length=70, blank=True, null=True)
	domicilio_numero = models.CharField(max_length=10, blank=True, null=True)
	domicilio_piso = models.CharField(max_length=10, blank=True, null=True)
	domicilio_oficina = models.CharField(max_length=10, blank=True, null=True)
	domicilio_sector = models.CharField(max_length=10, blank=True, null=True)
	domicilio_torre = models.CharField(max_length=10, blank=True, null=True)
	domicilio_manzana = models.CharField(max_length=10, blank=True, null=True)
	domicilio_parcela = models.CharField(max_length=10, blank=True, null=True)
	domicilio_catastro = models.CharField(max_length=10, blank=True, null=True)

	def __str__(self):
		return str(self.numero)

	@property
	def nombre(self):
		muestra = "#{}. ".format(self.numero)
		if self.domicilio_torre:
			muestra += "T: {}. ".format(self.domicilio_torre)
		if self.domicilio_manzana:
			muestra += "M: {}. ".format(self.domicilio_manzana)
		if self.domicilio_numero:
			muestra += "N°: {}. ".format(self.domicilio_numero)
		return muestra


	@property
	def nombre_completo(self):
		return None


	class Meta:
		unique_together = ('consorcio', 'numero')
		ordering = ['socio']


class Grupo(models.Model):

	""" Grupos vinculantes de dominios """

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	nombre = models.CharField(max_length=80)
	dominios = models.ManyToManyField(Dominio)
	baja = models.DateField(blank=True, null=True)

	def __str__(self):
		return self.nombre



class Acreedor(models.Model):

	""" Acreedores de la entidad """

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	primario = models.BooleanField(default=False)
	tipo = models.ManyToManyField(Gasto)
	recibe = models.ManyToManyField(Relacion, blank=True, related_name="recibe")
	genera = models.ManyToManyField(Relacion, blank=True, related_name="genera")
	nombre = models.CharField(max_length=150)
	# Tipo de documento segun tabla de AFIP
	tipo_documento = models.ForeignKey(DocumentType, blank=True, null=True, on_delete=models.CASCADE)
	numero_documento = models.CharField(max_length=13, blank=True, null=True)
	cuenta_contable = models.ForeignKey(Cuenta, on_delete=models.CASCADE)


	def __str__(self):
		return self.nombre
