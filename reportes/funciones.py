from contabilidad.models import *
from datetime import datetime, timedelta
from arquitectura.models import *


def saldoMensual(cuentas, cons, periodo, primer_dia=None):
	if not primer_dia:
		primer_dia = periodo.replace(day=1)
	ultimo_dia = periodo
	rango = [primer_dia, ultimo_dia]
	asientos = Asiento.objects.filter(consorcio=cons, fecha_asiento__range=rango)
	operaciones = [op.id for a in asientos for op in a.operaciones.all()]
	operaciones = Operacion.objects.filter(id__in=operaciones)

	for cuenta in cuentas:
		cuenta.subtotal = sum([op.haber - op.debe for op in operaciones.filter(cuenta=cuenta)])

	return cuentas

def hacerTabla(anteriores, periodo, cuentas):
	data = []
	columnas = [[a.periodo, a.periodo] for a in anteriores]
	columnas.append([periodo.periodo, periodo.periodo])
	total = 0
	for cuenta in cuentas:
		meses = []
		for anterior in anteriores:
			try:
				valor = anterior.subtotales.get(cuenta=cuenta).total
			except:
				valor = 0
			meses.append([anterior.periodo, valor])

		meses.append([periodo.periodo, cuenta.subtotal])
		data.append([cuenta, meses])
		total += cuenta.subtotal

	totales = []

	for anterior in anteriores:
		totales.append([anterior.periodo, anterior.total])


	totales.append([periodo.periodo, total])




	return columnas, data, totales


