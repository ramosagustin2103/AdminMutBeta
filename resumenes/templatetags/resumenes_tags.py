from django import template

register = template.Library()

@register.filter(name='porcentaje')
def porcentaje(numerador, denominador):
	try:
		return "{}%".format(round(float(numerador)*100/float(denominador),2))
	except:
		return "0%"
