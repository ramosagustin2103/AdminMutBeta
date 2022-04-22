from contabilidad.asientos.manager import AsientoCreator
from .models import *

def bloqueador(creditos):
	condiciones = []
	for c in creditos:
		if c.saldo:
			condiciones.append(c.prioritario)

	condiciones = list(set(condiciones))
	bloqueo = True if len(condiciones) > 1 else False
	return bloqueo

def bloqueador_descuentos(creditos):
	deudas = []
	for c in creditos:
		if c.saldo:
			if c.vencimiento:
				if c.vencimiento < date.today():
					deudas.append(c)
	deudor = False if len(deudas) == 0 else True
	return deudor

def asiento_diario(dia, consorcio, comprobantes):
	if comprobantes:
		descripcion = "Cobros - {}".format(str(dia))
		data_asiento = {
			'consorcio': consorcio,
			'fecha_asiento': dia,
			'descripcion': descripcion
		}
		operaciones = []
		for c in comprobantes:
			for operacion in c.hacer_contabilidad():
				operaciones.append(operacion) # Obtenemos todas las operaciones


		cuentas = set([o[0] for o in operaciones]) # Seteamos las cuentas
		data_operaciones = []
		for c in cuentas:
			diccionario = {
				'cuenta': c,
				'descripcion': descripcion
			}
			suma = 0
			for o in operaciones:
				if o[0] == c:
					suma += o[1] # Sumamos las cuentas
			if suma > 0:
				diccionario.update({
						'debe': suma,
						'haber': 0
					})
			else:
				diccionario.update({
						'haber': -suma,
						'debe': 0
					})
			data_operaciones.append(diccionario)


		crear_asiento = AsientoCreator(data_asiento, data_operaciones)
		asiento = crear_asiento.guardar()
		comprobantes.update(asiento=asiento)