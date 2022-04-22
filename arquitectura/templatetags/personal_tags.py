from django import template
from django.contrib.auth.models import Group
from decimal import Decimal

register = template.Library()
@register.filter(name='add_attr')
def add_attr(field, css):
	attrs = {}
	definition = css.split(',')

	for d in definition:
		if ':' not in d:
			attrs['class'] = d
		else:
			key, val = d.split(':')
			attrs[key] = val

	return field.as_widget(attrs=attrs)


@register.filter(name='multiply')
def multiply(value, arg):
	value = round(float(value)*float(arg),2)
	return Decimal("%.2f" % value)