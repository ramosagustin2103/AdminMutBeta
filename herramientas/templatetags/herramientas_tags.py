from django import template

register = template.Library()


def numerico(valor, tam):
	cero = "0"
	tam = int(tam)
	valor = str(round(round(valor, 2)*100, 0)) if valor else cero
	return (tam - len(valor))*cero + valor



def superficies(dominios, tipo):
	parametro = "superficie_{}".format(tipo)
	suma = sum([getattr(d, parametro) or 0 for d in dominios])
	return numerico(suma, 8)

register.filter('numerico', numerico)
register.filter('superficies', superficies)