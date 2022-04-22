import datetime
import json
from ntpath import join
from pdb import post_mortem
import re
import os
import ftplib
from datetime import date, datetime

from django.views import generic
from django.conf import settings

from .models import *

class Exp():
	"""
		Exportador/Importador ExP class, generador de barcode numerico.
	"""

	clientes = set(list(ClienteExp.objects.all().values_list('codigo_exp', flat=True)))
	fecha_archivo = datetime.now()
	ftp_servidor = 'files.plataformadepagos.com.ar'
	ftp_usuario = 'AdminCuUser'
	ftp_clave = 'AdminSALTA@@2019'

	# Funciones de importacion
	def exp_import(self):
		''' Importador de cobros Exp.'''
		for cliente in self.clientes:
			self.codigo_cliente = cliente
			self.copy_file()

	def copy_file(self):
		'''Escribe contenido del archivo en el servidor de expensas pagas en carpeta local.'''
		# Datos FTP
		nombre = "{}_RD{}.txt".format(str(self.codigo_cliente), self.fecha_archivo.strftime('%Y%m%d'))
		try:
			# Conectamos con el servidor, creamos archivo local y ejecutamos escritura de database.
			s = ftplib.FTP(self.ftp_servidor, self.ftp_usuario, self.ftp_clave)
			ruta_servidor_recibe = "/cli{}/Recibe/".format(str(self.codigo_cliente))
			s.cwd(ruta_servidor_recibe)
			s.retrbinary('RETR ' + nombre, open("{}/expensas_pagas/recibe/{}".format(settings.MEDIA_ROOT ,nombre), "wb").write) 
			s.quit()
			self.write_db(nombre=nombre)
		except:
			print('importacion no generada')


	def write_db(self, nombre):
		'''Escribe database con datos provistos por txt de exp'''
		listOfLines = []
		with open ("{}/expensas_pagas/recibe/{}".format(settings.MEDIA_ROOT ,nombre), "r") as myfile:
			for line in myfile:
				listOfLines.append(line.strip())
		listOfLines.pop(0)
		listOfLines.pop()
		listOfCobrosExp = []
		for c in listOfLines:
			listOfCobrosExp.append(CobroExp(
				codigo_consorcio = self.formato_imp(c[1:5], 'int'),
				unidad_funcional = self.formato_imp(c[5:10], 'int'),
				fecha_cobro = self.formato_imp(c[10:18], 'date'),
				importe_cobrado = self.formato_imp(c[18:29], 'float'),
				comision_plataforma = self.formato_imp(c[29:40], 'float'),
				neto_a_depositar = self.formato_imp(c[40:51], 'float'),
				canal_de_pago = c[51:],
			))
		CobroExp.objects.bulk_create(listOfCobrosExp)


	def formato_imp(self, val, tipo):
		''' Conversor al formato importacion. Recibe un str y retorna un valor admitido en el modelo. '''
		if tipo == 'float':
			x = val[:9]
			y = val[9:]
			output = float(x + '.' + y)
		if tipo == 'int':
			output = int(val)
		if tipo == 'date':
			output = datetime.strptime(val, '%Y%m%d').date()
		return output

		
	# Funciones de exportacion
	def exp_export(self):
		''' Inicializa la clase para crear un acrchivo txt por cliente de Exp.'''
		for cliente in self.clientes:
			self.queryset = Factura.objects.filter(consorcio__exp__codigo_exp=cliente, exp__inf_deuda=False, receipt__total_amount__lt=100000)
			if self.queryset.count() > 0:
				self.codigo_cliente = cliente
				self.dato_interno = self.queryset.first().consorcio.exp.first().di_exp
				nombre = 'DI_{}_{}.txt'.format(str(self.codigo_cliente), self.fecha_archivo.strftime('%Y%m%d%H%M%S'))
				self.write_txt(nombre=nombre)
				self.exp_upload(nombre=nombre)


	def exp_upload(self, nombre):	
		''' Sube el archivo al servidor de ExP. '''
		fileName = "/{}/expensas_pagas/envia/{}".format(settings.MEDIA_ROOT, nombre)
		routeDestination = "/cli{}/Envia/".format(str(self.codigo_cliente))		
		# abrimos la conexion con el servidor
		try:
			ftp=ftplib.FTP(self.ftp_servidor, self.ftp_usuario, self.ftp_clave)
			# Canviamos de directorio
			ftp.cwd(routeDestination)
			# Subimos el archivo
			ftp.storbinary("STOR {}".format(nombre), open(fileName, 'rb'))
			ftp.quit()
		except:
			print('Error al subir archivo')


	def write_txt(self, nombre):
		''' Crea un archivo txt y escribe una linea por elemento en la lista de registros.'''
		data = self.hacer_data_exp()
		file_export = open("{}/expensas_pagas/envia/{}".format(settings.MEDIA_ROOT, nombre), "w")
		for i in data:
			file_export.write(i + os.linesep)
		file_export.close()


	def hacer_data_exp(self):
		''' Concatena header, detalle y trailer. Retorna una lista con un elemento por registro.'''
		data = []
		data.append(self.hacer_header())
		for i in self.hacer_detalle():
			data.append(i)
		data.append(self.hacer_trailer())
		return data


	def hacer_header(self):
		''' Generador de header. Retorna un str.'''
		data_header = [
			self.formato_exp('int', 1, 1),
			self.formato_exp('int', 4, self.codigo_cliente),
			self.formato_exp('date', 14, self.fecha_archivo, '%Y%m%d%H%M%S'),
		]
		return ''.join(data_header)


	def hacer_detalle(self):
		''' Generador de detalle. Retorna una lista de str. Ademas genera self.total_1er_venc y self.total_2do_venc.'''
		data_detalle = []
		self.total_1er_venc = 0
		self.total_2do_venc = 0
		self.q_registros = 0
		for c in self.queryset:

			fecha1 = c.expensas_pagas(0)
			fecha2 = c.expensas_pagas(1)
			if not fecha2:
				fecha2 = fecha1
			saldo1 = c.saldo(fecha1)
			saldo2 = c.saldo(fecha2)

			if saldo1 < 100000 or saldo2 < 100000:
				if c.socio.socio.first():
					try: # Parche necesario porque en la base de dato existen socios sin usuario vinculado, no deberia corresponder en el nuevo sistema.
						email = c.socio.usuarios.first().email # Revisar, aveces manda 2 emails porque hay usuarios que tienen 2 emails cargados ejemplo (mendez mena)
					except:
						email = None

					vinculo = c.exp.first()

					dato = [
						self.formato_exp('int', 1, 5),
						self.formato_exp('int', 4, c.consorcio.id),
						self.formato_exp('int', 5, c.socio.id),
						self.formato_exp('char', 20, c.receipt.issued_date),
						self.formato_exp('char', 40, c.socio),
						self.formato_exp('char', 15, c.socio.socio.first().nombre),
						self.formato_exp('email', 40, email),
						self.formato_exp('date', 8, fecha1, '%Y%m%d'),
						self.formato_exp('float', 11, saldo1),
						self.formato_exp('date', 8, fecha2, '%Y%m%d'),
						self.formato_exp('float', 11, saldo2),
						self.formato_exp('int', 14, vinculo.cpe),
						self.formato_exp('int', 56, vinculo.barcode),
					]
					string = ''.join(dato)
					data_detalle.append(string)
					vinculo.inf_deuda = True
					vinculo.save()
					self.q_registros += 1
					self.total_1er_venc = self.total_1er_venc + saldo1
					self.total_2do_venc = self.total_2do_venc + saldo2
		return data_detalle


	def hacer_trailer(self):
		''' Generador de detale. Retorna un str.'''
		data_trailer = []
		data_trailer.extend((
			self.formato_exp('int', 1, 9),
			self.formato_exp('int', 4, self.codigo_cliente),
			self.formato_exp('int', 14, self.fecha_archivo.strftime('%Y%m%d%H%M%S')),
			self.formato_exp('int', 6, self.q_registros),
			self.formato_exp('float', 11, self.total_1er_venc),
			self.formato_exp('float', 11, self.total_2do_venc),
		))
		return ''.join(data_trailer)


	def formato_exp(self, tipo, long, val, format_date=False):
		''' Conversor al formato exp. Retorna un str en el formato solicitado. '''
		if not val:
			valor = 0 if tipo in ['int', 'float', 'date'] else ' '
		else:
			valor = val
		if tipo == 'char':
			char = str(valor)
			char_s_caracteres = re.sub('[/\*$()=~+%.#]', ' ', char)
			output = char_s_caracteres.ljust(long)
		if tipo == 'email':
			output = str(valor).ljust(long)
		else:
			if tipo == 'float' and valor != 0:
				str_dos_decimales = "{:.2f}".format(valor)
				s_punto = re.sub('[.]', '', str_dos_decimales)
				output = s_punto.zfill(long)
			if tipo == 'date' and valor != 0:
				output = str(valor.strftime(format_date)).zfill(long)
			if tipo == 'int' or valor == 0:
				output = str(valor).zfill(long)
		return output[0:long]



	# Funciones generadoras de barcode y cpe. Generan y guardan en base de datos un barcode y cpe por factura.
	def cpe(self, c):
		''' Generador de CPE. Recibe un credito. Retorna un str. '''
		data_cpe = [
			self.formato_exp('int', 4, c.consorcio.exp.first().codigo_exp),
			self.formato_exp('int', 4, c.consorcio.id),
			self.formato_exp('int', 5, c.socio.id),
		]
		dv1 = self.dv(''.join(data_cpe))
		data_cpe.append(self.formato_exp('int', 1, dv1))
		return ''.join(data_cpe)


	def barcode(self, c):
		''' Generador de barcode. Recibe un credito. Retorna un str. '''
		fecha1 = c.expensas_pagas(0)
		fecha2 = c.expensas_pagas(1) or fecha1
		saldo1 = c.saldo(fecha1)
		saldo2 = c.saldo(fecha2)
		if fecha2:
			dif = abs(fecha2 - fecha1).days
		else:
			dif = 0
		data_barcode = [
			self.formato_exp('int', 4, 2634),
			self.formato_exp('int', 4, c.consorcio.id),
			self.formato_exp('int', 5, c.socio.id),
			self.formato_exp('date', 6, fecha1, '%y%m%d'),
			self.formato_exp('float', 7, saldo1),
			self.formato_exp('int', 2, dif),
			self.formato_exp('float', 7, saldo2),
			self.formato_exp('int', 2, 0),
			self.formato_exp('float', 7, 0),
			self.formato_exp('int', 6, c.consorcio.exp.first().di_exp),
			self.formato_exp('int', 4, c.consorcio.exp.first().codigo_exp),
		]
		dv1 = self.dv(''.join(data_barcode))
		data_barcode.append(self.formato_exp('int', 1, dv1))
		dv2 = self.dv(''.join(data_barcode))
		data_barcode.append(self.formato_exp('int', 1, dv2))

		final = ''.join(data_barcode)

		guardar_barcode = DocumentoExp(
			documento=c,
			barcode=final,
			cpe=self.cpe(c)
		)
		guardar_barcode.save()

		return final


	def dv(self, data_barcode):
		''' Generador de digito verificador. Recibe un str. Retorna un int.'''
		barcode = data_barcode[1:]
		verificador_data = [3,5,7,9]
		result = int(data_barcode[0])
		indice = 0
		for i in barcode:
			y = int(i)*verificador_data[indice%4]
			result += y
			indice = indice + 1
		result = result / 2
		result = int(result) % 10
		return result







from django.shortcuts import render
from django.http import HttpResponse
import requests

class NewExp():
		
	def __init__(self):
		self.token = self.StartSesion()
		
	ext = {'codigo':'CodigoDePagoElectronico', 'cvu':'ClaveVirtualUniforme', 'barcode':'CodigoDeBarras'} #se lleva a adminsmart



	def formato_imp(self, val, tipo):
		''' Conversor al formato importacion. Recibe un str y retorna un valor admitido en el modelo. '''
		if tipo == 'float':
			x = val[:9]
			y = val[9:]
			output = float(x + '.' + y)
		if tipo == 'int':
			output = int(val)
		if tipo == 'date':
			output = datetime.strptime(val, '%Y%m%d').date()
		return output



	def formato_exp(self, tipo, long, val, format_date=False): #funcion que debe remplazarse al pasar a adminsmart
		''' Conversor al formato exp. Retorna un str en el formato solicitado. '''
		if not val:
			valor = 0 if tipo in ['int', 'float', 'date'] else ' '
		else:
			valor = val
		if tipo == 'char':
			char = str(valor)
			char_s_caracteres = re.sub('[/\*$()=~+%.#]', ' ', char)
			output = char_s_caracteres.ljust(long)
		if tipo == 'email':
			output = str(valor)
		else:
			if tipo == 'float' and valor != 0:
				output = "{:.2f}".format(valor)
			if tipo == 'date' and valor != 0:
				t = str(valor.strftime(format_date))
				output = t.replace('-', '%2F') 
			if tipo == 'int' or valor == 0:
				output = str(valor)
		return output

	def get_dato(self, c, dato_solicitado): #funcion que debe remplazarse al pasar a adminsmart
		r = {
			'cliente' : self.formato_exp('int', 5, c.consorcio.exp.first().codigo_exp),
			'consorcio' : self.formato_exp('int', 5, c.consorcio.id),
			'unidad_funcional' : self.formato_exp('int', 5, c.socio.id)
		}
		if dato_solicitado == 'codigo' or dato_solicitado == 'cvu':
			dato = [
				self.ext[dato_solicitado],
				'?Cliente=',
				r['cliente'],
				'&Consorcio=',
				r['consorcio'],
				'&UnidadFuncional=',
				r['unidad_funcional'],
			]
		elif dato_solicitado == 'barcode':
			fecha1 = c.expensas_pagas(0) #datetime.strptime('2022-04-19', '%Y-%m-%d')
			fecha2 = c.expensas_pagas(1) or fecha1 #datetime.strptime('2022-05-19', '%Y-%m-%d')
			saldo1 = c.saldo(fecha1)
			saldo2 = c.saldo(fecha2)
			dato = [
				self.ext[dato_solicitado],
				'?Cliente=',
				r['cliente'],
				'&Consorcio=',
				r['consorcio'],
				'&UnidadFuncional=',
				r['unidad_funcional'],
				'&FechaPrimerVencimiento=',
				self.formato_exp('date', 12, fecha1, '%d-%m-%Y'),
				'&ImportePrimerVencimiento=',
				self.formato_exp('float', 11, saldo1),
			]
			if not fecha1 == fecha2:
				if not saldo1 == saldo2:
					dato.append('&FechaSegundoVencimiento=')
					dato.append(self.formato_exp('date', 12, fecha2, '%d-%m-%Y'))
					dato.append('&ImporteSegundoVencimiento=')
					dato.append(self.formato_exp('float', 11, saldo2))
		st = ''.join(dato)
		return st				





	# desde aqui todo se lleva igual a adminsmart

	def StartSesion(self): #obtiene token para iniciar una consulta
		url = 'https://api.expensaspagas.com.ar/Sesion'
		payload = {"apiKey": "AdminCuUser", "secret": "AdminCu##2022"}
		r = requests.post(url, json=payload)
		if r.status_code == 200:
			data = r.json()
			token = data['token']
			return token

	def url_generator(self, c, dato_solicitado): #genera url para realizar consulta 	
		base_url = 'https://api.expensaspagas.com.ar/'
		dato = self.get_dato(c, dato_solicitado)
		st = ''.join([base_url, dato])
		return st

	def request_generator(self, c, dato_solicitado): #realiza consulta, recibe un objeto para extraer informacion(credito en admincu) y el dato a obtener (barcode, codigo o cvu) 
		token = self.token
		head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
		url = self.url_generator(c, dato_solicitado)
		print(url)
		r = requests.get(url, headers=head)
		print(r)
		if r.status_code == 200:
			data = r.json()
			if dato_solicitado == 'barcode':
				resp = data[dato_solicitado]
			else:
				resp = data[self.ext[dato_solicitado]]
			return resp

	def cupon_creator(self, c): #genera el cupon (documento exp) vinculado al objeto del sistema (en el caso de admincu el credito), retorna el barcode solamente a los fines de repetir el comportamiento del viejo sistema
		vinculo = c.exp.first() #solo debe crearse cupon si no tiene un cupon generado
		if vinculo == None:
			
			barcode = self.request_generator(c, dato_solicitado='barcode')
			codigo = self.request_generator(c, dato_solicitado='codigo')
			#cvu = self.request_generator(c, dato_solicitado='cvu') aun no funciona de su lado y no tenemos espacio en la base de dato para guardarlo ni lugar para escribir en el html
			guardar_cupon = DocumentoExp(
				documento=c,
				barcode=barcode,
				cpe=codigo
			)
			guardar_cupon.save()
			return barcode


		
		
		









	def hacer_detalle(self, queryset):  #esta funcion es cochina pero consecuencia de cochinadas del admincu, debe corregirse al pasar al smart
		data_detalle = []
		self.total_1er_venc = 0
		self.total_2do_venc = 0
		self.q_registros = 0
		for c in queryset:
			
			vinculo = c.exp.first() #solo deben agregarse valores a detalle si ya se tiene un cupon generado
			if not vinculo == None:
				
				fecha1 = c.expensas_pagas(0)
				fecha2 = c.expensas_pagas(1)
				saldo1 = c.saldo(fecha1)
				if not fecha2:
					saldo2 = None
				else:
					saldo2 = c.saldo(fecha2)
				


				if saldo1 != 0 or saldo2 !=0:
					if saldo1 < 100000 or saldo2 < 100000:
						if c.socio.socio.first():
							try: # Parche necesario porque en la base de dato existen socios sin usuario vinculado, no deberia corresponder en el nuevo sistema.
								email = c.socio.usuarios.first().email # Revisar, aveces manda 2 emails porque hay usuarios que tienen 2 emails cargados ejemplo (mendez mena)
							except:
								email = None

							Consorcio = c.consorcio.id
							UnidadFuncional = c.socio.id
							Periodo = self.formato_exp('date', 20, c.receipt.issued_date,'%m/%Y')
							Propietario = self.formato_exp('char', 35, c.socio)
							Ubicacion = '1'
							Email = self.formato_exp('email', 40, email)
							FechaPrimerVencimiento = self.formato_exp('date', 8, fecha1, '%d/%m/%Y')
							ImportePrimerVencimiento = saldo1
							FechaSegundoVencimiento = self.formato_exp('date', 8, fecha2, '%d/%m/%Y')
							ImporteSegundoVencimiento = saldo2
							CodigoDePagoElectronico = self.formato_exp('int', 14, vinculo.cpe)
							CodigoDeBarras = self.formato_exp('int', 56, vinculo.barcode)


							dato = {
								"Consorcio": Consorcio,
								"UnidadFuncional": UnidadFuncional,
								"Periodo": Periodo,
								"Propietario": Propietario,
								"Ubicacion": Ubicacion,
								"Email": Email,
								"FechaPrimerVencimiento": FechaPrimerVencimiento,
								"ImportePrimerVencimiento": ImportePrimerVencimiento,
								"FechaSegundoVencimiento": FechaSegundoVencimiento,
								"ImporteSegundoVencimiento": ImporteSegundoVencimiento,
								"CodigoDePagoElectronico":CodigoDePagoElectronico,
								"CodigoDeBarras": CodigoDeBarras,
								}
							data_detalle.append(dato)
							
							self.q_registros += 1
							self.total_1er_venc = self.total_1er_venc + saldo1
							self.total_2do_venc = self.total_2do_venc + saldo2
							vinculo.inf_deuda = True
							vinculo.save()
		return data_detalle



	def inf_deuda_generator(self, queryset): #debera modificarse al pasar a adminsmart
		detalle = self.hacer_detalle(queryset)
		t = {
		"Cliente":	self.codigo_cliente,
		"CantidadRegistros": int(self.q_registros),
		"TotalesPrimerVencimiento":	self.total_1er_venc,
		"TotalesSegundoVencimiento": self.total_2do_venc,
		"Detalle": detalle
		}
		return t



	def request_inf_deuda(self):
		self.clientes = set(list(ClienteExp.objects.all().values_list('codigo_exp', flat=True)))
		for cliente in self.clientes:
			queryset = Factura.objects.filter(consorcio__exp__codigo_exp=cliente, exp__inf_deuda=False, receipt__total_amount__lt=100000)
			if queryset.count() > 0:
				self.codigo_cliente = cliente

				#token = self.token
				#url = 'https://plapsacustomersapitest.azurewebsites.net/InformeDeDeuda'
				#head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
				payload = self.inf_deuda_generator(queryset)
				#r = requests.post(url=url, json=payload, headers=head)
				#if r.status_code == 200:
				#data = r.json()
				return payload







	def request_cobro_generator(self, cliente, fecha):
		g = [
			'https://api.expensaspagas.com.ar/ArchivoDePagos?',
			'Cliente=', str(cliente),
			'&',
			'FechaRendicion=', self.formato_exp('date', 12, fecha, '%d-%m-%Y') 
		]
		url = ''.join(g)
		print(url)
		token = self.token
		head = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
		r = requests.get(url, headers=head)
		print(r)
		if r.status_code == 200:
			d = r.text
			data = d.split("\n")
			if len(data) > 0:
				data.pop(0)
				data.pop()
				data.pop()
				for c in data:
					CobroExp.objects.create(
						codigo_consorcio = self.formato_imp(c[1:5], 'int'),
						unidad_funcional = self.formato_imp(c[5:10], 'int'),
						fecha_cobro = self.formato_imp(c[10:18], 'date'),
						importe_cobrado = self.formato_imp(c[18:29], 'float'),
						comision_plataforma = self.formato_imp(c[29:40], 'float'),
						neto_a_depositar = self.formato_imp(c[40:51], 'float'),
						canal_de_pago = c[51:],
					)
					print(cliente)
					print(fecha) 


	def cobros_exp(self):
		fechas = [
			#datetime(2022, 4, 7),
			#datetime(2022, 4, 8),
			#datetime(2022, 4, 9),
			#datetime(2022, 4, 10),
			#datetime(2022, 4, 11),
			#datetime(2022, 4, 12),
			#datetime(2022, 4, 13),
			#datetime(2022, 4, 14),
			#datetime(2022, 4, 15),
			#datetime(2022, 4, 16),
			#datetime(2022, 4, 17),
			#datetime(2022, 4, 18),
			datetime(2022, 4, 19),
			datetime(2022, 4, 20),
			datetime(2022, 4, 21),			
			]
		self.clientes = [1575, 1216, 1229]
		for cliente in self.clientes:
			for f in fechas:
				self.request_cobro_generator(cliente=cliente, fecha=f)
			











