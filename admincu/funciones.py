import datetime
import calendar
import random
import string
from datetime import date, timedelta
from django.contrib.auth.decorators import user_passes_test
from consorcios.models import *
from arquitectura.models import *
from contabilidad.models import *
from op.models import *
from templated_email import send_templated_mail

usuarios_demo = ["demo.admin", "demo.contable", "demo.js", "demo.ka"]
# Para no dejar agregar cosas en usuario demo
def valid_demo(usuario):
	if usuario.username in usuarios_demo:
		return True
	return False


# Decorador para grupos
def group_required(*grupos):
	def grupo(user):
		if user.is_authenticated:
			if bool(user.groups.filter(name__in=grupos)):
				return True
		return False
	return user_passes_test(grupo)


# Funcion para agregar al contexto
def context_consorcio(request):
	try:
		consorcio = Consorcio.objects.get(usuarios=request.user)
	except:
		consorcio = None
	if request.user.username in usuarios_demo:
		validacion_demo = True
	else:
		validacion_demo = False
	agregado = {
		'consorcio': consorcio,
		'validacion_demo': validacion_demo
	}
	return agregado


# Funcion para agregar a la vista
def consorcio(request):
	try:
		consorcio = Consorcio.objects.get(usuarios=request.user)
	except:
		consorcio = None
	return consorcio


# Creador de numeros aleatorios
def randomNumber(modelo, campo):
	query = False
	numero = 0
	while query == False:
		aleatorio = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(30)])
		try:
			filtro = {campo: aleatorio}
			numero = modelo.objects.get(**filtro)
		except:
			numero = aleatorio
			query = True
	return numero

# Creador de numeros aleatorios
def generador_codigo(modelo, campo):
	query = False
	codigo = ""
	while query == False:
		aleatorio = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(5)])
		try:
			filtro = {campo: aleatorio}
			codigo = modelo.objects.get(**filtro)
		except:
			codigo = aleatorio
			query = True
	return codigo



# def validacion_datos(ubicacion, contenedor, cons=None):
# 	errores = []
# 	# Nombre del archivo
# 	nombre = str(ubicacion).split('.xls')[0]
# 	nombre = nombre[::-1].split('/')[0]
# 	nombre = nombre[::-1]

# 	# Por si faltan datos
# 	dataoff = [
# 		"Debes indicar un %s en la fila %s" % (titulo, index)
# 		for titulo, valor in contenedor.isnull().to_dict().items() for index, v in valor.items() if v == True
# 	]
# 	if dataoff:
# 		errores.extend(dataoff)
# 		return False, errores


# 	titulos = list(contenedor)
# 	for titulo in titulos:
# 		# Validaciones particulares
# 		# Por si tiene relaciones en la base de datos
# 		try:
# 			relacion = eval(titulo.capitalize()) if titulo != 'periodo' else None
# 		except:
# 			relacion = None
# 		if relacion:
# 			for index, obj in enumerate(contenedor[titulo]):
# 				try:
# 					objeto = eval(titulo.capitalize()).objects.get(
# 								numero=obj,
# 								consorcio=cons,
# 							)
# 					contenedor[titulo][index] = objeto
# 				except:
# 					errores.append("Debes colocar un %s existente en la fila %s" % (titulo, index))
# 		## Sin relaciones
# 		else:
# 			# Para el periodo
# 			if titulo == "periodo":
# 				for index, obj in enumerate(contenedor[titulo]):
# 					try:
# 						objeto = datetime.strptime(obj, '%Y-%m').date()
# 					except:
# 						errores.append("Debes colocar un %s valido en la fila %s" % (titulo, index))

# 			# Para el capital
# 			elif titulo == "capital":
# 				for index, obj in enumerate(contenedor[titulo]):
# 					try:
# 						objeto = float(obj)
# 					except:
# 						errores.append("Debes colocar un %s valido en la fila %s" % (titulo, index))



# 	return contenedor, errores

def armar_link(link):
	return 'https://www.admincu.com{}'.format(link)

def emisor_mail(cons):
	emisor = "{} <no-reply@".format(cons.nombre_completo)
	if cons.dominioweb:
		emisor += "{}>".format(cons.dominioweb)
	else:
		emisor += "admincu.com>"

	return emisor