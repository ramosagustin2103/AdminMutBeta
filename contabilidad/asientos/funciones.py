from admincu.funciones import *
from arquitectura.models import *
from contabilidad.models import *
from django.db import transaction
from contabilidad.funciones import *
from op.models import *


def eliminarAsiento(asiento):
	asiento.operaciones.all().delete()
	asiento.delete()

def reversar_operaciones(asiento, identificacion ,descripcion):
	operaciones = []
	# Reversion de las lineas
	for op in asiento.operaciones.all():
		operaciones.append(
			Operacion(
				numero_aleatorio=identificacion,
				cuenta=op.cuenta,
				debe=op.haber,
				haber=op.debe,
				descripcion=descripcion,
			)
		)
	return operaciones


def asiento_cierre_res(ejercicio):

	rango = [ejercicio.inicio, ejercicio.cierre]
	cuentas = Plan.objects.get(consorcio=ejercicio.consorcio).cuentas.filter(nivel=4, numero__gt=400000).order_by('numero')
	positivas = cuentas.filter(numero__range=[400000,499999])
	negativas = cuentas.filter(numero__gte=500000)

	cuenta_resultados = Cuenta.objects.get(numero=321001)

	identificacion = randomNumber(Operacion, 'numero_aleatorio')
	descripcion = "Cierre de resultados. Ejercicio %s" % ejercicio.nombre

	operaciones = []
	suma = 0
	for cuenta in positivas:
		saldo = cuenta.saldo(ejercicio)
		if saldo != 0:
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=cuenta,
					debe=abs(saldo) if saldo > 0 else 0,
					haber=abs(saldo) if saldo < 0 else 0,
					descripcion=descripcion
				)
			)

	for cuenta in negativas:
		saldo = cuenta.saldo(ejercicio)
		if saldo != 0:
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=cuenta,
					debe=abs(saldo) if saldo < 0 else 0,
					haber=abs(saldo) if saldo > 0 else 0,
					descripcion=descripcion
				)
			)

	if not operaciones:
		return "No se encontraron resultados en el ejercicio."

	total_resultados = sum([o.debe - o.haber for o in operaciones])

	operaciones.append(Operacion(
			numero_aleatorio=identificacion,
			cuenta=cuenta_resultados,
			debe=abs(total_resultados) if total_resultados < 0 else 0,
			haber=abs(total_resultados) if total_resultados > 0 else 0,
			descripcion=descripcion
		))

	asiento_cierre_resultados = Asiento(
			consorcio=ejercicio.consorcio,
			fecha_asiento=ejercicio.cierre,
			descripcion=descripcion,
			principal=2
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento_cierre_resultados.save()
			asiento_cierre_resultados.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			return True
	except:
		return "Hubo un error al intentar crear el asiento. Intente nuevamente mas tarde."


def asiento_cierre_pat(ejercicio):

	rango = [ejercicio.inicio, ejercicio.cierre]
	cuentas = Plan.objects.get(consorcio=ejercicio.consorcio).cuentas.filter(nivel=4).order_by('numero')


	identificacion = randomNumber(Operacion, 'numero_aleatorio')
	operaciones = []
	descripcion = "Cierre patrimonial. Ejercicio %s" % ejercicio.nombre

	for cuenta in cuentas:
		op = cuenta.operaciones(ejercicio)
		debe = cuenta.saldo_debe(op)
		haber = cuenta.saldo_haber(op)
		diferencia = debe - haber
		if diferencia != 0:
			operaciones.append(Operacion(
				numero_aleatorio=identificacion,
				cuenta=cuenta,
				debe=abs(diferencia) if diferencia < 0 else 0,
				haber=abs(diferencia) if diferencia > 0 else 0,
				descripcion=descripcion

			))

	if not operaciones:
		return "No se encontraron resultados en el ejercicio."

	asiento_cierre_patrimonial = Asiento(
			consorcio=ejercicio.consorcio,
			fecha_asiento=ejercicio.cierre,
			descripcion=descripcion,
			principal=3
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento_cierre_patrimonial.save()
			asiento_cierre_patrimonial.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			return True
	except:
		return "Hubo un error al intentar crear el asiento. Intente nuevamente mas tarde."


def asiento_apertura(ejercicio):
	# Para recuperar el ejercicio anterior
	try:
		ejercicio_anterior = Ejercicio.objects.filter(consorcio=ejercicio.consorcio, cierre__lt=ejercicio.inicio).order_by('-cierre')[0]
	except:
		ejercicio_anterior = None

	# Para saber si el ejercicio anterior tiene asiento de cierre
	try:
		asiento_cierre_anterior = Asiento.objects.get(
			consorcio=ejercicio.consorcio,
			fecha_asiento__range=[ejercicio_anterior.inicio, ejercicio_anterior.cierre],
			principal=3
		)
	except:
		asiento_cierre_anterior = None

	if not asiento_cierre_anterior:
		return "No se puede generar el asiento de apertura si no hay cierre en ejercicio anterior."

	else:
		identificacion = randomNumber(Operacion, 'numero_aleatorio')
		descripcion = "Apertura patrimonial. Ejercicio %s" % ejercicio.nombre
		operaciones = reversar_operaciones(asiento_cierre_anterior, identificacion, descripcion)

		asiento_apertura_patrimonial = Asiento(
				consorcio=ejercicio.consorcio,
				fecha_asiento=ejercicio.inicio,
				descripcion="Apertura patrimonial. Ejercicio %s" % ejercicio.nombre,
				principal=1
			)
		try:
			with transaction.atomic():
				Operacion.objects.bulk_create(operaciones)
				asiento_apertura_patrimonial.save()
				asiento_apertura_patrimonial.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
				return True
		except:
			return "Hubo un error al intentar crear el asiento. Intente nuevamente mas tarde."


def asiento_deuda(deuda):
	gastoDeuda = GastoDeuda.objects.filter(deuda=deuda)
	operaciones = []
	identificacion = randomNumber(Operacion, 'numero_aleatorio')
	# Creacion de gastos
	for g in gastoDeuda:
		saldo = g.valor
		operaciones.append(
			Operacion(
				numero_aleatorio=identificacion,
				cuenta=g.gasto.cuenta_contable,
				debe=saldo if saldo > 0 else 0,
				haber=0 if saldo > 0 else saldo,
				descripcion="%s - %s" % (g.deuda.acreedor, g.deuda.numero)
			)
		)
	# Creacion de la deuda
	operaciones.append(
		Operacion(
			numero_aleatorio=identificacion,
			cuenta=deuda.acreedor.cuenta_contable,
			debe=0 if deuda.total > 0 else deuda.total,
			haber=deuda.total if deuda.total > 0 else 0,
			descripcion="%s - %s" % (g.deuda.acreedor, g.deuda.numero)
		)
	)
	# Creacion del asiento
	asiento = Asiento(
			consorcio=deuda.consorcio,
			fecha_asiento=deuda.fecha,
			descripcion="Deuda con %s - Numero de cbte %s" % (deuda.acreedor, deuda.numero),
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento.save()
			asiento.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			deuda.asiento = asiento
			deuda.save()
			return True
	except:
		return "Hubo un error al intentar crear el asiento."


def asiento_op(op, gastoOP, deudaOP, retencionOP, cajaOP):
	operaciones = []
	identificacion = randomNumber(Operacion, 'numero_aleatorio')
	descripcion = "OP %s-%s - %s" % (op.punto, op.numero, op.acreedor)
	# Creacion de gastos
	if gastoOP:
		for g in gastoOP:
			saldo = g.valor
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=g.gasto.cuenta_contable,
					debe=saldo if saldo > 0 else 0,
					haber=0 if saldo > 0 else saldo,
					descripcion=descripcion
				)
			)
	# Creacion de pago de deuda
	if deudaOP:
		for d in deudaOP:
			cuenta = d.deuda.retencion.cuenta_contable if d.deuda.retencion else d.deuda.acreedor.cuenta_contable
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=cuenta,
					debe=d.valor,
					haber=0,
					descripcion=descripcion
				)
			)
	# Creacion de la deuda por retenciones
	if retencionOP:
		for r in retencionOP:
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=r.deuda.retencion.cuenta_contable,
					debe=0,
					haber=r.valor,
					descripcion=descripcion
				)
			)

	# Creacion de los metodos
	for c in cajaOP:
		operaciones.append(
			Operacion(
				numero_aleatorio=identificacion,
				cuenta=c.caja.cuenta_contable,
				debe=0,
				haber=c.valor,
				descripcion=descripcion
			)
		)

	# Creacion del asiento
	fecha_asiento = op.fecha_operacion or op.fecha
	asiento = Asiento(
			consorcio=op.consorcio,
			fecha_asiento=fecha_asiento,
			descripcion=descripcion,
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento.save()
			asiento.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			op.asiento = asiento
			op.save()
			return True
	except:
		return "Hubo un error al intentar crear el asiento."


def asiento_op_anulacion(op):
	identificacion = randomNumber(Operacion, 'numero_aleatorio')
	descripcion = "Anulacion OP %s-%s - %s" % (op.punto, op.numero, op.acreedor)
	# Creacion de movimientos
	operaciones = reversar_operaciones(op.asiento, identificacion, descripcion)

	# Creacion del asiento
	asiento = Asiento(
			consorcio=op.consorcio,
			fecha_asiento=op.anulado,
			descripcion=descripcion,
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento.save()
			asiento.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			op.asiento_anulado = asiento
			op.save()
			return True
	except:
		return "Hubo un error al intentar crear el asiento."


def asiento_liq(liquidacion, creditos):
	operaciones = []
	identificacion = randomNumber(Operacion, 'numero_aleatorio')
	ingresos = Ingreso.objects.filter(consorcio=liquidacion.consorcio)
	cuentas = {i.cuenta_contable: 0 for i in ingresos}

	# Suma de creditos por tipo de recursos
	for c in creditos:
		cuentas[c.ingreso.cuenta_contable] += c.capital

	# Creacion del credito
	operaciones.append(
		Operacion(
			numero_aleatorio=identificacion,
			cuenta=Cuenta.objects.get(numero=112101),
			debe=liquidacion.capital,
			haber=0,
			descripcion="Liquidacion %s - %s" % (liquidacion.punto, liquidacion.numero)
		)
	)

	#Creacion de los recursos
	for cuenta,saldo in cuentas.items():
		if saldo !=0:
			operaciones.append(
					Operacion(
					numero_aleatorio=identificacion,
					cuenta=cuenta,
					debe=0,
					haber=saldo,
					descripcion="Liquidacion %s - %s" % (liquidacion.punto, liquidacion.numero)
				)
			)

	# Creacion del asiento
	asiento = Asiento(
			consorcio=liquidacion.consorcio,
			fecha_asiento=liquidacion.fecha,
			descripcion="Liquidacion %s - %s" % (liquidacion.punto, liquidacion.numero)
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento.save()
			asiento.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			liquidacion.asiento = asiento
			liquidacion.save()
			return True
	except:
		return "Hubo un error al intentar crear el asiento."


	return True


def asiento_comp(comprobante):
	descripcion = "%s %s - %s" % (comprobante.receipt.receipt_type, comprobante.receipt.point_of_sales, comprobante.receipt.receipt_number)
	identificacion = randomNumber(Operacion, 'numero_aleatorio')
	if comprobante.receipt.receipt_type.code == "15" or comprobante.receipt.receipt_type.code == "13":
		operaciones = []
		suma_capital = 0
		suma_descuentos = 0
		suma_intereses = 0
		for c in comprobante.cobro_set.all():
			suma_capital += c.capital
			suma_descuentos += c.int_desc if c.int_desc < 0 else 0
			suma_intereses += c.int_desc if c.int_desc > 0 else 0

		# Creacion de la forma de cobro
		if comprobante.receipt.receipt_type.code == "15":
			for c in comprobante.cajacomprobante_set.all():
				operaciones.append(
					Operacion(
						numero_aleatorio=identificacion,
						cuenta=c.caja.cuenta_contable,
						debe=c.valor,
						haber=0,
						descripcion=descripcion
					)
				)
		else:
			for c in comprobante.cobro_set.all():
				operaciones.append(
					Operacion(
						numero_aleatorio=identificacion,
						cuenta=c.credito.ingreso.cuenta_contable,
						debe=c.subtotal,
						haber=0,
						descripcion=descripcion
					)
				)

		# Creacion de descuentos
		if suma_descuentos:
			suma_descuentos = -suma_descuentos
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=Cuenta.objects.get(numero=511125),
					debe=suma_descuentos,
					haber=0,
					descripcion=descripcion
				)
			)

		# Creacion de intereses
		if suma_intereses:
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=Cuenta.objects.get(numero=411103),
					debe=0,
					haber=suma_intereses,
					descripcion=descripcion
				)
			)

		# Creacion de cobro de expensa
		if suma_capital:
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=Cuenta.objects.get(numero=112101),
					debe=0,
					haber=suma_capital,
					descripcion=descripcion
				)
			)

		# Creacion de la utilizacion de saldos
		for s in comprobante.saldos_utilizados.all():
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=Cuenta.objects.get(numero=112103),
					debe=s.subtotal_invertido,
					haber=0,
					descripcion=descripcion
				)
			)

		# Creacion del saldo resultante
		for s in comprobante.saldos.all():
			operaciones.append(
				Operacion(
					numero_aleatorio=identificacion,
					cuenta=Cuenta.objects.get(numero=112103),
					debe=0,
					haber=s.subtotal,
					descripcion=descripcion
				)
			)


	else:
		operaciones = reversar_operaciones(comprobante.relacionado.asiento, identificacion, descripcion)
	# Creacion del asiento
	asiento = Asiento(
			consorcio=comprobante.consorcio,
			fecha_asiento=comprobante.receipt.issued_date,
			descripcion=descripcion
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento.save()
			asiento.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			comprobante.asiento = asiento
			comprobante.save()
			return True
	except:
		return "Hubo un error al intentar crear el asiento."


	return True


def asiento_liq_auto(cierre, liquidacion):
	operaciones = []
	identificacion = randomNumber(Operacion, 'numero_aleatorio')

	# Creacion del credito
	operaciones.append(
		Operacion(
			numero_aleatorio=identificacion,
			cuenta=Cuenta.objects.get(numero=112101),
			debe=cierre.total_liq,
			haber=0,
			descripcion="Liquidacion %s - %s" % (liquidacion.punto, liquidacion.numero)
		)
	)

	# Creacion de la reserva
	if cierre.reservado:
		operaciones.append(
			Operacion(
				numero_aleatorio=identificacion,
				cuenta=Cuenta.objects.get(numero=311001),
				debe=0 if cierre.reservado > 0 else abs(cierre.reservado),
				haber=cierre.reservado if cierre.reservado > 0 else 0,
				descripcion="Liquidacion %s - %s" % (liquidacion.punto, liquidacion.numero)
			)
		)

	ingreso = Ingreso.objects.filter(consorcio=cierre.consorcio, primario=True)[0]
	# Creacion del ingreso
	operaciones.append(
		Operacion(
			numero_aleatorio=identificacion,
			cuenta=ingreso.cuenta_contable,
			debe=0,
			haber=cierre.total,
			descripcion="Liquidacion %s - %s" % (liquidacion.punto, liquidacion.numero)
		)
	)

	# Creacion del asiento
	asiento = Asiento(
			consorcio=liquidacion.consorcio,
			fecha_asiento=liquidacion.fecha,
			descripcion="Liquidacion %s - %s" % (liquidacion.punto, liquidacion.numero)
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento.save()
			asiento.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			liquidacion.asiento = asiento
			liquidacion.save()
			return True
	except:
		return "Hubo un error al intentar crear el asiento."


	return True


def asiento_compens(compensacion):
	operaciones = []
	cobro = compensacion.cobro_set.all()[0]
	identificacion = randomNumber(Operacion, 'numero_aleatorio')
	descripcion = "Compensacion saldo {}".format(compensacion.socio)
	suma_capital = 0
	suma_descuentos = 0
	suma_intereses = 0
	for c in compensacion.cobro_set.all():
		suma_capital += c.capital
		suma_descuentos += c.int_desc if c.int_desc < 0 else 0
		suma_intereses += c.int_desc if c.int_desc > 0 else 0

	# Creacion de la utilizacion de saldos
	for s in compensacion.saldos_utilizados.all():
		operaciones.append(
			Operacion(
				numero_aleatorio=identificacion,
				cuenta=Cuenta.objects.get(numero=112103),
				debe=s.subtotal_invertido,
				haber=0,
				descripcion=descripcion
			)
		)
	# Creacion de descuentos
	if suma_descuentos:
		suma_descuentos = -suma_descuentos
		operaciones.append(
			Operacion(
				numero_aleatorio=identificacion,
				cuenta=Cuenta.objects.get(numero=511125),
				debe=suma_descuentos,
				haber=0,
				descripcion=descripcion
			)
		)

	# Creacion de intereses
	if suma_intereses:
		operaciones.append(
			Operacion(
				numero_aleatorio=identificacion,
				cuenta=Cuenta.objects.get(numero=411103),
				debe=0,
				haber=suma_intereses,
				descripcion=descripcion
			)
		)

	# Creacion de cobro de expensa
	if suma_capital:
		operaciones.append(
			Operacion(
				numero_aleatorio=identificacion,
				cuenta=Cuenta.objects.get(numero=112101),
				debe=0,
				haber=suma_capital,
				descripcion=descripcion
			)
		)


	# Creacion del asiento
	asiento = Asiento(
			consorcio=compensacion.consorcio,
			fecha_asiento=compensacion.fecha,
			descripcion=descripcion,
		)
	try:
		with transaction.atomic():
			Operacion.objects.bulk_create(operaciones)
			asiento.save()
			asiento.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))
			compensacion.asiento = asiento
			compensacion.save()
			return True
	except:
		return "Hubo un error al intentar crear el asiento."


	return True

