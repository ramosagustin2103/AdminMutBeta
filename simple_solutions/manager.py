from datetime import date
import paramiko
import ftplib

from django.conf import settings

from .models import *
from creditos.models import Factura
from comprobantes.models import Comprobante
from expensas_pagas.models import DocumentoExp
from reportes.models import Reporte


# private_key = paramiko.RSAKey.from_private_key_file(settings.MEDIA_ROOT + "/admincu2.ppk")

class Conexion():
	"""
		Exportador/Importador ExP class, generador de barcode numerico.
	"""

	clientes = ClienteSS.objects.all()
	hoy = date.today()
	hostname = "s-ddd967132e9f42198.server.transfer.us-east-1.amazonaws.com"
	usuario = "admincu"
	key_path = settings.MEDIA_ROOT + "/admincu_ss"	
	opciones = [
		{
			'modelo': 'Factura',
			'carpeta': 'facturas',
			'titulo': 'FACTURA',
		},
		{
			'modelo': 'Comprobante',
			'carpeta': 'recibos',
			'titulo': 'RECIBO',
		},
		{
			'modelo': 'DocumentoExp',
			'carpeta': 'cupones',
			'titulo': 'CUPON',
		}
	]

	# Funciones de exportacion
	def export(self):
		''' Inicializa la clase para crear un acrchivo txt por cliente de Exp.'''

		for cliente in self.clientes:
			for opcion in self.opciones:
				ultimo_enviado = Enviado.objects.filter(consorcio=cliente.consorcio, modelo=opcion['modelo']).order_by("-id_modelo").first()
				if ultimo_enviado:
					kwargs = {
						'id__gt': ultimo_enviado.id_modelo
					}
					if opcion['modelo'] == "DocumentoExp":
						kwargs['documento__consorcio'] = cliente.consorcio
					else:
						kwargs['consorcio'] = cliente.consorcio
					documentos = eval(opcion['modelo']).objects.filter(**kwargs)
					if documentos:
						a_enviar, envios = self.procesar(cliente.nombre, documentos, opcion)
						self.upload(cliente.nombre, a_enviar, opcion['carpeta'], envios)
						
					

	def procesar(self, nombre_cliente, documentos, opcion):
		documentos_procesados = []
		envios = []
		for d in documentos:
			if d.pdf:
				documento = {
					'nombre': "{}_{}_{}_{}.pdf".format(nombre_cliente, d.socio.id, opcion['titulo'], d.id),
					'path': d.pdf.path 
				}
				documentos_procesados.append(documento)

				consorcio = d.documento.consorcio if opcion['modelo'] == "DocumentoExp" else d.consorcio 
				envios.append(Enviado(
					consorcio=consorcio,
					modelo=opcion['modelo'],
					id_modelo=d.id,
					fecha_envio=self.hoy
				))

		return documentos_procesados, envios

	def upload(self, carpeta_cliente, documentos_procesados, carpeta_documento, envios):	
		try:
			ssh_connect = paramiko.SSHClient()
			ssh_connect.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			key = paramiko.RSAKey.from_private_key_file(self.key_path)		
			ssh_connect.connect( hostname=self.hostname, username=self.usuario, pkey=key)
			sftp = ssh_connect.open_sftp()
			for d in documentos_procesados:
				remotepath = "/{}/{}/{}".format(carpeta_cliente, carpeta_documento, d['nombre'])
				respuesta = sftp.put(d['path'], remotepath=remotepath)
			
			ssh_connect.close()
			self.save(envios)
		except:
			print('Error al subir archivo')			

	def save(self, envios):
		Enviado.objects.bulk_create(envios)