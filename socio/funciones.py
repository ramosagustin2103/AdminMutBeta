from .models import *
from comprobantes.models import *

def generar_cobro(pago):
	cobros = Cobro.objects.filter(mercado_pago=pago)
	if not cobros:
		pagos = Pago.objects.filter(preference=pago.preference)
		cobros = []
		for p in pagos:
			cobros.append(Cobro(
				consorcio=p.socio.consorcio,
				socio=p.socio,
				credito=p.credito,
				capital=p.capital,
				int_desc=p.int_desc,
				subtotal=p.subtotal,
				mercado_pago=pago,
			))
			p.credito.compensado = True
			p.credito.save()
		Cobro.objects.bulk_create(cobros)